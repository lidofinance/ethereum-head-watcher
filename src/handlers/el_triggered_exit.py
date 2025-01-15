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
            logger.debug({"msg": f"No withdrawals requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        our_withdrawal_address, our_validators = [], []
        for withdrawal in head.message.body.execution_requests.withdrawals:
            if withdrawal.source_address in watcher.valid_withdrawal_addresses:
                our_withdrawal_address.append(withdrawal)
            elif withdrawal.validator_pubkey in watcher.user_keys:
                our_validators.append(withdrawal)

        if our_withdrawal_address:
            self._send_withdrawal_address_alerts(watcher, slot, our_withdrawal_address)
        if our_validators:
            self._send_our_validators_alert(watcher, slot, our_validators)

    def _send_withdrawal_address_alerts(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherELWithdrawalFromUserWithdrawalAddress", severity="critical")
        summary = "🔗‍🏃🚪Our validator triggered withdrawal was requested from our Withdrawal Vault address"
        description = '\n\n'.join(map(lambda w: self._describe_withdrawal(w, watcher.user_keys), withdrawals))
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_our_validators_alert(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherUserELWithdrawal", severity="info")
        summary = "🔗‍🏃🚪Our validator triggered withdrawal was requested"
        description = '\n\n'.join(map(lambda w: self._describe_withdrawal(w, watcher.user_keys), withdrawals))
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_alert(self, watcher, alert: CommonAlert, summary: str, description: str, slot: str):
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description))

    @staticmethod
    def _describe_withdrawal(withdrawal: WithdrawalRequest, user_keys: dict[str, NamedKey]) -> str:
        return '\n'.join([
            f'Source address: {withdrawal.source_address}',
            f'Validator: {validator_pubkey_link(withdrawal.validator_pubkey, user_keys)}',
            f'Amount: {withdrawal.amount}',
        ])
