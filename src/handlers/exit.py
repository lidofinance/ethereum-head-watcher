import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Optional

from unsync import unsync
from web3 import Web3

from src import variables
from src.alerts.common import CommonAlert
from src.handlers.handler import WatcherHandler
from src.keys_source.base_source import SourceType
from src.metrics.prometheus.duration_meter import duration_meter
from src.providers.consensus.typings import BlockDetailsResponse, FullBlockInfo
from src.typings import BlockNumber
from src.utils.events import get_events_in_range
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

@dataclass
class ExitedOperatorValidators:
    operator: str
    validator_indexes: list[int]


class ExitsHandler(WatcherHandler):
    last_total_requests_processed = 0
    last_requested_validator_indexes: dict[int, set[int]]

    def __init__(self):
        super().__init__()
        self.last_requested_validator_indexes = {}

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

            description = ''
            all_expected = set().union(*self.last_requested_validator_indexes.values())
            by_operator: defaultdict[tuple[int, int], ExitedOperatorValidators] = defaultdict(
                lambda: ExitedOperatorValidators(operator='', validator_indexes=[])
            )

            for user_exit in user_exits:
                if int(user_exit.index) in all_expected:
                    continue

                key = (int(user_exit.module_index), int(user_exit.operator_index))
                by_operator[key].operator = user_exit.operator
                by_operator[key].validator_indexes.append(int(user_exit.index))

            if by_operator:
                total_exits = 0
                for operator_exits in by_operator.values():
                    total_exits += len(operator_exits.validator_indexes)
                    description += f'\n{operator_exits.operator} - '
                    description += (
                        "["
                        + ', '.join(
                            [
                                f'[{validator_index}](http://{NETWORK_NAME}.beaconcha.in/validator/{validator_index})'
                                for validator_index in operator_exits.validator_indexes
                            ]
                        )
                        + "]"
                    )
                description += (
                    f'\n\nslot: [{block.message.slot}](https://{NETWORK_NAME}.beaconcha.in/slot/{block.message.slot})'
                )
                alert = CommonAlert(name="HeadWatcherUserUnexpectedExit", severity="critical")
                summary = f'🚨🚨🚨 {total_exits} Our validators were unexpectedly exited! 🚨🚨🚨'
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
            self.send_alert(watcher, alert.build_body(summary, description, ADDITIONAL_ALERTMANAGER_LABELS))

    @duration_meter()
    def _update_last_requested_validator_indexes(self, watcher, block: BlockDetailsResponse) -> None:
        """Update local cache with last validator indexes requested to exit by VEBO"""
        if not watcher.keys_source.modules_operators_dict:
            return

        current_block_number = int(block.message.body.execution_payload.block_number)

        # todo:
        #  should we look at the refSlot for report?
        #  compere local last processed refSlot and calculated refSlot (get from contract + frame size)
        #  instead of getting total_requests_processed every block with lido exits
        total_requests_processed = (
            watcher.execution.lido_contracts.validators_exit_bus_oracle.functions.getTotalRequestsProcessed().call(
                block_identifier=current_block_number
            )
        )

        if total_requests_processed <= self.last_total_requests_processed:
            return

        logger.info({'msg': 'Getting last validator indexes requested to exit by VEBO'})

        lookup_window = Web3.to_int(watcher.execution.lido_contracts.oracle_daemon_config.functions.get(
            'EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS'
        ).call(block_identifier=current_block_number))

        last_cached_block = -1
        if self.last_requested_validator_indexes:
            last_cached_block = max(self.last_requested_validator_indexes)

        l_block = max(last_cached_block + 1, current_block_number - lookup_window)

        events = get_events_in_range(
            watcher.execution.lido_contracts.validators_exit_bus_oracle.events.ValidatorExitRequest,
            l_block=BlockNumber(l_block),
            r_block=BlockNumber(current_block_number),
        )

        for event in events:
            if event['blockNumber'] not in self.last_requested_validator_indexes:
                self.last_requested_validator_indexes[event['blockNumber']] = set()
            self.last_requested_validator_indexes[event['blockNumber']].add(event['args']['validatorIndex'])

        for cached_block in list(self.last_requested_validator_indexes.keys()):
            if cached_block < current_block_number - lookup_window:
                del self.last_requested_validator_indexes[cached_block]

        self.last_total_requests_processed = total_requests_processed
