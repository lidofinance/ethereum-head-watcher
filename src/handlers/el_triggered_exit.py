import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import FullBlockInfo

logger = logging.getLogger()


class ElTriggeredExitHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.withdrawals:
            logger.debug({"msg": f"No withdrawals requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        for withdrawal in head.message.body.execution_requests.withdrawals:
            alert, summary = None, ""
            if withdrawal.source_address in watcher.suspicious_addresses:
                alert = CommonAlert(name="HeadWatcherELWithdrawalFromUserWithdrawalAddress", severity="critical")
                summary = "🔗‍🏃🚪Our validator triggered withdrawal was requested from our Withdrawal Vault address"
            elif withdrawal.validator_pubkey in watcher.user_keys:
                alert = CommonAlert(name="HeadWatcherUserELWithdrawal", severity="info")
                summary = "🔗‍🏃🚪Unexpected EL withdrawal request found"

            if alert:
                description = (f"EL withdrawals request source_address='{withdrawal.source_address}', "
                               f"validator_pubkey={withdrawal.validator_pubkey}, "
                               f"amount='{withdrawal.amount}'\n"
                               f"Slot: {beaconchain(slot)}")
                self.send_alert(watcher, alert.build_body(summary, description))
