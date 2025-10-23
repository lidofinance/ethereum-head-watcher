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
        withdrawal_address, source_pubkey, target_pubkey = [], [], []
        for consolidation in head.message.body.execution_requests.consolidations:
            if consolidation.source_address in watcher.valid_withdrawal_addresses:
                withdrawal_address.append(consolidation)
            elif consolidation.source_pubkey in watcher.user_keys:
                source_pubkey.append(consolidation)
            elif consolidation.target_pubkey in watcher.user_keys:
                target_pubkey.append(consolidation)
            # in the future we should check the type of validator WC:
            # if it is 0x02 and source_address == WCs of source validator - It's donation!

        if withdrawal_address:
            self._send_withdrawals_address(watcher, slot, withdrawal_address)
        if source_pubkey:
            self._send_source_pubkey(watcher, slot, source_pubkey)
        if target_pubkey:
            self._send_target_pubkey(watcher, slot, target_pubkey)

    def _send_withdrawals_address(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationSourceWithdrawalAddress", severity="critical")
        summary = "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault source address"
        self._send_alert(watcher, slot, alert, summary, consolidations, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_source_pubkey(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationUserSourcePubkey", severity="info")
        summary = "⚠️⚠️⚠️ Consolidation was requested for our validators"
        self._send_alert(watcher, slot, alert, summary, consolidations)

    def _send_target_pubkey(self, watcher, slot, consolidations: list[ConsolidationRequest]):
        alert = CommonAlert(name="HeadWatcherConsolidationUserTargetPubkey", severity="info")
        summary = "⚠️⚠️⚠️ Someone attempts to consolidate their validators to our validators"
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
