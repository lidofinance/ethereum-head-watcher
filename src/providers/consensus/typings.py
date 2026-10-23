from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from src.typings import BlockRoot, StateRoot
from src.utils.dataclass import FromResponse, Nested


@dataclass
class BeaconSpecResponse(FromResponse):
    DEPOSIT_CHAIN_ID: str
    SLOTS_PER_EPOCH: str
    SECONDS_PER_SLOT: str
    DEPOSIT_CONTRACT_ADDRESS: str


@dataclass
class GenesisResponse(FromResponse):
    genesis_time: str
    genesis_validators_root: str
    genesis_fork_version: str


@dataclass
class BlockRootResponse(FromResponse):
    # https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockRoot
    root: BlockRoot


@dataclass
class BlockHeaderMessage(Nested, FromResponse):
    slot: str
    proposer_index: str
    parent_root: BlockRoot
    state_root: StateRoot
    body_root: str


@dataclass
class BlockHeader(Nested, FromResponse):
    message: BlockHeaderMessage
    signature: str


@dataclass
class BlockHeaderResponseData(Nested, FromResponse):
    # https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockHeader
    root: BlockRoot
    canonical: bool
    header: BlockHeader


@dataclass
class BlockHeaderFullResponse(Nested, FromResponse):
    # https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockHeader
    execution_optimistic: bool
    data: BlockHeaderResponseData
    finalized: Optional[bool] = None


@dataclass
class BlockExecutionPayload(FromResponse):
    block_number: str
    block_hash: str = ''


@dataclass
class ExecutionPayloadBid(FromResponse):
    """
    Commitment to an execution payload the proposer puts into the block since Gloas (EIP-7732).

    The field set is not settled in the specs yet, so every field here is optional: an unexpected
    shape must reduce the amount of data we have, not break block parsing.
    """

    block_hash: str = ''
    parent_block_hash: str = ''
    parent_block_root: str = ''
    builder_index: str = ''
    slot: str = ''
    value: str = ''


@dataclass
class SignedExecutionPayloadBid(Nested, FromResponse):
    message: ExecutionPayloadBid
    signature: str = ''


@dataclass
class VoluntaryExit(FromResponse):
    validator_index: str


@dataclass
class BlockVoluntaryExit(Nested, FromResponse):
    message: VoluntaryExit
    signature: str


@dataclass
class ConsolidationRequest(FromResponse):
    source_address: str
    source_pubkey: str
    target_pubkey: str


@dataclass
class WithdrawalRequest(FromResponse):
    source_address: str
    validator_pubkey: str
    amount: str


@dataclass
class DepositRequest(FromResponse):
    pubkey: str
    withdrawal_credentials: str
    amount: str
    signature: str
    index: int


@dataclass
class ExecutionRequests(Nested, FromResponse):
    deposits: list[DepositRequest]
    withdrawals: list[WithdrawalRequest]
    consolidations: list[ConsolidationRequest]


@dataclass
class BlockBody(Nested, FromResponse):
    voluntary_exits: list[BlockVoluntaryExit]
    proposer_slashings: list
    attester_slashings: list
    # Up to Fulu the block body carries the execution payload and the execution requests inline.
    # Since Gloas (EIP-7732) it commits to a payload bid instead, while the payload itself is
    # revealed by the builder in a separate envelope.
    execution_payload: Optional[BlockExecutionPayload] = None
    execution_requests: Optional[ExecutionRequests] = None
    signed_execution_payload_bid: Optional[SignedExecutionPayloadBid] = None
    # Requests of the payload of the parent block, applied while this block is being processed.
    # `process_parent_execution_payload` checks them against `execution_requests_root` of the bid of
    # the parent, and has them empty when the payload of the parent was skipped.
    parent_execution_requests: Optional[ExecutionRequests] = None

    @property
    def el_block_number(self) -> Optional[int]:
        """Number of the EL block included in this block, None if the payload is not a part of it."""
        return int(self.execution_payload.block_number) if self.execution_payload else None


@dataclass
class BlockMessage(Nested, FromResponse):
    slot: str
    proposer_index: str
    parent_root: str
    state_root: StateRoot
    body: BlockBody


@dataclass
class BlockDetailsResponse(Nested, FromResponse):
    # https://ethereum.github.io/beacon-APIs/#/Beacon/getBlockV2
    message: BlockMessage
    signature: str
    # Name of the fork the block belongs to ("electra", "fulu", "gloas", ...). It is a part of the
    # response envelope rather than of `data`, so the client fills it in explicitly.
    version: str = ''


@dataclass
class PendingConsolidation(Nested, FromResponse):
    source_index: str
    target_index: str


@dataclass
class FullBlockInfo(BlockDetailsResponse, BlockHeaderResponseData):
    pass


@dataclass
class ChainReorgEvent(FromResponse):
    # https://ethereum.github.io/beacon-APIs/#/Beacon/getChainReorgEvents
    depth: str
    slot: str
    old_head_block: BlockRoot
    new_head_block: BlockRoot


class ValidatorStatus(StrEnum):
    PENDING_INITIALIZED = 'pending_initialized'
    PENDING_QUEUED = 'pending_queued'

    ACTIVE_ONGOING = 'active_ongoing'
    ACTIVE_EXITING = 'active_exiting'
    ACTIVE_SLASHED = 'active_slashed'

    EXITED_UNSLASHED = 'exited_unslashed'
    EXITED_SLASHED = 'exited_slashed'

    WITHDRAWAL_POSSIBLE = 'withdrawal_possible'
    WITHDRAWAL_DONE = 'withdrawal_done'


@dataclass
class ValidatorState(FromResponse):
    # All uint variables presents in str
    pubkey: str
    withdrawal_credentials: str
    effective_balance: str
    slashed: bool
    activation_eligibility_epoch: str
    activation_epoch: str
    exit_epoch: str
    withdrawable_epoch: str


@dataclass
class Validator(Nested, FromResponse):
    index: str
    balance: str
    status: ValidatorStatus
    validator: ValidatorState
