import logging
from dataclasses import dataclass

from web3 import Web3

from src.providers.consensus.typings import BlockDetailsResponse
from src.typings import BlockNumber
from src.utils.events import get_events_in_range

logger = logging.getLogger()


@dataclass
class ValidatorExitsInfo:
    last_total_requests_processed: int
    last_requested_exit_indexes: dict[int, set[int]]


def get_last_requested_validator_exit_indexes(
    watcher, block: BlockDetailsResponse, exits_info: ValidatorExitsInfo
) -> ValidatorExitsInfo:
    """Read last validator indexes requested to exit by VEBO"""
    if not watcher.keys_source.modules_operators_dict:
        return exits_info

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

    if total_requests_processed <= exits_info.last_total_requests_processed:
        return exits_info

    logger.info({'msg': 'Getting last validator indexes requested to exit by VEBO'})

    # pylint: disable=duplicate-code
    lookup_window = Web3.to_int(
        watcher.execution.lido_contracts.oracle_daemon_config.functions.get(
            'EXIT_EVENTS_LOOKBACK_WINDOW_IN_SLOTS'
        ).call(block_identifier=current_block_number)
    )

    last_cached_block = -1
    if exits_info.last_requested_exit_indexes:
        last_cached_block = max(exits_info.last_requested_exit_indexes)

    l_block = max(last_cached_block + 1, current_block_number - lookup_window)

    events = get_events_in_range(
        watcher.execution.lido_contracts.validators_exit_bus_oracle.events.ValidatorExitRequest,
        l_block=BlockNumber(l_block),
        r_block=BlockNumber(current_block_number),
    )

    for event in events:
        if event['blockNumber'] not in exits_info.last_requested_exit_indexes:
            exits_info.last_requested_exit_indexes[event['blockNumber']] = set()
        exits_info.last_requested_exit_indexes[event['blockNumber']].add(event['args']['validatorIndex'])

    for cached_block in list(exits_info.last_requested_exit_indexes.keys()):
        if cached_block < current_block_number - lookup_window:
            del exits_info.last_requested_exit_indexes[cached_block]

    exits_info.last_total_requests_processed = total_requests_processed

    return exits_info
