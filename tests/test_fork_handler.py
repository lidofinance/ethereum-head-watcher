"""
`ForkHandler` and the head deduplication it depends on.

The handler decides, from the reorg events the SSE listener collected and the blocks the watcher has already handled,
whether a chain reorganisation left slots unprocessed. What ends up in `handled_blocks` is decided by
`Watcher._get_header_full_info`, so the two are covered together: the handler can only be right about a gap if the head
loop put the right blocks there.

Blocks are built by parsing a response of the shape a beacon node returns and merging the two halves the way
`_get_header_full_info` merges them, rather than by constructing the dataclasses directly, so a change in how a block is
parsed or assembled shows up here.
"""

# pylint: disable=unbalanced-tuple-unpacking
import threading
from dataclasses import asdict
from secrets import token_hex
from unittest.mock import MagicMock

import pytest

from src.handlers.fork import ForkHandler
from src.providers.consensus.typings import (
    BlockDetailsResponse,
    BlockHeaderResponseData,
    ChainReorgEvent,
    FullBlockInfo,
)
from src.watcher import Watcher
from tests.execution_requests.stubs import WatcherStub


def random_hex(length: int) -> str:
    return '0x' + token_hex(length)


class ForkWatcherStub(WatcherStub):
    """
    `WatcherStub` plus the reorg queue the SSE listener fills in.

    The queue methods are borrowed from `Watcher` rather than reimplemented, so these tests still fail if the
    take-and-forget semantics change.
    """

    pending_chain_reorgs = Watcher.pending_chain_reorgs
    drop_chain_reorg = Watcher.drop_chain_reorg

    def __init__(self):
        super().__init__()
        self.chain_reorgs: dict[str, ChainReorgEvent] = {}
        self._chain_reorgs_lock = threading.Lock()


def block_parts(slot: int, parent_root: str, root: str = None):
    """
    A block of the Gloas shape, parsed the way the consensus client parses it.

    Returned as the two halves `get_block_header` and `get_block_details` answer with, so that the
    `_get_header_full_info` tests can feed it the same pair the real endpoints do.
    """
    root = root or random_hex(32)
    state_root = random_hex(32)
    signature = random_hex(96)

    header_response = {
        'root': root,
        'canonical': True,
        'header': {
            'message': {
                'slot': str(slot),
                'proposer_index': '25',
                'parent_root': parent_root,
                'state_root': state_root,
                'body_root': random_hex(32),
            },
            'signature': signature,
        },
    }

    block_response = {
        'message': {
            'slot': str(slot),
            'proposer_index': '25',
            'parent_root': parent_root,
            'state_root': state_root,
            'body': {
                'randao_reveal': signature,
                'eth1_data': {'deposit_root': random_hex(32), 'deposit_count': '0', 'block_hash': random_hex(32)},
                'graffiti': random_hex(32),
                'proposer_slashings': [],
                'attester_slashings': [],
                'attestations': [],
                'deposits': [],
                'voluntary_exits': [],
                'sync_aggregate': {'sync_committee_bits': '0x00', 'sync_committee_signature': signature},
                'bls_to_execution_changes': [],
                'signed_execution_payload_bid': {
                    'message': {
                        'parent_block_hash': random_hex(32),
                        'parent_block_root': parent_root,
                        'block_hash': random_hex(32),
                        'prev_randao': random_hex(32),
                        'fee_recipient': random_hex(20),
                        'gas_limit': '200000000',
                        'builder_index': '18446744073709551615',
                        'slot': str(slot),
                        'value': '0',
                        'execution_payment': '0',
                        'blob_kzg_commitments': [],
                        'execution_requests_root': random_hex(32),
                    },
                    'signature': signature,
                },
                'payload_attestations': [],
                'parent_execution_requests': {
                    'deposits': [],
                    'withdrawals': [],
                    'consolidations': [],
                    'builder_deposits': [],
                    'builder_exits': [],
                },
            },
        },
        'signature': signature,
    }

    header = BlockHeaderResponseData.from_response(**header_response)
    details = BlockDetailsResponse.from_response(**{**block_response, 'version': 'gloas'})
    return header, details


def block(slot: int, parent_root: str, root: str = None) -> FullBlockInfo:
    """One handled block, merged the way `Watcher._get_header_full_info` merges the two responses"""
    header, details = block_parts(slot, parent_root, root)
    return FullBlockInfo(**asdict(header), **asdict(details))


def chain(first_slot: int, length: int) -> list[FullBlockInfo]:
    """Consecutive blocks, each one's `parent_root` pointing at the previous one's `root`"""
    blocks = []
    parent_root = random_hex(32)
    for offset in range(length):
        current = block(first_slot + offset, parent_root)
        blocks.append(current)
        parent_root = current.root
    return blocks


def reorg_event(slot: int, new_head_block: str, depth: int = 2) -> ChainReorgEvent:
    """A `chain_reorg` event in the shape a beacon node sends it, through the real parser"""
    return ChainReorgEvent.from_response(
        slot=str(slot),
        depth=str(depth),
        old_head_block=random_hex(32),
        new_head_block=new_head_block,
        old_head_state=random_hex(32),
        new_head_state=random_hex(32),
        epoch=str(slot // 32),
        execution_optimistic=False,
    )


@pytest.fixture
def watcher() -> ForkWatcherStub:
    return ForkWatcherStub()


def handle(watcher: ForkWatcherStub, head: FullBlockInfo) -> ForkHandler:
    handler = ForkHandler()
    handler.handle(watcher, head).result()
    return handler


def test_known_reorg_target_with_a_known_parent_raises_no_alert(watcher: ForkWatcherStub):
    """The watcher handled the branch the chain reorganised onto, so nothing was missed"""
    first, second, head = chain(100, 3)
    watcher.handled_blocks = [first, second]

    watcher.chain_reorgs[second.header.message.slot] = reorg_event(101, new_head_block=second.root)

    handle(watcher, head)

    assert watcher.alertmanager.sent_alerts == []
    assert watcher.chain_reorgs == {}, 'a consumed reorg event must not be handled twice'


def test_reorg_to_an_unknown_block_alerts_with_the_slot_range(watcher: ForkWatcherStub):
    """The new branch was never handled, so the slots it carries need a human to look at them"""
    first, second, head = chain(100, 3)
    watcher.handled_blocks = [first, second]

    watcher.chain_reorgs['101'] = reorg_event(101, new_head_block=random_hex(32), depth=2)

    handle(watcher, head)

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('UnhandledChainReorg')
    assert alert.labels.severity == 'info'
    assert alert.annotations.summary == '**🔗‍🔀 Unhandled slots after chain reorganization**'
    assert 'Reorg depth is 2 slots.' in alert.annotations.description
    # slot - depth .. slot inclusive
    for slot in (99, 100, 101):
        assert f'/slot/{slot})' in alert.annotations.description
    assert '/slot/98)' not in alert.annotations.description
    assert '/slot/102)' not in alert.annotations.description
    assert watcher.chain_reorgs == {}


def test_unknown_reorg_target_that_is_the_head_parent_alerts_once(watcher: ForkWatcherStub):
    """
    The reorg landed on the parent of the current head and we know neither.

    Both branches of the handler match here, and the `head_parent_is_alerted` flag is what keeps the operator from being
    paged twice about the same gap.
    """
    first, second = chain(100, 2)
    watcher.handled_blocks = [first, second]

    unknown_parent_root = random_hex(32)
    head = block(103, parent_root=unknown_parent_root)
    watcher.chain_reorgs['102'] = reorg_event(102, new_head_block=unknown_parent_root)

    handle(watcher, head)

    assert len(watcher.alertmanager.sent_alerts) == 1, 'UnhandledHead must be suppressed by the reorg alert'
    assert watcher.alertmanager.sent_alerts[0].labels.alertname.startswith('UnhandledChainReorg')


def test_unknown_head_parent_without_a_reorg_event_alerts(watcher: ForkWatcherStub):
    """A head whose parent we never handled, with no reorg event to explain it"""
    first, second = chain(100, 2)
    watcher.handled_blocks = [first, second]

    head = block(107, parent_root=random_hex(32))

    handle(watcher, head)

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('UnhandledHead')
    assert alert.labels.severity == 'info'
    assert alert.annotations.summary == '**🫳🐦 Unhandled chain slot**'
    assert head.header.message.parent_root in alert.annotations.description
    # 107 - 101 - 2 == 4
    assert 'And 4 slot(s) before it' in alert.annotations.description


def test_consecutive_head_raises_no_alert(watcher: ForkWatcherStub):
    """The ordinary case: the head extends the block we handled last"""
    first, second, head = chain(100, 3)
    watcher.handled_blocks = [first, second]

    handle(watcher, head)

    assert watcher.alertmanager.sent_alerts == []


def test_first_head_after_start_raises_no_alert(watcher: ForkWatcherStub):
    """Nothing has been handled yet, so an unknown parent says nothing about a missed slot"""
    head = block(100, parent_root=random_hex(32))

    handle(watcher, head)

    assert watcher.alertmanager.sent_alerts == []


def test_reorg_landed_on_before_the_poll_raises_no_alert(watcher: ForkWatcherStub):
    """
    The reorg happened before the watcher got to that slot, so it went straight to the new branch.

    Nothing was missed and nothing stale was processed, so silence is the right answer -- this pins that the handler
    does not page on a reorg it effectively never experienced.
    """
    shared_parent = block(99, parent_root=random_hex(32))
    watcher.handled_blocks = [shared_parent]

    head = block(100, parent_root=shared_parent.root)
    watcher.chain_reorgs['100'] = reorg_event(100, new_head_block=head.root, depth=1)

    handle(watcher, head)

    assert watcher.alertmanager.sent_alerts == []
    assert watcher.chain_reorgs == {}


def test_a_second_reorg_at_the_same_slot_survives_for_the_next_cycle(watcher: ForkWatcherStub):
    """
    A reorg the listener stores while an earlier one of the same slot is being handled is kept.

    The handler takes a snapshot and then forgets each event by identity, so replacing the value under a slot key must
    not make the replacement disappear along with it.
    """
    first, second = chain(100, 2)
    watcher.handled_blocks = [first, second]
    head = block(102, parent_root=second.root)

    racing_event = reorg_event(100, new_head_block=random_hex(32), depth=30)
    watcher.chain_reorgs['100'] = reorg_event(100, new_head_block=random_hex(32), depth=1)

    class RacingForkHandler(ForkHandler):
        """Stands in for the SSE thread delivering a second event mid-handling"""

        def _send_reorg_alert(self, watcher, chain_reorg):
            watcher.chain_reorgs['100'] = racing_event
            super()._send_reorg_alert(watcher, chain_reorg)

    RacingForkHandler().handle(watcher, head).result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    assert 'Reorg depth is 1 slots.' in watcher.alertmanager.sent_alerts[0].annotations.description
    assert watcher.chain_reorgs == {'100': racing_event}, 'the racing event must wait, not vanish'

    # and the next cycle reports it, the way the watcher would after handling `head`
    watcher.handled_blocks.append(head)
    handle(watcher, block(103, parent_root=head.root))

    assert len(watcher.alertmanager.sent_alerts) == 2
    assert 'Reorg depth is 30 slots.' in watcher.alertmanager.sent_alerts[1].annotations.description
    assert watcher.chain_reorgs == {}


def test_a_reorg_event_is_forgotten_only_after_its_alert_is_out(watcher: ForkWatcherStub):
    """
    Ordering matters: `send_alerts` can raise on an Alertmanager outage.

    Forgetting the event first would lose it, because the raised exception aborts the head and the event never comes
    back. Forgetting it last leaves it in the queue for the next cycle.
    """
    first, second = chain(100, 2)
    watcher.handled_blocks = [first, second]
    head = block(102, parent_root=second.root)
    watcher.chain_reorgs['100'] = reorg_event(100, new_head_block=random_hex(32), depth=1)

    calls = []
    watcher.alertmanager.send_alerts = MagicMock(side_effect=lambda alerts: calls.append('sent'))
    forget = watcher.drop_chain_reorg

    def recording_drop(event):
        calls.append('dropped')
        forget(event)

    watcher.drop_chain_reorg = recording_drop

    handle(watcher, head)

    assert calls == ['sent', 'dropped']
    assert watcher.chain_reorgs == {}


# --- the head loop tells blocks apart by root, not by slot ---------------------------------------
# A reorg replaces the block of a slot that may already have been handled. Deduplicating the head by slot number would
# skip the replacement entirely, leaving the canonical block's operations unchecked, so `_get_header_full_info` compares
# roots.


def head_lookup_watcher(handled_blocks: list[FullBlockInfo], header, details) -> Watcher:
    """`Watcher` with only what `_get_header_full_info` touches, built without its network init"""
    watcher = Watcher.__new__(Watcher)
    watcher.handled_blocks = list(handled_blocks)
    watcher.genesis_time = 0
    watcher.consensus = MagicMock()
    watcher.consensus.get_block_header = MagicMock(return_value=header)
    watcher.consensus.get_block_details = MagicMock(return_value=details)
    return watcher


def test_head_replaced_by_a_reorg_at_the_same_slot_is_handled():
    """The canonical block of an already handled slot is a different block and has to be handled"""
    shared_parent = block(99, parent_root=random_hex(32))
    orphaned = block(100, parent_root=shared_parent.root)
    header, details = block_parts(100, parent_root=shared_parent.root)

    watcher = head_lookup_watcher([shared_parent, orphaned], header, details)

    current_head = watcher._get_header_full_info()  # pylint: disable=protected-access

    assert current_head is not None, 'the replacement block must not be mistaken for the orphan'
    assert current_head.root == header.root
    assert current_head.root != orphaned.root
    assert current_head.message.slot == orphaned.message.slot


def test_unchanged_head_is_skipped():
    """The ordinary case the deduplication exists for: polling faster than the chain advances"""
    parent = block(99, parent_root=random_hex(32))
    header, details = block_parts(100, parent_root=parent.root)
    handled = FullBlockInfo(**asdict(header), **asdict(details))

    watcher = head_lookup_watcher([parent, handled], header, details)

    assert watcher._get_header_full_info() is None  # pylint: disable=protected-access
    watcher.consensus.get_block_details.assert_not_called()


def test_reorg_back_to_an_earlier_handled_block_is_skipped():
    """Matching every handled block, not just the last, keeps a reorg back from alerting twice"""
    first = block(99, parent_root=random_hex(32))
    header, details = block_parts(100, parent_root=first.root)
    original = FullBlockInfo(**asdict(header), **asdict(details))
    replacement = block(100, parent_root=first.root)

    # the chain reorged to `replacement` and then back to `original`, which we already handled
    watcher = head_lookup_watcher([first, original, replacement], header, details)

    assert watcher._get_header_full_info() is None  # pylint: disable=protected-access


def test_first_head_after_start_is_handled():
    """Nothing handled yet, so nothing to match against"""
    header, details = block_parts(100, parent_root=random_hex(32))

    watcher = head_lookup_watcher([], header, details)

    current_head = watcher._get_header_full_info()  # pylint: disable=protected-access

    assert current_head is not None
    assert current_head.root == header.root
