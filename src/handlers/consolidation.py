import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import FullBlockInfo

logger = logging.getLogger()


class ConsolidationHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        if not head.message.body.execution_requests or not head.message.body.execution_requests.consolidations:
            logger.info({"msg": f"No consolidation requests in block [{head.message.slot}]"})
            return

        slot = head.message.slot
        for consolidation in head.message.body.execution_requests.consolidations:
            alert, summary = None, ""
            if consolidation.source_address in watcher.suspicious_addresses:
                alert = CommonAlert(name="HeadWatcherConsolidationSuspiciousSourceAddress", severity="critical")
                summary = "🔗🤗 Highly suspicious source address"
            elif consolidation.source_pubkey in watcher.user_keys:
                alert = CommonAlert(name="HeadWatcherConsolidationSourceLido", severity="moderate")
                summary = "🔗🤗 Attempt to consolidate Lido validator"
            elif consolidation.target_pubkey in watcher.user_keys:
                alert = CommonAlert(name="HeadWatcherConsolidationPossibleDonation", severity="moderate")
                summary = "🔗🤗 Someone wants to donate to Lido"
            # in the future we should check the type of validator WC:
            # if it is 0x02 and source_address == WCs of source validator - It's donation!

            if alert:
                description = (f"EL consolidation request source_address='{consolidation.source_address}', "
                               f"source_pubkey={consolidation.source_pubkey}, "
                               f"target_pubkey='{consolidation.target_pubkey}'\n"
                               f"Slot: {beaconchain(slot)}")
                self.send_alert(watcher, alert.build_body(summary, description))
