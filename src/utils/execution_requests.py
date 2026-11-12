import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from src.providers.consensus.typings import (
    BlockDetailsResponse,
    ConsolidationRequest,
    ExecutionRequests,
    FullBlockInfo,
    WithdrawalRequest,
)
from src.typings import StateRoot

logger = logging.getLogger()


class ExecutionRequestsSource(StrEnum):
    # Up to Fulu the requests are a part of the block body and are applied within the same slot
    BLOCK = 'block'
    # Since Gloas (EIP-7732) the block carries the requests of the payload of its parent
    PARENT_BLOCK = 'parent_block'
    # No payload was applied while the head block was being processed, so there is nothing to check
    NOTHING_APPLIED = 'nothing_applied'


@dataclass
class ExecutionRequestsContext:
    """
    Execution requests applied to the beacon state while the head block was being processed.

    Up to Fulu a block carries its requests inline and they are applied within the same slot, so
    `request_slot` and `state_slot` are equal. Since Gloas (EIP-7732) the requests belong to the
    payload of the parent block and are applied by `apply_parent_execution_payload` while the head
    block is being processed: they were published in `request_slot` (the parent slot) but are only
    observable in the state of `state_slot` (the head slot).

    Reading validator states and pending consolidations by the state of `state_slot` is what keeps
    the checks meaningful: a consolidation moves its source validator to `active_exiting` and appends
    an entry to the pending consolidations queue exactly when it is applied. Reading them by the
    state of `request_slot` would report every accepted consolidation as invalid and rejected.

    That state is addressed by `state_root` rather than by `state_slot`, so that a reorg can not
    silently answer the questions about a slot from another branch of the chain. `state_slot` is left
    for the alerts to point a human at.
    """

    source: ExecutionRequestsSource
    request_slot: str
    state_slot: str
    state_root: StateRoot
    requests: Optional[ExecutionRequests] = None
    el_block_number: Optional[int] = None

    @property
    def consolidations(self) -> list[ConsolidationRequest]:
        return self.requests.consolidations if self.requests else []

    @property
    def withdrawals(self) -> list[WithdrawalRequest]:
        return self.requests.withdrawals if self.requests else []


def resolve_execution_requests(watcher, head: FullBlockInfo) -> ExecutionRequestsContext:
    """Find the execution requests that were applied to the state while `head` was being processed"""
    head_slot = head.message.slot
    # Whichever branch below is taken, the state that has the requests applied is the one the head
    # block leaves behind, so the same root addresses it every time
    head_state_root = head.message.state_root
    body = head.message.body

    if body.execution_payload is not None:
        return ExecutionRequestsContext(
            source=ExecutionRequestsSource.BLOCK,
            request_slot=head_slot,
            state_slot=head_slot,
            state_root=head_state_root,
            requests=body.execution_requests,
            el_block_number=body.el_block_number,
        )

    # Since Gloas (EIP-7732) the head block carries the requests of the payload of its parent in
    # `parent_execution_requests`, and `process_parent_execution_payload` checks them against the
    # commitment in the bid of the parent. So they take no request of their own, and no payload can
    # be applied with its requests left unreadable.
    #
    # The parent block is still read, to name the slot the requests were published in and to tell a
    # skipped payload from an applied one. Following `parent_root` instead of counting slots back
    # keeps missed slots and reorgs handled for free.
    parent = _get_parent_block(watcher, head)
    if parent is None:
        # Only the slot to name in an alert is lost, the requests themselves are at hand
        logger.warning({'msg': f'Can not tell which slot published the requests applied at block [{head_slot}]'})
        return ExecutionRequestsContext(
            source=ExecutionRequestsSource.PARENT_BLOCK,
            request_slot=head_slot,
            state_slot=head_slot,
            state_root=head_state_root,
            requests=body.parent_execution_requests,
            el_block_number=_applied_el_block_number(watcher, head),
        )

    if parent.message.body.execution_payload is not None:
        # The first block of the fork: the requests of its pre-Gloas parent were applied in the
        # parent slot itself and were handled back when the parent was the head.
        logger.info({'msg': f'Block [{head_slot}] is the first block of the Gloas fork with an out of block payload'})
        return ExecutionRequestsContext(
            source=ExecutionRequestsSource.NOTHING_APPLIED,
            request_slot=head_slot,
            state_slot=head_slot,
            state_root=head_state_root,
            el_block_number=parent.message.body.el_block_number,
        )

    if not _parent_payload_applied(head, parent):
        # The builder did not reveal the payload in time, so the head is built on the branch without
        # it and nothing was applied. The head carries no requests then, and they stay in the EL
        # queues to be included into one of the following payloads.
        logger.info(
            {'msg': f'Payload of block [{parent.message.slot}] was not applied at block [{head_slot}]'}
        )
        return ExecutionRequestsContext(
            source=ExecutionRequestsSource.NOTHING_APPLIED,
            request_slot=parent.message.slot,
            state_slot=head_slot,
            state_root=head_state_root,
            el_block_number=_applied_el_block_number(watcher, head),
        )

    return ExecutionRequestsContext(
        source=ExecutionRequestsSource.PARENT_BLOCK,
        request_slot=parent.message.slot,
        state_slot=head_slot,
        state_root=head_state_root,
        requests=body.parent_execution_requests,
        el_block_number=_applied_el_block_number(watcher, head),
    )


def _applied_el_block_number(watcher, head: FullBlockInfo) -> Optional[int]:
    """
    Number of the latest EL block applied to the state.

    Whatever branch the head is built on, the parent block hash of its bid is the payload the state
    already has: the one of the parent block when it was revealed in time, the one of an earlier
    ancestor when it was not. So the hash identifies the EL block the contract calls of the handlers
    have to be made against.

    Costs one EL request per head block.
    """
    bid = head.message.body.signed_execution_payload_bid
    if bid is None or not bid.message.parent_block_hash:
        return None

    if watcher.execution is None:
        # Keys are taken from a file, so there is nothing to look up in the EL contracts anyway
        return None

    try:
        return int(watcher.execution.eth.get_block(bid.message.parent_block_hash).number)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            {
                'msg': f'Can not get EL block [{bid.message.parent_block_hash}] applied at block '
                f'[{head.message.slot}]',
                'exception': str(e),
            }
        )
        return None


def _get_parent_block(watcher, head: FullBlockInfo) -> Optional[BlockDetailsResponse]:
    """Parent block, taken from the already handled heads when possible to save a request"""
    parent_root = head.message.parent_root

    for handled in reversed(watcher.handled_blocks):
        if handled.root == parent_root:
            return handled

    try:
        return watcher.consensus.get_block_details(parent_root)
    except Exception as e:  # pylint: disable=broad-except
        logger.error({'msg': f'Can not get parent block [{parent_root}] for slot {head.message.slot}', 'exception': str(e)})
        return None


def _parent_payload_applied(head: FullBlockInfo, parent: BlockDetailsResponse) -> bool:
    """
    Whether the payload of the parent block was applied while the head block was being processed.

    Since Gloas (EIP-7732) a proposer may build on the branch without the parent payload if the
    builder did not reveal it in time. Such a block commits to a payload whose parent is the payload
    of an earlier ancestor, so the operations of the parent payload never reach the state.

    When the bids can not be read the payload is treated as applied: for a monitoring bot a false
    alert is a better outcome than a silently skipped block.
    """
    head_bid = head.message.body.signed_execution_payload_bid
    parent_bid = parent.message.body.signed_execution_payload_bid

    if head_bid is None or parent_bid is None:
        return True

    if not head_bid.message.parent_block_hash or not parent_bid.message.block_hash:
        return True

    return head_bid.message.parent_block_hash == parent_bid.message.block_hash
