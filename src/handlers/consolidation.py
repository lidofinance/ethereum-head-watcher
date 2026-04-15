import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain, validator_pubkey_link
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import ConsolidationRequest, FullBlockInfo
from src.variables import ADDITIONAL_ALERTMANAGER_LABELS

logger = logging.getLogger()


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
        foreign_wa_our_source_pubkey = []
        foreign_wa_our_target_pubkey = []
        for consolidation in head.message.body.execution_requests.consolidations:
            if consolidation.source_address in watcher.valid_withdrawal_addresses:
                our_wa.append(consolidation)

                if consolidation.source_pubkey not in watcher.user_keys:
                    our_wa_foreign_source_pubkey.append(consolidation)
                if consolidation.target_pubkey not in watcher.user_keys:
                    our_wa_foreign_target_pubkey.append(consolidation)
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
