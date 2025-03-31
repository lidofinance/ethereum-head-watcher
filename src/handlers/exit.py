import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Optional

from unsync import unsync

from src import variables
from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.keys_source.base_source import SourceType
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockDetailsResponse, FullBlockInfo
from src.variables import ADDITIONAL_ALERTMANAGER_LABELS, NETWORK_NAME

logger = logging.getLogger()

Owner = Literal['user', 'other', 'unknown']


@dataclass
class ExitInfo:
    index: str
    owner: Owner
    operator: Optional[str] = None
    operator_index: Optional[str] = None
    module_index: Optional[str] = None


class ExitsHandler(WatcherHandler):
    last_total_requests_processed = 0
    last_requested_validator_indexes: dict[tuple[int, int], int] = {}

    @unsync
    @duration_meter()
    def handle(self, watcher, head: FullBlockInfo):
        exits = []
        for voluntary_exit in head.message.body.voluntary_exits:
            validator_index = voluntary_exit.message.validator_index
            validator_key = watcher.indexed_validators_keys.get(validator_index)
            if validator_key is None:
                exits.append(ExitInfo(index=validator_index, owner='unknown'))
            else:
                if user_key := watcher.user_keys.get(validator_key):
                    exits.append(
                        ExitInfo(
                            index=validator_index,
                            owner='user',
                            operator=user_key.operatorName,
                            operator_index=user_key.operatorIndex,
                            module_index=user_key.moduleIndex,
                        )
                    )
                else:
                    exits.append(
                        ExitInfo(
                            index=validator_index,
                            owner='other',
                        )
                    )
        if watcher.disable_unexpected_exit_alerts:
            exits = [e for e in exits if e.owner == 'user' and str(e.module_index) not in watcher.disable_unexpected_exit_alerts]
        if not exits:
            logger.debug({'msg': f'No exits in block [{head.message.slot}]'})
        else:
            logger.info({'msg': f'Exits in block [{head.message.slot}]: {len(exits)}'})
            self._send_alerts(watcher, head, exits)

    def _send_alerts(self, watcher, block: FullBlockInfo, exits):
        user_exits = [s for s in exits if s.owner == 'user']
        unknown_exits = [s for s in exits if s.owner == 'unknown']
        if user_exits:
            if variables.KEYS_SOURCE == SourceType.KEYS_API.value:
                self._update_last_requested_validator_indexes(watcher, block)
            summary = f'🚨🚨🚨 {len(user_exits)} Our validators were unexpected exited! 🚨🚨🚨'
            description = ''
            by_operator: dict[str, list] = defaultdict(list)
            for user_exit in user_exits:
                operator_last_exited_index = self.last_requested_validator_indexes.get(
                    (user_exit.module_index, user_exit.operator_index), 0
                )
                if int(user_exit.index) > operator_last_exited_index:
                    by_operator[str(user_exit.operator)].append(user_exit)
            if by_operator:
                for operator, operator_exits in by_operator.items():
                    description += f'\n{operator} -'
                    description += (
                        "["
                        + ', '.join(
                            [
                                f'[{exit.index}](http://{NETWORK_NAME}.beaconcha.in/validator/{exit.index})'
                                for exit in operator_exits
                            ]
                        )
                        + "]"
                    )
                description += (
                    f'\n\nslot: [{block.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{block.message.slot})'
                )
                alert = CommonAlert(name="HeadWatcherUserUnexpectedExit", severity="critical")
                self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))
        if unknown_exits:
            summary = f'🚨 {len(unknown_exits)} unknown validators were exited!'
            description = (
                "["
                + ', '.join(
                    [
                        f'[{exit.index}](http://{NETWORK_NAME}.beaconcha.in/validator/{exit.index})'
                        for exit in unknown_exits
                    ]
                )
                + "]"
            )
            description += (
                f'\n\nslot: [{block.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{block.message.slot})'
            )
            alert = CommonAlert(name="HeadWatcherUnknownExit", severity="critical")
            self.send_alert(watcher, alert.build_body(summary, description))

    @duration_meter()
    def _update_last_requested_validator_indexes(self, watcher, block: BlockDetailsResponse) -> None:
        """Update last requested to exit validator indexes"""
        if not watcher.keys_source.modules_operators_dict:
            return
        # todo:
        #  should we look at the refSlot for report?
        #  compere local last processed refSlot and calculated refSlot (get from contract + frame size)
        #  instead of getting total_requests_processed every block with lido exits
        total_requests_processed = (
            watcher.execution.lido_contracts.validators_exit_bus_oracle.functions.getTotalRequestsProcessed().call(
                block_identifier=int(block.message.body.execution_payload.block_number)
            )
        )
        if total_requests_processed <= self.last_total_requests_processed:
            return
        logger.info({'msg': 'Get last requested to exit Lido validator indexes'})
        for module_index, operators in watcher.keys_source.modules_operators_dict.items():
            requested_validator_indexes = (
                watcher.execution.lido_contracts.validators_exit_bus_oracle.functions.getLastRequestedValidatorIndices(
                    module_index, operators
                ).call(block_identifier=int(block.message.body.execution_payload.block_number))
            )
            for operator_index, validator_index in enumerate(requested_validator_indexes):
                self.last_requested_validator_indexes[(int(module_index), operator_index)] = validator_index
        self.last_total_requests_processed = total_requests_processed
