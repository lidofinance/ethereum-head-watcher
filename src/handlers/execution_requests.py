import logging

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import FullBlockInfo
from src.utils.execution_requests import ExecutionRequestsSource

logger = logging.getLogger()

# A single unread envelope is usually a hiccup of a node, alert only when it does not recover
UNAVAILABLE_BLOCKS_BEFORE_ALERT = 3
# Alerts live for 5 seconds in Alertmanager, so a lasting outage has to be reported again from time
# to time. 150 blocks is around half an hour.
UNAVAILABLE_ALERT_REPEAT_IN_BLOCKS = 150


class ExecutionRequestsHandler(WatcherHandler):
    """
    Watches the ability of the watcher to read execution requests rather than the chain itself.

    Since Gloas (EIP-7732) the requests are read from the payload envelope of the parent block. When
    a payload was applied to the state but its envelope can not be read, the consolidation and the EL
    triggered exit handlers see nothing and stay silent, which is indistinguishable from a chain
    without requests. This handler makes that gap visible.
    """

    unavailable_blocks: int
    unavailable_since_slot: str

    def __init__(self):
        super().__init__()
        self.unavailable_blocks = 0
        self.unavailable_since_slot = ''

    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        ctx = watcher.execution_requests(head)

        if ctx.source != ExecutionRequestsSource.UNAVAILABLE:
            if self.unavailable_blocks >= UNAVAILABLE_BLOCKS_BEFORE_ALERT:
                logger.warning(
                    {
                        'msg': f'Execution requests are readable again at block [{head.message.slot}] '
                        f'after {self.unavailable_blocks} block(s)'
                    }
                )
            self.unavailable_blocks = 0
            self.unavailable_since_slot = ''
            return

        if not self.unavailable_blocks:
            self.unavailable_since_slot = ctx.request_slot
        self.unavailable_blocks += 1

        logger.warning(
            {
                'msg': f'Execution requests are not readable at block [{head.message.slot}], '
                f'{self.unavailable_blocks} block(s) in a row'
            }
        )

        if self._should_alert():
            self._send_unavailable_alert(watcher, head)

    def _should_alert(self) -> bool:
        """Alert once the outage is confirmed, then repeat it while it lasts"""
        if self.unavailable_blocks < UNAVAILABLE_BLOCKS_BEFORE_ALERT:
            return False
        blocks_since_first_alert = self.unavailable_blocks - UNAVAILABLE_BLOCKS_BEFORE_ALERT
        return blocks_since_first_alert % UNAVAILABLE_ALERT_REPEAT_IN_BLOCKS == 0

    def _send_unavailable_alert(self, watcher, head: FullBlockInfo):
        alert = CommonAlert(name="HeadWatcherExecutionRequestsUnavailable", severity="info")
        summary = "**🕶️ Execution requests can not be read**"
        description = '\n'.join(
            [
                'Payloads are applied to the state but their envelopes can not be read, so validator '
                'consolidations and EL triggered exits are not checked.',
                f'Blocks in a row: {self.unavailable_blocks}, since slot: '
                f'{beaconchain(self.unavailable_since_slot)}',
                f'Last checked slot: {beaconchain(head.message.slot)}',
            ]
        )
        self.send_alert(watcher, alert.build_body(summary, description))
