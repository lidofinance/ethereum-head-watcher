import logging
from typing import Iterator

from web3.contract.contract import ContractEvent
from web3.types import EventData

from src.typings import BlockNumber
from src.variables import EVENTS_SEARCH_STEP

logger = logging.getLogger()

class InconsistentEvents(Exception):
    pass


def get_events_in_range(event: ContractEvent, l_block: BlockNumber, r_block: BlockNumber) -> Iterator[EventData]:
    """Fetch all the events in the given blocks range (closed interval)"""
    if l_block > r_block:
        raise ValueError(f"{l_block=} > {r_block=}")

    while True:
        to_block = min(r_block, BlockNumber(l_block + EVENTS_SEARCH_STEP))

        logger.info({"msg": f"Fetching {event.event_name} events in range [{l_block}:{to_block}]"})

        for e in event.get_logs(fromBlock=l_block, toBlock=to_block):
            if not l_block <= e['blockNumber'] <= to_block:
                raise InconsistentEvents
            yield e

        if to_block == r_block:
            break

        l_block = BlockNumber(to_block + 1)
