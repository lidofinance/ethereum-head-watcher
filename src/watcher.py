import logging
import time


from dataclasses import asdict

from unsync import unsync

from src import variables
from src.constants import SECONDS_PER_SLOT, SLOTS_PER_EPOCH
from src.metrics.prometheus.duration_meter import duration_meter
from src.metrics.prometheus.watcher import SLOT_NUMBER, BLOCK_NUMBER, SLASHINGS
from src.providers.consensus.client import ConsensusClient
from src.providers.consensus.typings import BlockDetailsResponse
from src.providers.keys.client import KeysAPIClient
from src.providers.keys.typings import KeysApiStatus, LidoNamedKey
from src.typings import BlockNumber, SlotNumber
from src.variables import CYCLE_SLEEP_IN_SECONDS

logger = logging.getLogger()


class Watcher:
    consensus: ConsensusClient
    keys_api: KeysAPIClient
    genesis_time: int = None

    head: BlockDetailsResponse = None

    keys_api_status: KeysApiStatus = None
    lido_keys: dict[str, LidoNamedKey] = None
    indexed_validators_keys: dict[str, str] = None

    watch_on_end_of_epoch = None
    keys_updater = None

    def __init__(self):
        self.consensus = ConsensusClient(variables.CONSENSUS_CLIENT_URI)
        self.keys_api = KeysAPIClient(variables.KEYS_API_URI)
        self.genesis_time = int(self.consensus.get_genesis().genesis_time)

    def run(self):
        while True:
            # todo: while we check current head, new head could be created
            current_head = self._get_head_block()
            if self.head is not None and current_head.message.slot == self.head.message.slot:
                logger.info({'msg': f'No new head, waiting {CYCLE_SLEEP_IN_SECONDS} seconds'})
                time.sleep(CYCLE_SLEEP_IN_SECONDS)
                continue

            if (self.keys_updater is not None and self.keys_updater.done()) or self.lido_keys is None:
                self.keys_updater = self._update_lido_keys(current_head)

            if (self.watch_on_end_of_epoch is not None and self.watch_on_end_of_epoch.done()) or self.indexed_validators_keys is None:
                self.watch_on_end_of_epoch = self._update_validators()

            if self.indexed_validators_keys is None or self.lido_keys is None:
                self.keys_updater.result()
                self.watch_on_end_of_epoch.result()

            logger.info({'msg': f'New head [{current_head.message.slot}]. Looking for slashings'})
            SLOT_NUMBER.set(current_head.message.slot)
            BLOCK_NUMBER.set(current_head.message.body['execution_payload']['block_number'])
            self.head = self._watch_on_head(current_head)

            time.sleep(CYCLE_SLEEP_IN_SECONDS)

    @duration_meter()
    def _watch_on_head(self, head: BlockDetailsResponse) -> BlockDetailsResponse:
        slashings = {
            ("proposer", "lido"): [],
            ("proposer", "other"): [],
            ("attester", "lido"): [],
            ("attester", "other"): [],
            # It's possible when we have unsynced indexed validators
            ("proposer", "unknown"): [],
            ("attester", "unknown"): [],
        }
        any_slashing = False
        for proposer_slashing in head.message.body['proposer_slashings']:
            any_slashing = True
            signed_header_1 = proposer_slashing['signed_header_1']
            proposer_key = self.indexed_validators_keys.get(signed_header_1['message']['proposer_index'])
            if proposer_key is None:
                slashings['proposer', 'unknown'].append(signed_header_1['message']['proposer_index'])
            else:
                if lido_key := self.lido_keys.get(proposer_key):
                    slashings['proposer', 'lido'].append(lido_key)
                else:
                    slashings['proposer', 'other'].append(proposer_key)

        for attester_slashing in head.message.body['attester_slashings']:
            any_slashing = True
            attestation_1 = attester_slashing['attestation_1']
            attestation_2 = attester_slashing['attestation_2']
            attesters = set(attestation_1['attesting_indices']).intersection(attestation_2['attesting_indices'])
            for attester in attesters:
                attester_key = self.indexed_validators_keys.get(attester)
                if attester_key is None:
                    slashings['attester', 'unknown'].append(attester)
                else:
                    if lido_key := self.lido_keys.get(attester_key):
                        slashings['attester', 'lido'].append(lido_key)
                    else:
                        slashings['attester', 'other'].append(attester_key)

        if not any_slashing:
            logger.info({'msg': f'No slashings in block [{head.message.slot}]'})
            # todo: clear metrics ???
        else:
            for key, value in slashings.items():
                SLASHINGS.labels(*key).set(len(value))
            logger.info({'msg': f'Slashings in block: {sum(len(value) for value in slashings.values())}'})

        return head

    @unsync
    @duration_meter()
    async def _update_validators(self):
        """
        If current time it's the end of epoch - new validators will be added to the active set
        At this moment there is no new head, but we should get validators by slot anyway
        https://github.com/ethereum/consensus-specs/blob/dev/specs/phase0/beacon-chain.md#registry-updates
        """
        now = time.time()
        diff = now - self.genesis_time
        slot = int(diff / SECONDS_PER_SLOT)
        if self.indexed_validators_keys is None or slot % SLOTS_PER_EPOCH == 0:
            logger.info({'msg': 'Updating indexed validators keys'})
            self.indexed_validators_keys = self._get_indexed_validator_keys(SlotNumber(slot))
            logger.info({'msg': f'Indexed validators keys updated: [{len(self.indexed_validators_keys)}]'})

    @unsync
    @duration_meter()
    async def _update_lido_keys(self, block: BlockDetailsResponse) -> None:
        """Return dict with `publickey` as key and `LidoNamedKey` as value"""
        current_keys_status = self.keys_api.get_status()
        if self.keys_api_status is not None and (
            current_keys_status.elBlockSnapshot['timestamp'] >= self.keys_api_status.elBlockSnapshot['timestamp']
        ):
            return

        logger.info({'msg': 'Updating Lido keys'})
        block_number = BlockNumber(int(block.message.body['execution_payload']['block_number']))
        fetched_lido_keys = self.keys_api.get_used_lido_keys(block_number)
        modules_operators = self.keys_api.get_operators(block_number)
        modules_operators_dict = {}
        for mo in modules_operators:
            for operator in mo.operators:
                modules_operators_dict[(mo.module['stakingModuleAddress'], operator['index'])] = operator['name']
        named_keys = {}
        for key in fetched_lido_keys:
            named_keys[key.key] = LidoNamedKey(
                **asdict(key), operatorName=modules_operators_dict[(key.moduleAddress, key.operatorIndex)]
            )

        self.keys_api_status = current_keys_status
        self.lido_keys = named_keys

        logger.warning({'msg': f'Lido keys updated: [{len(named_keys)}]'})

    def _get_indexed_validator_keys(self, slot: SlotNumber) -> dict[str, str]:
        return {
            validator.index: validator.validator.pubkey
            for validator in self.consensus.get_validators(slot)
        }

    @duration_meter()
    def _get_head_block(self):
        # todo: add handlers to change fallback:
        #  when head < current time significantly
        #  when head doesn't change for a long time
        return self.consensus.get_block_details('head')
