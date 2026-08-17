from unittest.mock import MagicMock

from src.providers.consensus.typings import ConsolidationRequest
from src.utils.execution_requests import (
    ExecutionRequestsSource,
    resolve_execution_requests,
)
from tests.execution_requests.helpers import (
    GLOAS_EL_BLOCK_NUMBER,
    GLOAS_HEAD_SLOT,
    GLOAS_PARENT_SLOT,
    create_gloas_head_with_envelope,
    create_sample_block,
    create_sample_gloas_block,
    gen_random_address,
    gen_random_pubkey,
    random_hex,
)
from tests.execution_requests.stubs import WatcherStub


def sample_consolidation() -> ConsolidationRequest:
    return ConsolidationRequest(
        source_address=gen_random_address(),
        source_pubkey=gen_random_pubkey(),
        target_pubkey=gen_random_pubkey(),
    )


def with_execution(watcher: WatcherStub, block_number: int = 30):
    """Give the stub an EL that resolves any block hash to `block_number`"""
    watcher.execution = MagicMock()
    watcher.execution.eth.get_block = MagicMock(return_value=MagicMock(number=block_number))
    return watcher.execution


def test_pre_gloas_requests_come_from_the_block_itself(watcher: WatcherStub):
    consolidation = sample_consolidation()
    block = create_sample_block(consolidations=[consolidation])

    ctx = resolve_execution_requests(watcher, block)

    assert ctx.source == ExecutionRequestsSource.BLOCK
    assert ctx.request_slot == block.message.slot
    assert ctx.state_slot == block.message.slot
    assert ctx.state_root == block.message.state_root
    assert ctx.consolidations == [consolidation]
    assert ctx.el_block_number == 31
    watcher.consensus.get_block_details.assert_not_called()
    watcher.consensus.get_execution_payload_envelope.assert_not_called()


def test_gloas_requests_come_from_the_parent_envelope(watcher: WatcherStub):
    consolidation = sample_consolidation()
    head = create_gloas_head_with_envelope(watcher, consolidations=[consolidation])
    execution = with_execution(watcher)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.ENVELOPE
    assert ctx.request_slot == GLOAS_PARENT_SLOT
    assert ctx.state_slot == GLOAS_HEAD_SLOT
    # The requests are published by the parent but only observable in the state left by the head
    assert ctx.state_root == head.message.state_root
    assert ctx.consolidations == [consolidation]
    assert ctx.el_block_number == int(GLOAS_EL_BLOCK_NUMBER)
    assert watcher.consensus.get_execution_payload_envelope.call_args.args[0] == head.message.parent_root
    # The envelope already carries the number, the common path must not touch the EL for it
    execution.eth.get_block.assert_not_called()


def test_parent_block_is_reused_from_the_handled_heads(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher)
    watcher.handled_blocks = [watcher.consensus.get_block_details.return_value]
    watcher.consensus.get_block_details.reset_mock()

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.ENVELOPE
    watcher.consensus.get_block_details.assert_not_called()


def test_nothing_is_applied_at_the_first_block_of_the_fork(watcher: WatcherStub):
    """The requests of a pre-Gloas parent were applied in its own slot and handled back then"""
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    watcher.consensus.get_block_details = MagicMock(return_value=create_sample_block())

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.NOTHING_APPLIED
    assert not ctx.consolidations
    # The payload of the pre-Gloas parent is still the latest one applied to the state
    assert ctx.el_block_number == 31
    watcher.consensus.get_execution_payload_envelope.assert_not_called()


def test_nothing_is_applied_when_the_parent_payload_was_not_revealed(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.NOTHING_APPLIED
    assert ctx.request_slot == GLOAS_PARENT_SLOT
    assert ctx.state_slot == GLOAS_HEAD_SLOT
    assert not ctx.consolidations
    watcher.consensus.get_execution_payload_envelope.assert_not_called()


def test_payload_is_treated_as_applied_when_the_bids_can_not_be_read(watcher: WatcherStub):
    """A false alert is a better outcome for a monitoring bot than a silently skipped block"""
    consolidation = sample_consolidation()
    head = create_gloas_head_with_envelope(watcher, consolidations=[consolidation])
    head.message.body.signed_execution_payload_bid = None

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.ENVELOPE
    assert ctx.consolidations == [consolidation]


def test_requests_are_unavailable_when_the_envelope_is_missing(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    watcher.consensus.get_execution_payload_envelope = MagicMock(return_value=None)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.UNAVAILABLE
    assert ctx.request_slot == GLOAS_PARENT_SLOT
    assert ctx.state_slot == GLOAS_HEAD_SLOT
    assert not ctx.consolidations


def test_requests_are_unavailable_when_the_envelope_request_fails(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    watcher.consensus.get_execution_payload_envelope = MagicMock(side_effect=ConnectionError('boom'))

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.UNAVAILABLE
    assert not ctx.consolidations


def test_requests_are_unavailable_when_the_parent_block_can_not_be_read(watcher: WatcherStub):
    head = create_sample_gloas_block()
    watcher.consensus.get_block_details = MagicMock(side_effect=ConnectionError('boom'))

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.UNAVAILABLE
    assert ctx.request_slot == head.message.slot
    assert ctx.state_slot == head.message.slot
    assert not ctx.withdrawals
    watcher.consensus.get_execution_payload_envelope.assert_not_called()


def test_el_block_number_is_resolved_by_the_bid_when_the_parent_payload_was_not_revealed(watcher: WatcherStub):
    """
    The exits handler still has to look VEBO requests up on a block whose parent payload was skipped,
    and the parent block hash of the head bid points at the payload the state actually has.
    """
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)
    execution = with_execution(watcher, block_number=30)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.NOTHING_APPLIED
    assert ctx.el_block_number == 30
    assert (
        execution.eth.get_block.call_args.args[0]
        == head.message.body.signed_execution_payload_bid.message.parent_block_hash
    )


def test_el_block_number_is_resolved_by_the_bid_when_the_envelope_is_missing(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher, consolidations=[sample_consolidation()])
    watcher.consensus.get_execution_payload_envelope = MagicMock(return_value=None)
    with_execution(watcher, block_number=30)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.UNAVAILABLE
    assert ctx.el_block_number == 30


def test_el_block_number_is_resolved_by_the_bid_when_the_parent_block_can_not_be_read(watcher: WatcherStub):
    head = create_sample_gloas_block()
    watcher.consensus.get_block_details = MagicMock(side_effect=ConnectionError('boom'))
    with_execution(watcher, block_number=30)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.UNAVAILABLE
    assert ctx.el_block_number == 30


def test_el_block_number_is_not_resolved_when_the_el_request_fails(watcher: WatcherStub):
    head = create_gloas_head_with_envelope(watcher)
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)
    execution = with_execution(watcher)
    execution.eth.get_block = MagicMock(side_effect=ConnectionError('boom'))

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.NOTHING_APPLIED
    assert ctx.el_block_number is None


def test_el_block_number_is_not_resolved_without_execution_access(watcher: WatcherStub):
    """Keys come from a file, so there is nothing to look up in the Lido contracts anyway"""
    head = create_gloas_head_with_envelope(watcher)
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)

    ctx = resolve_execution_requests(watcher, head)

    assert ctx.source == ExecutionRequestsSource.NOTHING_APPLIED
    assert ctx.el_block_number is None
