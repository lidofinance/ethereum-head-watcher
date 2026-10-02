import logging
from typing import Iterator

from eth_utils import event_abi_to_log_topic
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import EventData

from src.typings import BlockNumber
from src.variables import EVENTS_SEARCH_STEP

logger = logging.getLogger()


class InconsistentEvents(Exception):
    pass


def get_events_in_range(
    contract: Contract, event_names: list[str], l_block: BlockNumber, r_block: BlockNumber
) -> Iterator[EventData]:
    """Fetch several events of one contract with a single get_logs query per chunk.

    Events are yielded ordered by (blockNumber, logIndex). Closed interval.
    """
    if l_block > r_block:
        raise ValueError(f"{l_block=} > {r_block=}")

    events = [contract.events[name]() for name in event_names]
    by_topic = {event_abi_to_log_topic(event.abi): event for event in events}
    topics = [[Web3.to_hex(topic) for topic in by_topic]]

    while True:
        to_block = min(r_block, BlockNumber(l_block + EVENTS_SEARCH_STEP))

        logger.info({"msg": f"Fetching {', '.join(event_names)} events in range [{l_block}:{to_block}]"})

        logs = contract.w3.eth.get_logs(
            {'address': contract.address, 'fromBlock': l_block, 'toBlock': to_block, 'topics': topics}
        )

        chunk = []
        for log in logs:
            if not l_block <= log['blockNumber'] <= to_block:
                raise InconsistentEvents(
                    f"Event block {log['blockNumber']} is outside requested range [{l_block}:{to_block}]"
                )
            chunk.append(by_topic[log['topics'][0]].process_log(log))

        chunk.sort(key=lambda e: (e['blockNumber'], e['logIndex']))
        yield from chunk

        if to_block == r_block:
            break

        l_block = BlockNumber(to_block + 1)
