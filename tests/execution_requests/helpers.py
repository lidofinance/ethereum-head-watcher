from secrets import token_hex

from src.providers.consensus.typings import (
    FullBlockInfo,
    BlockHeader,
    BlockHeaderMessage,
    BlockMessage,
    BlockBody,
    BlockExecutionPayload,
    ExecutionRequests,
    WithdrawalRequest,
    ConsolidationRequest,
)
from src.typings import StateRoot, BlockRoot


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
