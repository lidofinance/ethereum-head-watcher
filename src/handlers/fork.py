from unsync import unsync

from src.alerts.slashing import CommonAlert
from src.handlers.handler import WatcherHandler
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockHeaderResponseData, ChainReorgEvent
from src.variables import NETWORK_NAME


class ForkHandler(WatcherHandler):
    @unsync
    @duration_meter()
    def handle(self, watcher, head: BlockHeaderResponseData):
        def _known_header(root: str) -> BlockHeaderResponseData:
            header, *_ = [h for h in [*watcher.handled_headers, head] if h.root == root]
            return header

        for chain_reorg in watcher.chain_reorgs.values():
            known_header = _known_header(chain_reorg.new_head_block)
            known_parent = _known_header(known_header.header.message.parent_root)
            if not known_header or not known_parent:
                self._send_alert(watcher, chain_reorg)
                del watcher.chain_reorgs[chain_reorg.slot]
                break
            del watcher.chain_reorgs[chain_reorg.slot]

    def _send_alert(self, watcher, chain_reorg: ChainReorgEvent):
        alert = CommonAlert(name="UnhandledChainReorg", severity="info")
        links = "\n".join(
            [
                f"[{s}](https://{NETWORK_NAME}.beaconcha.in/slot/{s})"
                for s in range(int(chain_reorg.slot) - int(chain_reorg.depth), int(chain_reorg.slot) + 1)
            ]
        )
        summary = "🔗‍🔀Unhandled slots after chain reorganization"
        description = f"Reorg depth is ${chain_reorg.depth} slots.\nPlease, check possible unhandled slots: {links}"
        watcher.alertmanager.send_alerts([alert.build_body(summary, description)])
