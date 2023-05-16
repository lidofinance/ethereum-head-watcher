import json_stream.requests

import logging
import time

from unsync import unsync, Unfuture

from src import variables
from src.constants import SECONDS_PER_SLOT, SLOTS_PER_EPOCH
from src.handlers.handler import WatcherHandler
from src.metrics.prometheus.basic import KEYS_API_LATEST_BLOCKNUMBER
from src.metrics.prometheus.duration_meter import duration_meter
from src.metrics.prometheus.watcher import (
    SLOT_NUMBER,
    BLOCK_NUMBER,
    KEYS_API_BLOCK_NUMBER,
    VALIDATORS_INDEX_SLOT_NUMBER,
)
from src.providers.alertmanager.client import AlertmanagerClient
from src.providers.consensus.client import ConsensusClient
from src.providers.consensus.typings import BlockDetailsResponse
from src.providers.keys.client import KeysAPIClient
from src.providers.keys.typings import KeysApiStatus, LidoNamedKey
from src.typings import BlockNumber, SlotNumber
from src.variables import CYCLE_SLEEP_IN_SECONDS, SLOTS_RANGE

logger = logging.getLogger()


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
    keys_api_status: KeysApiStatus = None
    keys_api_nonce: int = 0

    lido_keys: dict[str, LidoNamedKey] = {}
    indexed_validators_keys: dict[str, str] = {}

    head: BlockDetailsResponse = None

    def __init__(self, handlers: list[WatcherHandler]):
        self.consensus = ConsensusClient(variables.CONSENSUS_CLIENT_URI)
        self.keys_api = KeysAPIClient(variables.KEYS_API_URI)
        self.alertmanager = AlertmanagerClient(variables.ALERTMANAGER_URI)
        self.genesis_time = int(self.consensus.get_genesis().genesis_time)
        self.handlers = handlers

        # todo: add chain org event watcher. If we see that we was on not right fork, we should send alert about it

    def run(self):
        logger.info({'msg': f'Watcher started. Handlers: {[handler.__class__.__name__ for handler in self.handlers]}'})

        def wrapped(slot_to_handle='head'):
            current_head = self._get_head_block(slot_to_handle)
            if not current_head:
                logger.info({'msg': f'No new head, waiting {CYCLE_SLEEP_IN_SECONDS} seconds'})
                time.sleep(CYCLE_SLEEP_IN_SECONDS)
                return

            if self.keys_updater is not None and self.keys_updater.done():
                self.keys_updater.result()
                self.keys_updater = self._update_lido_keys(current_head)

            if self.validators_updater is not None and self.validators_updater.done():
                self.validators_updater.result()
                self.validators_updater = self._update_validators()

            if self.keys_updater is None or self.validators_updater is None:
                self.keys_updater = self._update_lido_keys(current_head)
                self.validators_updater = self._update_validators()

            logger.info({'msg': f'New head [{current_head.message.slot}]. Run handlers'})
            SLOT_NUMBER.set(current_head.message.slot)
            BLOCK_NUMBER.set(current_head.message.body['execution_payload']['block_number'])

            # ATTENTION! While we handle current head, new head could be happened
            # We should keep eye on handler execution time
            self._handle_head(current_head)
            self.head = current_head

            time.sleep(CYCLE_SLEEP_IN_SECONDS)

        if SLOTS_RANGE:
            start, end = SLOTS_RANGE.split('-')
            for slot in range(int(start), int(end) + 1):
                wrapped(str(slot))
        else:
            while True:
                wrapped()

    @duration_meter()
    def _handle_head(self, head: BlockDetailsResponse):
        tasks = [h.handle(self, head) for h in self.handlers]
        [t.result() for t in tasks]

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
        if not self.indexed_validators_keys or slot % SLOTS_PER_EPOCH == 0:
            logger.info({'msg': 'Updating indexed validators keys'})
            try:
                stream = self.consensus.get_validators_stream(SlotNumber(slot))
            except Exception as e:
                logger.error({'msg': f'Error while getting validators: {e}'})
                return

            for validator in json_stream.requests.load(stream)['data']:
                index = ""
                pubkey = ""
                for key, value in validator.items():
                    if key == "index":
                        if value in self.indexed_validators_keys:
                            continue
                        index = value
                    elif index != "" and key == "validator":
                        for k, v in value.items():
                            if k == "pubkey":
                                pubkey = v
                self.indexed_validators_keys[index] = pubkey
            logger.info({'msg': f'Indexed validators keys updated: [{len(self.indexed_validators_keys)}]'})
            VALIDATORS_INDEX_SLOT_NUMBER.set(slot)

    @unsync
    @duration_meter()
    def _update_lido_keys(self, block: BlockDetailsResponse) -> None:
        """Return dict with `publickey` as key and `LidoNamedKey` as value"""
        try:
            current_keys_status = self.keys_api.get_status()
        except Exception as e:
            logger.error({'msg': 'Can not get keys api status', 'exception': str(e)})
            return

        if self.keys_api_status is not None and (
            current_keys_status.elBlockSnapshot['timestamp'] >= self.keys_api_status.elBlockSnapshot['timestamp']
        ):
            return

        block_number = BlockNumber(int(block.message.body['execution_payload']['block_number']))
        KEYS_API_LATEST_BLOCKNUMBER.set(block_number)

        # Get modules and calculate current nonce
        # If nonce is not changed - we don't need to update keys
        try:
            modules = self.keys_api.get_modules()[0]
        except Exception as e:
            logger.error({'msg': 'Can not get modules', 'exception': str(e)})
            return

        current_nonce = sum([module['nonce'] for module in modules])
        del modules
        if self.keys_api_nonce >= current_nonce:
            return
        self.keys_api_nonce = current_nonce

        logger.info({'msg': 'Updating Lido keys'})
        try:
            modules_operators_stream = self.keys_api.get_operators_stream()
        except Exception as e:
            logger.error({'msg': 'Can not get modules operators', 'exception': str(e)})
            return
        modules_operators_dict = {}
        for mo in json_stream.requests.load(modules_operators_stream)['data']:
            staking_module_address = ""
            staking_module_operators = []
            for key, value in mo.items():
                if key == "operators":
                    for operator in value:
                        operator_index = ""
                        operator_name = ""
                        for k, v in operator.items():
                            if k == "index":
                                operator_index = v
                            if k == "name":
                                operator_name = v
                        staking_module_operators.append((operator_index, operator_name))
                elif key == "module":
                    for k, v in value.items():
                        if k == "stakingModuleAddress":
                            staking_module_address = v
            for operator_index, operator_name in staking_module_operators:
                modules_operators_dict[(staking_module_address, operator_index)] = operator_name

        try:
            fetched_lido_keys_stream = self.keys_api.get_used_lido_keys_stream()
        except Exception as e:
            logger.error({'msg': 'Can not get used lido keys', 'exception': str(e)})
            return
        for lido_key in json_stream.requests.load(fetched_lido_keys_stream)['data']:
            module_address = ""
            operator_index = ""
            pubkey = ""
            for key, value in lido_key.items():
                if key == "moduleAddress":
                    module_address = value
                elif key == "operatorIndex":
                    operator_index = value
                elif key == "key":
                    pubkey = value
            operator_name = modules_operators_dict[(module_address, operator_index)]
            self.lido_keys[pubkey] = LidoNamedKey(key=pubkey, operatorName=operator_name)

        self.keys_api_status = current_keys_status
        del modules_operators_dict

        logger.warning({'msg': f'Lido keys updated: [{len(self.lido_keys)}]'})
        KEYS_API_BLOCK_NUMBER.set(block_number)

    @duration_meter()
    def _get_head_block(self, slot=None) -> BlockDetailsResponse | None:
        def force_use_fallback_callback(result) -> bool:
            """Callback that will be called if we can't get valid head block from beacon node"""
            data, _ = result
            diff = time.time() - ((int(data['message']['slot']) * SECONDS_PER_SLOT) + self.genesis_time)
            if self.head is not None and diff > SECONDS_PER_SLOT * 4:
                # head didn't change for more than 4 slots (1/8 of epoch)
                return True
            return False

        slot = slot or 'head'
        current_head = self.consensus.get_block_details(
            slot, force_use_fallback_callback if slot == 'head' else lambda _: False
        )
        if self.head is not None and int(current_head.message.slot) == int(self.head.message.slot):
            return
        return current_head
