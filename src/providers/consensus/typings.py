from dataclasses import dataclass
from enum import Enum
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
    execution_payload: BlockExecutionPayload
    voluntary_exits: list[BlockVoluntaryExit]
    proposer_slashings: list
    attester_slashings: list
    execution_requests: Optional[ExecutionRequests] = None


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


class ValidatorStatus(Enum):
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
