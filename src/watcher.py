import json
import threading

import json_stream.requests

import logging
import time

import sseclient
from unsync import unsync, Unfuture

from src import variables
from src.constants import SECONDS_PER_SLOT, SLOTS_PER_EPOCH
from src.handlers.handler import WatcherHandler
from src.metrics.prometheus.duration_meter import duration_meter
from src.metrics.prometheus.watcher import (
    SLOT_NUMBER,
    KEYS_API_SLOT_NUMBER,
    VALIDATORS_INDEX_SLOT_NUMBER,
)
from src.providers.alertmanager.client import AlertmanagerClient
from src.providers.consensus.client import ConsensusClient
from src.providers.consensus.typings import ChainReorgEvent, BlockHeaderResponseData
from src.providers.keys.client import KeysAPIClient
from src.providers.keys.typings import KeysApiStatus, LidoNamedKey
from src.typings import SlotNumber
from src.variables import CYCLE_SLEEP_IN_SECONDS, SLOTS_RANGE

logger = logging.getLogger()

MAX_HANDLED_HEADERS_COUNT = 96  # Keep only the last 96 slots (3 epochs) for chain reorgs check


class Watcher:
    # Init
    consensus: ConsensusClient
    keys_api: KeysAPIClient
    alertmanager: AlertmanagerClient
    genesis_time: int
    handlers: list[WatcherHandler]

    # Tasks
    validators_updater: Unfuture = None
    keys_updater: Unfuture = None

    # Last state
    keys_api_status: KeysApiStatus | None = None
    keys_api_nonce: int = 0

    lido_keys: dict[str, LidoNamedKey] = {}
    indexed_validators_keys: dict[str, str] = {}

    chain_reorgs: dict[str, ChainReorgEvent] = {}

    handled_headers: list[BlockHeaderResponseData] = []

    def __init__(self, handlers: list[WatcherHandler]):
        self.consensus = ConsensusClient(variables.CONSENSUS_CLIENT_URI)
        self.keys_api = KeysAPIClient(variables.KEYS_API_URI)
        self.alertmanager = AlertmanagerClient(variables.ALERTMANAGER_URI)
        self.genesis_time = int(self.consensus.get_genesis().genesis_time)
        self.handlers = handlers

    def run(self):
        def _run(slot_to_handle='head'):
            current_head = self._get_header(slot_to_handle)
            if not current_head:
                logger.debug({'msg': f'No new head, waiting {CYCLE_SLEEP_IN_SECONDS} seconds'})
                time.sleep(CYCLE_SLEEP_IN_SECONDS)
                return

            if self.keys_updater is not None and self.keys_updater.done():
                self.keys_updater.result()
                try:
                    self.keys_updater = self._update_lido_keys(current_head)
                except Exception as e:  # pylint: disable=broad-except
                    logger.error({'msg': 'Can not update lido keys', 'exception': str(e)})

            if self.validators_updater is not None and self.validators_updater.done():
                self.validators_updater.result()
                self.validators_updater = self._update_validators()

            if self.keys_updater is None:
                try:
                    self.keys_updater = self._update_lido_keys(current_head)
                except Exception as e:  # pylint: disable=broad-except
                    logger.error({'msg': 'Can not update lido keys', 'exception': str(e)})
            if self.validators_updater is None:
                self.validators_updater = self._update_validators()

            logger.info({'msg': f'New head [{current_head.header.message.slot}]'})
            SLOT_NUMBER.set(current_head.header.message.slot)

            # ATTENTION! While we handle current head, new head could be happened
            # We should keep eye on handler execution time
            self._handle_head(current_head)
            self.handled_headers.append(current_head)
            if len(self.handled_headers) > MAX_HANDLED_HEADERS_COUNT:
                self.handled_headers.pop(0)

            logger.info({'msg': f'Head [{current_head.header.message.slot}] is handled'})
            time.sleep(CYCLE_SLEEP_IN_SECONDS)

        logger.info({'msg': f'Watcher started. Handlers: {[handler.__class__.__name__ for handler in self.handlers]}'})

        self.listen_chain_reorg_event()

        if SLOTS_RANGE:
            start, end = SLOTS_RANGE.split('-')
            for slot in range(int(start), int(end) + 1):
                _run(str(slot))
                self.keys_updater.result()
                self.validators_updater.result()
        else:
            while True:
                _run()

    @duration_meter()
    def _handle_head(self, head: BlockHeaderResponseData):
        tasks = [h.handle(self, head) for h in self.handlers]
        for t in tasks:
            t.result()

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
        if self.indexed_validators_keys and SLOTS_PER_EPOCH != 0:
            return
        logger.info({'msg': 'Updating indexed validators keys'})
        try:
            stream = self.consensus.get_validators_stream(SlotNumber(slot))
            self.indexed_validators_keys = ConsensusClient.parse_validators(
                json_stream.requests.load(stream)['data'], self.indexed_validators_keys
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error({'msg': f'Error while getting validators: {e}'})
            return

        logger.info({'msg': f'Indexed validators keys updated: [{len(self.indexed_validators_keys)}]'})
        VALIDATORS_INDEX_SLOT_NUMBER.set(slot)

    @unsync
    @duration_meter()
    def _update_lido_keys(self, header: BlockHeaderResponseData) -> None:
        """Return dict with `publickey` as key and `LidoNamedKey` as value"""

        current_keys_status = self.keys_api.get_status()
        if self.keys_api_status is not None and (
            current_keys_status.elBlockSnapshot['timestamp'] >= self.keys_api_status.elBlockSnapshot['timestamp']
        ):
            return

        # Get modules and calculate current nonce
        # If nonce is not changed - we don't need to update keys
        modules = self.keys_api.get_modules()[0]

        current_nonce = sum(module['nonce'] for module in modules)
        del modules
        if self.keys_api_nonce >= current_nonce:
            return
        self.keys_api_nonce = current_nonce

        logger.info({'msg': 'Updating Lido keys'})
        modules_operators_stream = self.keys_api.get_operators_stream()
        modules_operators_dict = KeysAPIClient.parse_modules(
            json_stream.requests.load(modules_operators_stream)['data']
        )

        fetched_lido_keys_stream = self.keys_api.get_used_lido_keys_stream()
        self.lido_keys = KeysAPIClient.parse_keys(
            json_stream.requests.load(fetched_lido_keys_stream)['data'], modules_operators_dict
        )

        self.keys_api_status = current_keys_status
        del modules_operators_dict

        logger.warning({'msg': f'Lido keys updated: [{len(self.lido_keys)}]'})
        KEYS_API_SLOT_NUMBER.set(int(header.header.message.slot))

    @duration_meter()
    def _get_header(self, slot=None) -> BlockHeaderResponseData | None:
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
        return current_head

    @unsync
    def listen_chain_reorg_event(self):
        logger.info({'msg': 'Listening chain reorg events'})
        response = self.consensus.get_chain_reorg_stream()
        client = sseclient.SSEClient(response)
        for event in client.events():
            logger.warning({'msg': f'Chain reorg event: {event.data}'})
            event = ChainReorgEvent.from_response(**json.loads(event.data))
            lock = threading.Lock()
            with lock:
                self.chain_reorgs[event.slot] = event
