import json
import logging
import threading
import time
from dataclasses import asdict
from functools import cached_property
from typing import Optional

import json_stream.requests
import sseclient
from unsync import Unfuture, unsync

from src import variables
from src.constants import SECONDS_PER_SLOT, SLOTS_PER_EPOCH
from src.handlers.handler import WatcherHandler
from src.keys_source.base_source import BaseSource, NamedKey
from src.metrics.prometheus.duration_meter import duration_meter
from src.metrics.prometheus.watcher import (
    KEYS_SOURCE_SLOT_NUMBER,
    SLOT_NUMBER,
    VALIDATORS_INDEX_SLOT_NUMBER,
)
from src.providers.alertmanager.client import AlertmanagerClient
from src.providers.consensus.client import ConsensusClient
from src.providers.consensus.typings import (
    BlockHeaderResponseData,
    ChainReorgEvent,
    FullBlockInfo,
)
from src.providers.http_provider import NotOkResponse
from src.utils.decorators import thread_as_daemon
from src.variables import CYCLE_SLEEP_IN_SECONDS, SLOTS_RANGE
from src.web3py.typings import Web3

logger = logging.getLogger()

KEEP_MAX_HANDLED_HEADERS_COUNT = 96  # Keep only the last 96 slots (3 epochs) for chain reorgs check
MAX_VALIDATORS_INDEX_FETCH_REQUESTS = 50


class Watcher:
    def __init__(self, handlers: list[WatcherHandler], keys_source: BaseSource, web3: Web3 | None = None):
        # Init
        self.execution: Web3 | None = web3
        self.consensus: ConsensusClient = ConsensusClient(variables.CONSENSUS_CLIENT_URI)
        self.keys_source: BaseSource = keys_source
        self.alertmanager: AlertmanagerClient = AlertmanagerClient(variables.ALERTMANAGER_URI)
        self.genesis_time: int = int(self.consensus.get_genesis().genesis_time)
        self.handlers: list[WatcherHandler] = handlers
        # Tasks
        self.validators_updater: Unfuture = None
        self.keys_updater: Unfuture = None
        self.chain_reorg_event_listener: threading.Thread | None = None
        self.user_keys: dict[str, NamedKey] = {}
        self.indexed_validators_keys: dict[str, str] = {}
        self.chain_reorgs: dict[str, ChainReorgEvent] = {}
        self.handled_headers: list[BlockHeaderResponseData] = []
        self.disable_unexpected_exit_alerts: list[str] = variables.DISABLE_UNEXPECTED_EXIT_ALERTS

    def run(self, slots_range: Optional[str] = SLOTS_RANGE):
        def _run(slot_to_handle='head'):
            current_head = self._get_header_full_info(slot_to_handle)
            if not current_head:
                logger.debug({'msg': f'No new head, waiting {CYCLE_SLEEP_IN_SECONDS} seconds'})
                time.sleep(CYCLE_SLEEP_IN_SECONDS)
                return

            if self.keys_updater is None or self.keys_updater.done():
                self.keys_updater = self._update_user_keys(current_head)
            if self.validators_updater is None or self.validators_updater.done():
                self.validators_updater = self._update_validators()

            logger.info({'msg': f'New head [{current_head.header.message.slot}]'})

            # ATTENTION! While we handle current head, new head could be happened
            # We should keep eye on handler execution time
            self._handle_head(current_head)

            SLOT_NUMBER.set(current_head.header.message.slot)
            logger.info({'msg': f'Head [{current_head.header.message.slot}] is handled'})
            time.sleep(CYCLE_SLEEP_IN_SECONDS)

        logger.info({'msg': f'Watcher started. Handlers: {[handler.__class__.__name__ for handler in self.handlers]}'})

        if slots_range is not None:
            start, end = slots_range.split('-')
            for slot in range(int(start), int(end) + 1):
                try:
                    _run(str(slot))
                except NotOkResponse as e:
                    if e.status == 404:
                        pass
                self.keys_updater.result()
                self.validators_updater.result()
        else:
            while True:
                try:
                    # Run event listener task very first time or re-run after error
                    if self.chain_reorg_event_listener is None or not self.chain_reorg_event_listener.is_alive():
                        self.chain_reorg_event_listener = self.listen_chain_reorg_event()
                    _run()
                except Exception as e:  # pylint: disable=broad-except
                    logger.error({'msg': 'Error while handling head', 'exception': str(e)})
                    time.sleep(CYCLE_SLEEP_IN_SECONDS)

    @duration_meter()
    def _handle_head(self, head: FullBlockInfo):
        tasks = [h.handle(self, head) for h in self.handlers]
        for t in tasks:
            t.result()
        self.handled_headers.append(head)
        if len(self.handled_headers) > KEEP_MAX_HANDLED_HEADERS_COUNT:
            self.handled_headers.pop(0)

    @unsync
    @duration_meter()
    def _update_validators(self):
        """
        If current time it's the end of epoch - new validators will be added to the active set
        At this moment there is no new head, but we should get validators by slot anyway
        https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#registry-updates
        """
        now = time.time()
        diff = now - self.genesis_time
        slot = int(diff / SECONDS_PER_SLOT)
        if self.indexed_validators_keys and slot % SLOTS_PER_EPOCH != 0:
            return
        logger.info({'msg': 'Updating indexed validators keys'})
        if variables.VALIDATORS_INDEX_INCREMENTAL and self.indexed_validators_keys:
            updated = self._update_validators_incremental()
        else:
            updated = self._update_validators_full()
        if not updated:
            return

        logger.info({'msg': f'Indexed validators keys updated: [{len(self.indexed_validators_keys)}]'})
        VALIDATORS_INDEX_SLOT_NUMBER.set(slot)

    def _update_validators_full(self) -> bool:
        try:
            stream = self.consensus.get_validators_stream('head')
            self.indexed_validators_keys = ConsensusClient.parse_validators(
                json_stream.requests.load(stream)['data'], self.indexed_validators_keys
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error({'msg': f'Error while getting validators: {e}'})
            return False
        return True

    def _update_validators_incremental(self) -> bool:
        """
        The validator registry is append-only (index and pubkey immutable once assigned),
        so we only fetch unknown indexes, plus re-fetch a small tail of recent indexes to handle reorgs near the head.
        """
        try:
            max_known = max((int(index) for index in self.indexed_validators_keys), default=-1)
            if len(self.indexed_validators_keys) != max_known + 1:
                # Holes below max_known (e.g. interrupted full scan) would never be healed by the windowed fetch
                logger.warning({'msg': 'Validators index is not contiguous. Fall back to full scan'})
            else:
                # Start a tail below the head: one contiguous pass both re-fetches the
                # recent tail (reorg protection) and discovers new validators.
                tail = max(variables.VALIDATORS_INDEX_REFETCH_TAIL, 0)
                self._fetch_validators_from(max(0, max_known + 1 - tail))
                return True
        except Exception as e:  # pylint: disable=broad-except
            logger.warning({'msg': f'Error while incremental validators update: {e}. Fall back to full scan'})
        return self._update_validators_full()

    def _fetch_validators_from(self, start_index: int):
        """
        Fetch validators from start_index in chunks until the first short or empty page (= end of registry).
        """
        chunk_size = max(variables.VALIDATORS_INDEX_CHUNK_SIZE, 1)
        next_index = start_index
        for _ in range(MAX_VALIDATORS_INDEX_FETCH_REQUESTS):
            validator_ids = [str(index) for index in range(next_index, next_index + chunk_size)]
            validators = self.consensus.post_validators_by_ids('head', validator_ids)
            if len(validators) > chunk_size:
                raise RuntimeError(
                    f'postStateValidators returned {len(validators)} rows for {chunk_size} requested ids '
                    f'from index {next_index}; node is ignoring the id filter'
                )
            self.indexed_validators_keys.update((v.index, v.validator.pubkey) for v in validators)
            if len(validators) < chunk_size:
                return
            next_index += chunk_size
        raise RuntimeError(
            f'Validators index scan exceeded {MAX_VALIDATORS_INDEX_FETCH_REQUESTS} requests '
            f'from index {start_index}; node may be ignoring the id filter'
        )

    @unsync
    @duration_meter()
    def _update_user_keys(self, header: BlockHeaderResponseData) -> None:
        """Return dict with `publickey` as key and `NamedKey` as value"""
        try:
            new_keys = self.keys_source.update_keys()
        except Exception as e:  # pylint: disable=broad-except
            logger.error({'msg': 'Can not update user keys', 'exception': str(e)})
            return
        if new_keys:
            self.user_keys = new_keys
            logger.warning({'msg': f'User keys updated: [{len(self.user_keys)}]'})
        KEYS_SOURCE_SLOT_NUMBER.set(int(header.header.message.slot))

    @duration_meter()
    def _get_header_full_info(self, slot=None) -> FullBlockInfo | None:
        def force_use_fallback_callback(result) -> bool:
            """Callback that will be called if we can't get valid head block from beacon node"""
            data, _ = result
            diff = time.time() - ((int(data['header']['message']['slot']) * SECONDS_PER_SLOT) + self.genesis_time)
            if len(self.handled_headers) > 0 and diff > SECONDS_PER_SLOT * 4:
                # head didn't change for more than 4 slots (1/8 of epoch)
                return True
            return False

        slot = slot or 'head'

        current_head = self.consensus.get_block_header(
            slot, force_use_fallback_callback if slot == 'head' else lambda _: False
        )
        if len(self.handled_headers) > 0 and int(current_head.header.message.slot) == int(
            self.handled_headers[-1].header.message.slot
        ):
            return None
        current_block = self.consensus.get_block_details(current_head.root)
        return FullBlockInfo(**asdict(current_head), **asdict(current_block))

    @thread_as_daemon
    def listen_chain_reorg_event(self):
        try:
            logger.info({'msg': 'Listening chain reorg events'})
            response = self.consensus.get_chain_reorg_stream()
            client = sseclient.SSEClient(response)
            for event in client.events():
                logger.warning({'msg': f'Chain reorg event: {event.data}'})
                event = ChainReorgEvent.from_response(**json.loads(event.data))
                lock = threading.Lock()
                with lock:
                    self.chain_reorgs[event.slot] = event
        except Exception as e:  # pylint: disable=broad-except
            logger.error({'msg': 'Error while listening chain reorg events', 'exception': str(e)})

    @cached_property
    def valid_withdrawal_addresses(self):
        addresses = set(variables.VALID_WITHDRAWAL_ADDRESSES)
        if not addresses and self.execution:
            addresses = {self.execution.lido_contracts.lido_locator.functions.withdrawalVault().call().lower()}
        return addresses
