import threading

from unsync import unsync

from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.handlers.helpers import beaconchain
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockHeaderResponseData, ChainReorgEvent


class ForkHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: BlockHeaderResponseData):
        def _known_header(root: str) -> BlockHeaderResponseData:
            header, *_ = [h for h in [*watcher.handled_headers, head] if h.root == root] or [None]
            return header

        head_parent_is_alerted = False

        chain_reorgs = [*watcher.chain_reorgs.values()]

        for chain_reorg in chain_reorgs:
            known_header = _known_header(chain_reorg.new_head_block)
            known_parent = _known_header(known_header.header.message.parent_root) if known_header else None
            if not known_header or not known_parent:
                self._send_reorg_alert(watcher, chain_reorg)
                if chain_reorg.new_head_block == head.header.message.parent_root:
                    head_parent_is_alerted = True
            lock = threading.Lock()
            with lock:
                del watcher.chain_reorgs[chain_reorg.slot]

        if watcher.handled_headers and not head_parent_is_alerted:
            known_parent = _known_header(head.header.message.parent_root)
            if not known_parent:
                self._send_unhandled_head_alert(watcher, head)

    def _send_reorg_alert(self, watcher, chain_reorg: ChainReorgEvent):
        alert = CommonAlert(name="UnhandledChainReorg", severity="info")
        links = "\n".join(
            [
                beaconchain(s)
                for s in range(int(chain_reorg.slot) - int(chain_reorg.depth), int(chain_reorg.slot) + 1)
            ]
        )
        summary = "🔗‍🔀 Unhandled slots after chain reorganization"
        description = f"Reorg depth is {chain_reorg.depth} slots.\nPlease, check possible unhandled slots: {links}"
        self.send_alert(watcher, alert.build_body(summary, description))

    def _send_unhandled_head_alert(self, watcher, head: BlockHeaderResponseData):
        alert = CommonAlert(name="UnhandledHead", severity="info")
        summary = "🫳🐦 Unhandled chain slot"
        additional_msg = ""
        diff = int(head.header.message.slot) - int(watcher.handled_headers[-1].header.message.slot) - 2
        if diff > 0:
            additional_msg = f"\nAnd {diff} slot(s) before it"
        parent_root = head.header.message.parent_root
        description = f"Please, check unhandled slot: {beaconchain(parent_root)}{additional_msg}"
        self.send_alert(watcher, alert.build_body(summary, description))
