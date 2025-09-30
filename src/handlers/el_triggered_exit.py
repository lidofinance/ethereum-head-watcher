import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain, validator_pubkey_link
from src.keys_source.base_source import NamedKey
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import FullBlockInfo, WithdrawalRequest

logger = logging.getLogger()


class ElTriggeredExitHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.withdrawals:
            logger.debug({"msg": f"No withdrawal requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot

        our_withdrawals = [
            w for w in head.message.body.execution_requests.withdrawals
            if w.validator_pubkey in watcher.user_keys
        ]

        if not our_withdrawals:
            return

        partial_our_withdrawals: list[WithdrawalRequest] = [w for w in our_withdrawals if self._is_partial(w)]
        full_our_withdrawals: list[WithdrawalRequest] = [w for w in our_withdrawals if self._is_full(w)]

        if partial_our_withdrawals:
            self._send_partial_withdrawal_alert(watcher, slot, partial_our_withdrawals)

        if full_our_withdrawals:
            self._send_full_withdrawal_alert(watcher, slot, full_our_withdrawals)


    def _send_partial_withdrawal_alert(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherPartialELWithdrawalObserved", severity="critical")
        summary = "🚨 Partial withdrawal observed for our validator(s) (unsupported)"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_full_withdrawal_alert(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherUserELWithdrawal", severity="info")
        summary = "⚠️ Full withdrawal (exit) requested for our validator(s)"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_alert(self, watcher, alert: CommonAlert, summary: str, description: str, slot: str):
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description))

    @staticmethod
    def _is_full(withdrawal: WithdrawalRequest) -> bool:
        return int(withdrawal.amount) == 0

    @staticmethod
    def _is_partial(withdrawal: WithdrawalRequest) -> bool:
        return int(withdrawal.amount) > 0

    @staticmethod
    def _describe_withdrawal(withdrawal: WithdrawalRequest, user_keys: dict[str, NamedKey]) -> str:
        return '\n'.join([
            f'Source address: {withdrawal.source_address}',
            f'Validator: {validator_pubkey_link(withdrawal.validator_pubkey, user_keys)}',
            f'Amount: {withdrawal.amount}',
        ])
