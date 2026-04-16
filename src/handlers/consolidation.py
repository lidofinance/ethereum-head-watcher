import logging

from dataclasses import dataclass
from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain, validator_pubkey_link
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockDetailsResponse, ConsolidationRequest, FullBlockInfo, ValidatorStatus
from src.utils.exit import ValidatorExitsInfo, get_last_requested_validator_exit_indexes
from src.variables import ADDITIONAL_ALERTMANAGER_LABELS

logger = logging.getLogger()

@dataclass
class OverDepositConsolidation:
    source_address: str
    source_index: int
    source_pubkey: str
    source_balance: int
    target_index: int
    target_pubkey: str
    target_balance: int

@dataclass
class InvalidStatusConsolidation:
    source_address: str
    source_index: int
    source_pubkey: str
    source_status: ValidatorStatus
    source_exit_epoch: int
    target_index: int
    target_pubkey: str
    target_status: ValidatorStatus
    target_exit_epoch: int

@dataclass
class RequestedToExitConsolidation:
    source_address: str
    source_index: int
    source_pubkey: str
    target_index: int
    target_pubkey: str

class ConsolidationHandler(WatcherHandler):
    last_total_vebo_requests_processed = 0
    last_requested_exit_indexes: dict[int, set[int]]

    def __init__(self):
        super().__init__()
        self.last_requested_exit_indexes = {}

    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.consolidations:
            logger.info({"msg": f"No consolidation requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        user_wa = []
        user_wa_foreign_source_pubkey = []
        user_wa_foreign_target_pubkey = []
        user_wa_user_source_target_pubkey = []
        foreign_wa_user_source_pubkey = []
        foreign_wa_user_target_pubkey = []
        for consolidation in head.message.body.execution_requests.consolidations:
            if consolidation.source_address in watcher.valid_withdrawal_addresses:
                user_wa.append(consolidation)

                if consolidation.source_pubkey not in watcher.user_keys:
                    user_wa_foreign_source_pubkey.append(consolidation)
                if consolidation.target_pubkey not in watcher.user_keys:
                    user_wa_foreign_target_pubkey.append(consolidation)
                if consolidation.source_pubkey in watcher.user_keys and consolidation.target_pubkey in watcher.user_keys:
                    user_wa_user_source_target_pubkey.append(consolidation)
            else:
                if consolidation.source_pubkey in watcher.user_keys:
                    foreign_wa_user_source_pubkey.append(consolidation)
                if consolidation.target_pubkey in watcher.user_keys:
                    foreign_wa_user_target_pubkey.append(consolidation)
            # in the future we should check the type of validator WC:
            # if it is 0x02 and source_address == WCs of source validator - It's donation!

        if user_wa:
            self._send_withdrawals_address(watcher, slot, user_wa)
        if user_wa_foreign_source_pubkey:
            self._send_user_withdrawal_address_foreign_source_pubkey(watcher, slot, user_wa_foreign_source_pubkey)
        if user_wa_foreign_target_pubkey:
            self._send_user_withdrawal_address_foreign_target_pubkey(watcher, slot, user_wa_foreign_target_pubkey)
        if foreign_wa_user_source_pubkey:
            self._send_foreign_withdrawal_address_user_source_pubkey(watcher, slot, foreign_wa_user_source_pubkey)
        if foreign_wa_user_target_pubkey:
            self._send_foreign_withdrawal_address_user_target_pubkey(watcher, slot, foreign_wa_user_target_pubkey)
        if user_wa_user_source_target_pubkey:
            self._process_user_withdrawal_address_user_source_target_pubkey(watcher, head, user_wa_user_source_target_pubkey)

    def _process_user_withdrawal_address_user_source_target_pubkey(
        self, watcher, block: FullBlockInfo, consolidations: list[ConsolidationRequest]
    ):
        slot = block.message.slot
        pubkeys = list({pk for c in consolidations for pk in (c.source_pubkey, c.target_pubkey)})
        validators = watcher.consensus.get_validators(slot, pubkeys)
        pending_consolidations = watcher.consensus.get_pending_consolidations(slot)
        self._update_last_requested_exit_indexes(watcher, block)

        all_exit_indexes = set().union(*self.last_requested_exit_indexes.values())

        over_deposit_consolidations = []
        invalid_status_consolidations = []
        rejected_consolidations = []
        requested_to_exit_consolidations = []

        for consolidation in consolidations:
            source_validator = next((v for v in validators if v.validator.pubkey == consolidation.source_pubkey), None)
            target_validator = next((v for v in validators if v.validator.pubkey == consolidation.target_pubkey), None)

            if source_validator is None:
                raise ValueError(f'Unknown source validator pubkey: {consolidation.source_pubkey}')
            if target_validator is None:
                raise ValueError(f'Unknown target validator pubkey: {consolidation.target_pubkey}')

            if int(source_validator.balance) + int(target_validator.balance) > 2048000000000:
                over_deposit_consolidations.append(
                    OverDepositConsolidation(
                        source_address=consolidation.source_address,
                        source_index=int(source_validator.index),
                        source_pubkey=consolidation.source_pubkey,
                        source_balance=int(source_validator.balance),
                        target_index=int(target_validator.index),
                        target_pubkey=consolidation.target_pubkey,
                        target_balance=int(target_validator.balance),
                    )
                )

            if source_validator.status != ValidatorStatus.ACTIVE_ONGOING.value or target_validator.status != ValidatorStatus.ACTIVE_ONGOING.value:
                invalid_status_consolidations.append(
                    InvalidStatusConsolidation(
                        source_address=consolidation.source_address,
                        source_index=int(source_validator.index),
                        source_pubkey=consolidation.source_pubkey,
                        source_status=source_validator.status,
                        source_exit_epoch=int(source_validator.validator.exit_epoch),
                        target_index=int(target_validator.index),
                        target_pubkey=consolidation.target_pubkey,
                        target_status=target_validator.status,
                        target_exit_epoch=int(target_validator.validator.exit_epoch),
                    )
                )

            pending_consolidation = next((pc for pc in pending_consolidations if pc.source_index == source_validator.index and pc.target_index == target_validator.index), None)
            if pending_consolidation is None:
                rejected_consolidations.append(consolidation)

            if int(source_validator.index) in all_exit_indexes or int(target_validator.index) in all_exit_indexes:
                requested_to_exit_consolidations.append(
                    RequestedToExitConsolidation(
                        source_address=consolidation.source_address,
                        source_index=int(source_validator.index),
                        source_pubkey=consolidation.source_pubkey,
                        target_index=int(target_validator.index),
                        target_pubkey=consolidation.target_pubkey,
                    )
                )

        if over_deposit_consolidations:
            self._send_over_deposit(watcher, slot, over_deposit_consolidations)
        if invalid_status_consolidations:
            self._send_invalid_status(watcher, slot, invalid_status_consolidations)
        if rejected_consolidations:
            self._send_rejected(watcher, slot, rejected_consolidations)
        if requested_to_exit_consolidations:
            self._send_requested_to_exit(watcher, slot, requested_to_exit_consolidations)

    def _send_withdrawals_address(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationSourceWithdrawalAddress", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault source address"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_user_withdrawal_address_foreign_source_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserWithdrawalAddressForeignSourcePubkey", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested for foreign source validator from Withdrawal Vault address"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_user_withdrawal_address_foreign_target_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserWithdrawalAddressForeignTargetPubkey", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault address to foreign target validator"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_foreign_withdrawal_address_user_source_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserSourcePubkey", severity="info")
        summary = "⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)"
        self._send_alert(watcher, slot, alert, summary, consolidations)

    def _send_foreign_withdrawal_address_user_target_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserTargetPubkey", severity="info")
        summary = "⚠️⚠️⚠️ Someone attempts to consolidate their validators to our validators (not from Withdrawal Vault address)"
        self._send_alert(watcher, slot, alert, summary, consolidations)

    def _send_rejected(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationCLRejected", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was rejected on CL"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_over_deposit(self, watcher, slot: str, consolidations: list[OverDepositConsolidation]):
        alert = CommonAlert(name="HeadWatcherConsolidationOverDeposit", severity="critical")
        summary = "⚠️⚠️⚠️ Total balance of source and target validators during consolidation is greater than 2048 ETH"
        description = '\n\n'.join(self._describe_over_deposit_consolidation(c, watcher.user_keys) for c in consolidations)
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))

    def _send_invalid_status(self, watcher, slot: str, consolidations: list[InvalidStatusConsolidation]):
        alert = CommonAlert(name="HeadWatcherConsolidationInvalidStatus", severity="critical")
        summary = "⚠️⚠️⚠️ Attempt to consolidate validators whose status is not active"
        description = '\n\n'.join(self._describe_invalid_status_consolidation(c, watcher.user_keys) for c in consolidations)
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))

    def _send_requested_to_exit(self, watcher, slot: str, consolidations: list[RequestedToExitConsolidation]):
        alert = CommonAlert(name="HeadWatcherConsolidationRequestedToExit", severity="critical")
        summary = "⚠️⚠️⚠️ Attempt to consolidate validators that were requested to exit by VEBO"
        description = '\n\n'.join(self._describe_requested_to_exit_consolidation(c, watcher.user_keys) for c in consolidations)
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))

    def _send_alert(self, watcher, slot: str, alert: CommonAlert, summary: str,
                    consolidations: list[ConsolidationRequest], additional_labels=None) -> None:
        description = '\n\n'.join(self._describe_consolidation(c, watcher.user_keys) for c in consolidations)
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description, additional_labels))

    @staticmethod
    def _describe_consolidation(consolidation: ConsolidationRequest, keys):
        return '\n'.join([
            f'Request source address: {consolidation.source_address}',
            f'Source: {validator_pubkey_link(consolidation.source_pubkey, keys)}',
            f'Target: {validator_pubkey_link(consolidation.target_pubkey, keys)}',
        ])

    @staticmethod
    def _describe_over_deposit_consolidation(consolidation: OverDepositConsolidation, keys):
        return '\n'.join([
            f'Request source address: {consolidation.source_address}',
            f'Source index: {consolidation.source_index}',
            f'Source pubkey: {validator_pubkey_link(consolidation.source_pubkey, keys)}',
            f'Source balance (gwei): {consolidation.source_balance}',
            f'Target index: {consolidation.target_index}',
            f'Target pubkey: {validator_pubkey_link(consolidation.target_pubkey, keys)}',
            f'Target balance (gwei): {consolidation.target_balance}',
        ])

    @staticmethod
    def _describe_invalid_status_consolidation(consolidation: InvalidStatusConsolidation, keys):
        return '\n'.join([
            f'Request source address: {consolidation.source_address}',
            f'Source index: {consolidation.source_index}',
            f'Source pubkey: {validator_pubkey_link(consolidation.source_pubkey, keys)}',
            f'Source status: {consolidation.source_status}',
            f'Source exit epoch: {consolidation.source_exit_epoch}',
            f'Target index: {consolidation.target_index}',
            f'Target pubkey: {validator_pubkey_link(consolidation.target_pubkey, keys)}',
            f'Target status: {consolidation.target_status}',
            f'Target exit epoch: {consolidation.target_exit_epoch}',
        ])

    @staticmethod
    def _describe_requested_to_exit_consolidation(consolidation: RequestedToExitConsolidation, keys):
        return '\n'.join([
            f'Request source address: {consolidation.source_address}',
            f'Source index: {consolidation.source_index}',
            f'Source pubkey: {validator_pubkey_link(consolidation.source_pubkey, keys)}',
            f'Target index: {consolidation.target_index}',
            f'Target pubkey: {validator_pubkey_link(consolidation.target_pubkey, keys)}',
        ])

    @duration_meter()
    def _update_last_requested_exit_indexes(self, watcher, block: BlockDetailsResponse) -> None:
        """Update local cache with last validator indexes requested to exit by VEBO"""

        exits_info = ValidatorExitsInfo(
            last_total_requests_processed=self.last_total_vebo_requests_processed,
            last_requested_exit_indexes=self.last_requested_exit_indexes,
        )

        updated_exits_info = get_last_requested_validator_exit_indexes(watcher, block, exits_info)

        self.last_total_vebo_requests_processed = updated_exits_info.last_total_requests_processed
        self.last_requested_exit_indexes = updated_exits_info.last_requested_exit_indexes
