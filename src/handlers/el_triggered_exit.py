import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain, validator_pubkey_link
from src.keys_source.base_source import NamedKey
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import FullBlockInfo, WithdrawalRequest
from src.variables import ADDITIONAL_ALERTMANAGER_LABELS

logger = logging.getLogger()


class ElTriggeredExitHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.withdrawals:
            logger.debug({"msg": f"No withdrawal requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        withdrawals = head.message.body.execution_requests.withdrawals
        valid_withdrawal_addresses = watcher.valid_withdrawal_addresses

        user_withdrawals = [
            w
            for w in withdrawals
            if w.source_address in valid_withdrawal_addresses and w.validator_pubkey in watcher.user_keys
        ]

        user_partial_withdrawals = [w for w in user_withdrawals if self._is_partial(w)]
        user_full_withdrawals = [w for w in user_withdrawals if self._is_full(w)]

        requests_from_our_source_for_foreign_validators = [
            w
            for w in withdrawals
            if w.source_address in valid_withdrawal_addresses and w.validator_pubkey not in watcher.user_keys
        ]

        requests_from_unknown_source_for_our_validators = [
            w
            for w in withdrawals
            if w.source_address not in valid_withdrawal_addresses and w.validator_pubkey in watcher.user_keys
        ]

        if user_full_withdrawals:
            self._send_full_withdrawal_alert(watcher, slot, user_full_withdrawals)

        if user_partial_withdrawals:
            self._send_partial_withdrawal_alert(watcher, slot, user_partial_withdrawals)

        if requests_from_our_source_for_foreign_validators:
            self._send_request_from_our_source_for_foreign_validators_alert(
                watcher, slot, requests_from_our_source_for_foreign_validators
            )

        if requests_from_unknown_source_for_our_validators:
            self._send_request_from_unknown_source_for_our_validators_alert(
                watcher, slot, requests_from_unknown_source_for_our_validators
            )

    def _send_full_withdrawal_alert(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherFullELWithdrawalObserved", severity="info")
        summary = "⚠️ Full withdrawal (exit) requested for our validator(s)"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_partial_withdrawal_alert(self, watcher, slot: str, withdrawals: list[WithdrawalRequest]):
        alert = CommonAlert(name="HeadWatcherPartialELWithdrawalObserved", severity="critical")
        summary = "🚨 Partial withdrawal observed for our validator(s) (unsupported)"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_request_from_our_source_for_foreign_validators_alert(
        self, watcher, slot: str, withdrawals: list[WithdrawalRequest]
    ):
        alert = CommonAlert(name="HeadWatcherELRequestFromOurSourceForForeignValidators", severity="critical")
        summary = "🚨️ Withdrawal request from our source address for non-user validator(s) observed"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot, ADDITIONAL_ALERTMANAGER_LABELS)

    def _send_request_from_unknown_source_for_our_validators_alert(
        self, watcher, slot: str, withdrawals: list[WithdrawalRequest]
    ):
        alert = CommonAlert(name="HeadWatcherELRequestFromUnknownSourceForOurValidators", severity="critical")
        summary = "🚨 Withdrawal request from unknown source address for our validator(s) observed"
        description = '\n\n'.join(self._describe_withdrawal(w, watcher.user_keys) for w in withdrawals)
        self._send_alert(watcher, alert, summary, description, slot)

    def _send_alert(
        self, watcher, alert: CommonAlert, summary: str, description: str, slot: str, additional_labels=None
    ):
        description += f'\n\nSlot: {beaconchain(slot)}'
        self.send_alert(watcher, alert.build_body(summary, description, additional_labels))

    @staticmethod
    def _is_full(withdrawal: WithdrawalRequest) -> bool:
        return int(withdrawal.amount) == 0

    @staticmethod
    def _is_partial(withdrawal: WithdrawalRequest) -> bool:
        return int(withdrawal.amount) > 0

    @staticmethod
    def _describe_withdrawal(withdrawal: WithdrawalRequest, user_keys: dict[str, NamedKey]) -> str:
        return '\n'.join(
            [
                f'Source address (EL): {withdrawal.source_address}',
                f'Validator pubkey: {validator_pubkey_link(withdrawal.validator_pubkey, user_keys)}',
                f'Amount (gwei): {withdrawal.amount}',
            ]
        )
