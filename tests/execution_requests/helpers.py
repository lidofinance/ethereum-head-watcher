from secrets import token_hex
from unittest.mock import MagicMock

from src.providers.consensus.typings import (
    FullBlockInfo,
    BlockHeader,
    BlockHeaderMessage,
    BlockMessage,
    BlockBody,
    BlockExecutionPayload,
    ExecutionPayloadBid,
    ExecutionPayloadEnvelope,
    ExecutionRequests,
    SignedExecutionPayloadBid,
    Validator,
    ValidatorState,
    ValidatorStatus,
    WithdrawalRequest,
    ConsolidationRequest,
)
from src.typings import StateRoot, BlockRoot

GLOAS_PARENT_SLOT = '32'
GLOAS_HEAD_SLOT = '33'
GLOAS_EL_BLOCK_NUMBER = '31'


def gen_random_pubkey():
    return random_hex(48)


def gen_random_address():
    return random_hex(20)


def random_hex(length: int) -> str:
    return '0x' + token_hex(length)


def create_sample_block(
    withdrawals: list[WithdrawalRequest] = None, consolidations: list[ConsolidationRequest] = None
) -> FullBlockInfo:
    block = FullBlockInfo(
        root=BlockRoot('0xa69fd326c1e4a84ac56a9f1e440cdb451fce8c4535e4fabd8447cda15506a8d5'),
        canonical=True,
        header=BlockHeader(
            message=BlockHeaderMessage(
                slot='33',
                proposer_index='25',
                parent_root=BlockRoot('0x924057843cd2718a918a1e354c0eb111b15f471319195ed9eeb45e7bf2dae3a7'),
                state_root=StateRoot('0xcc026c107005b9442a26d763409886968cde30a1fbd605e2d9a1c813ddce9062'),
                body_root='0x6f01de44a85b4cbe85d1d452de1979630217ce42e2326388152f39bb9d0a3dce',
            ),
            signature='0x99dde0eb3eaaec71e26e7a614f7eb99c37d7a143edbd55c0b2648dc9f2e754a4e26c3f1320592c2603567cc089a68d5d12f65ec1d9940837dd0d59b05356a0bbc1c3ad51a9546ece8c1233b7398ae3cf1df27c61591bf548b065b68d69bb9450',
        ),
        message=BlockMessage(
            slot='33',
            proposer_index='25',
            parent_root='0x924057843cd2718a918a1e354c0eb111b15f471319195ed9eeb45e7bf2dae3a7',
            state_root=StateRoot('0xcc026c107005b9442a26d763409886968cde30a1fbd605e2d9a1c813ddce9062'),
            body=BlockBody(
                execution_payload=BlockExecutionPayload(block_number='31'),
                voluntary_exits=[],
                proposer_slashings=[],
                attester_slashings=[],
            ),
        ),
        signature='0x99dde0eb3eaaec71e26e7a614f7eb99c37d7a143edbd55c0b2648dc9f2e754a4e26c3f1320592c2603567cc089a68d5d12f65ec1d9940837dd0d59b05356a0bbc1c3ad51a9546ece8c1233b7398ae3cf1df27c61591bf548b065b68d69bb9450',
    )
    if not withdrawals and not consolidations:
        return block

    execution_requests = ExecutionRequests(
        deposits=[], withdrawals=withdrawals or [], consolidations=consolidations or []
    )
    block.message.body.execution_requests = execution_requests
    return block


def create_sample_gloas_block(
    slot: str = GLOAS_HEAD_SLOT,
    parent_root: str = None,
    payload_block_hash: str = None,
    parent_payload_block_hash: str = None,
) -> FullBlockInfo:
    """
    Block shaped as after Glamsterdam (EIP-7732): the body commits to an execution payload bid,
    while the payload itself and the execution requests are revealed in a separate envelope.
    """
    block = create_sample_block()
    block.version = 'gloas'
    block.root = BlockRoot(random_hex(32))
    block.message.slot = slot
    block.header.message.slot = slot
    block.message.state_root = StateRoot(random_hex(32))
    block.header.message.state_root = block.message.state_root
    if parent_root is not None:
        block.message.parent_root = parent_root
        block.header.message.parent_root = BlockRoot(parent_root)
    block.message.body.execution_payload = None
    block.message.body.signed_execution_payload_bid = SignedExecutionPayloadBid(
        message=ExecutionPayloadBid(
            block_hash=payload_block_hash or random_hex(32),
            parent_block_hash=parent_payload_block_hash or random_hex(32),
            parent_block_root=block.message.parent_root,
            builder_index='7',
            slot=slot,
            value='1000',
        ),
        signature=random_hex(96),
    )
    return block


def create_gloas_head_with_envelope(
    watcher,
    withdrawals: list[WithdrawalRequest] = None,
    consolidations: list[ConsolidationRequest] = None,
) -> FullBlockInfo:
    """
    Head block of the Glamsterdam (EIP-7732) shape whose parent revealed an envelope with the given
    execution requests, with the consensus stub wired to serve that parent block and that envelope.

    The bid of the head is built on the payload of the parent, so the requests of the parent envelope
    are applied while the head is being processed.
    """
    parent_payload_block_hash = random_hex(32)

    parent = create_sample_gloas_block(slot=GLOAS_PARENT_SLOT, payload_block_hash=parent_payload_block_hash)
    head = create_sample_gloas_block(
        slot=GLOAS_HEAD_SLOT, parent_root=parent.root, parent_payload_block_hash=parent_payload_block_hash
    )

    envelope = ExecutionPayloadEnvelope(
        payload=BlockExecutionPayload(block_number=GLOAS_EL_BLOCK_NUMBER, block_hash=parent_payload_block_hash),
        execution_requests=ExecutionRequests(
            deposits=[], withdrawals=withdrawals or [], consolidations=consolidations or []
        ),
        beacon_block_root=parent.root,
        builder_index='7',
    )

    watcher.consensus.get_block_details = MagicMock(return_value=parent)
    watcher.consensus.get_execution_payload_envelope = MagicMock(return_value=envelope)
    return head


def create_validator(
    index: str,
    pubkey: str,
    status: ValidatorStatus,
    balance: str = '32000000000',
    exit_epoch: str = '1000000000',
) -> Validator:
    return Validator(
        index=index,
        balance=balance,
        status=status,
        validator=ValidatorState(
            pubkey=pubkey,
            withdrawal_credentials=random_hex(32),
            effective_balance='32000000000',
            slashed=False,
            activation_eligibility_epoch='2048',
            activation_epoch='2048',
            exit_epoch=exit_epoch,
            withdrawable_epoch=exit_epoch,
        ),
    )
