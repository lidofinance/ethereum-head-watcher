import logging

from dataclasses import dataclass
from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain, validator_pubkey_link
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import ConsolidationRequest, FullBlockInfo, ValidatorStatus
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

class ConsolidationHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.consolidations:
            logger.info({"msg": f"No consolidation requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        our_wa = []
        our_wa_foreign_source_pubkey = []
        our_wa_foreign_target_pubkey = []
        our_wa_our_source_target_pubkey = []
        foreign_wa_our_source_pubkey = []
        foreign_wa_our_target_pubkey = []
        for consolidation in head.message.body.execution_requests.consolidations:
            if consolidation.source_address in watcher.valid_withdrawal_addresses:
                our_wa.append(consolidation)

                if consolidation.source_pubkey not in watcher.user_keys:
                    our_wa_foreign_source_pubkey.append(consolidation)
                if consolidation.target_pubkey not in watcher.user_keys:
                    our_wa_foreign_target_pubkey.append(consolidation)
                if consolidation.source_pubkey in watcher.user_keys and consolidation.target_pubkey in watcher.user_keys:
                    our_wa_our_source_target_pubkey.append(consolidation)
            else:
                if consolidation.source_pubkey in watcher.user_keys:
                    foreign_wa_our_source_pubkey.append(consolidation)
                if consolidation.target_pubkey in watcher.user_keys:
                    foreign_wa_our_target_pubkey.append(consolidation)
            # in the future we should check the type of validator WC:
            # if it is 0x02 and source_address == WCs of source validator - It's donation!

        if our_wa:
            self._send_withdrawals_address(watcher, slot, our_wa)
        if our_wa_foreign_source_pubkey:
            self._send_our_withdrawal_address_foreign_source_pubkey(watcher, slot, our_wa_foreign_source_pubkey)
        if our_wa_foreign_target_pubkey:
            self._send_our_withdrawal_address_foreign_target_pubkey(watcher, slot, our_wa_foreign_target_pubkey)
        if foreign_wa_our_source_pubkey:
            self._send_foreign_withdrawal_address_our_source_pubkey(watcher, slot, foreign_wa_our_source_pubkey)
        if foreign_wa_our_target_pubkey:
            self._send_foreign_withdrawal_address_our_target_pubkey(watcher, slot, foreign_wa_our_target_pubkey)
        if our_wa_our_source_target_pubkey:
            self._process_our_withdrawal_address_our_source_target_pubkey(watcher, slot, our_wa_our_source_target_pubkey)

    def _process_our_withdrawal_address_our_source_target_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        pubkeys = list({pk for c in consolidations for pk in (c.source_pubkey, c.target_pubkey)})
        validators = watcher.consensus.get_validators(slot, pubkeys)

        over_deposit_consolidations = []
        invalid_status_consolidations = []

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

        if over_deposit_consolidations:
            self._send_over_deposit(watcher, slot, over_deposit_consolidations)

        if invalid_status_consolidations:
            self._send_invalid_status(watcher, slot, invalid_status_consolidations)

    def _send_withdrawals_address(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationSourceWithdrawalAddress", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault source address"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_our_withdrawal_address_foreign_source_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationOurWithdrawalAddressForeignSourcePubkey", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested for foreign source validator from Withdrawal Vault address"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_our_withdrawal_address_foreign_target_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationOurWithdrawalAddressForeignTargetPubkey", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault address to foreign target validator"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_foreign_withdrawal_address_our_source_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserSourcePubkey", severity="info")
        summary = "⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)"
        self._send_alert(watcher, slot, alert, summary, consolidations)

    def _send_foreign_withdrawal_address_our_target_pubkey(
        self, watcher, slot, consolidations: list[ConsolidationRequest]
    ):
        alert = CommonAlert(name="HeadWatcherConsolidationUserTargetPubkey", severity="info")
        summary = "⚠️⚠️⚠️ Someone attempts to consolidate their validators to our validators (not from Withdrawal Vault address)"
        self._send_alert(watcher, slot, alert, summary, consolidations)

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
