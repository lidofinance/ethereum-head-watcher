from unittest.mock import MagicMock

from src.keys_source.keys_api_source import KeysApiSource
from src.providers.consensus.client import ConsensusClient
from src.providers.consensus.typings import BlockDetailsResponse
from src.utils.exit import ValidatorExitsInfo, get_last_requested_validator_exit_indexes

PARENT_ROOT = '0x924057843cd2718a918a1e354c0eb111b15f471319195ed9eeb45e7bf2dae3a7'
STATE_ROOT = '0xcc026c107005b9442a26d763409886968cde30a1fbd605e2d9a1c813ddce9062'
PAYLOAD_BLOCK_HASH = '0x2b0d4e0c1a5c0f4a51e2e9d4d0a4b8f7e6c5d4b3a2918070605040302010ffee'
SOURCE_ADDRESS = '0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f'
SOURCE_PUBKEY = '0x' + 'aa' * 48
TARGET_PUBKEY = '0x' + 'bb' * 48
SIGNATURE = '0x' + 'cc' * 96

CONSOLIDATION = {'source_address': SOURCE_ADDRESS, 'source_pubkey': SOURCE_PUBKEY, 'target_pubkey': TARGET_PUBKEY}

# Body fields of a pre-Glamsterdam (up to Fulu) block
INLINE_PAYLOAD_AND_REQUESTS = {
    'execution_payload': {
        'block_number': '31',
        'block_hash': PAYLOAD_BLOCK_HASH,
        'transactions': [],  # not modelled, has to be ignored
    },
    'execution_requests': {
        'deposits': [],
        'withdrawals': [{'source_address': SOURCE_ADDRESS, 'validator_pubkey': SOURCE_PUBKEY, 'amount': '0'}],
        'consolidations': [CONSOLIDATION],
    },
}

# Body fields of a Glamsterdam (EIP-7732) block: a payload bid instead of the payload and the requests
PAYLOAD_BID = {
    'signed_execution_payload_bid': {
        'message': {
            'parent_block_hash': PAYLOAD_BLOCK_HASH,
            'parent_block_root': PARENT_ROOT,
            'block_hash': '0x1f2e3d4c5b6a798807060504030201000f1e2d3c4b5a69788796a5b4c3d2e1f0',
            'fee_recipient': SOURCE_ADDRESS,  # not modelled, has to be ignored
            'gas_limit': '30000000',  # not modelled, has to be ignored
            'builder_index': '7',
            'slot': '11000000',
            'value': '1000',
        },
        'signature': SIGNATURE,
    },
    'payload_attestations': [],  # not modelled, has to be ignored
}


def block_data(body: dict) -> dict:
    """`data` of a getBlockV2 response with the fork specific part of the body passed in"""
    return {
        'message': {
            'slot': '11000000',
            'proposer_index': '25',
            'parent_root': PARENT_ROOT,
            'state_root': STATE_ROOT,
            'body': {
                'randao_reveal': SIGNATURE,  # not modelled, has to be ignored
                'proposer_slashings': [],
                'attester_slashings': [],
                'voluntary_exits': [{'message': {'validator_index': '42'}, 'signature': SIGNATURE}],
                **body,
            },
        },
        'signature': SIGNATURE,
    }


def test_block_with_inline_payload_and_requests_is_parsed():
    block = BlockDetailsResponse.from_response(**block_data(INLINE_PAYLOAD_AND_REQUESTS))

    body = block.message.body
    assert body.execution_payload.block_number == '31'
    assert body.execution_payload.block_hash == PAYLOAD_BLOCK_HASH
    assert body.el_block_number == 31
    assert body.signed_execution_payload_bid is None
    assert [c.target_pubkey for c in body.execution_requests.consolidations] == [TARGET_PUBKEY]
    assert [w.validator_pubkey for w in body.execution_requests.withdrawals] == [SOURCE_PUBKEY]
    assert [e.message.validator_index for e in body.voluntary_exits] == ['42']


def test_block_with_payload_bid_is_parsed():
    """Since Gloas (EIP-7732) there is no payload and no requests in the body, parsing must survive it"""
    block = BlockDetailsResponse.from_response(**block_data(PAYLOAD_BID))

    body = block.message.body
    assert body.execution_payload is None
    assert body.execution_requests is None
    assert body.el_block_number is None
    assert body.signed_execution_payload_bid.message.parent_block_hash == PAYLOAD_BLOCK_HASH
    assert body.signed_execution_payload_bid.message.builder_index == '7'
    assert [e.message.validator_index for e in body.voluntary_exits] == ['42']


def test_payload_bid_with_unexpected_field_set_is_parsed():
    """The bid layout is not final yet, so neither a missing nor an unknown field may break parsing"""
    body = {'signed_execution_payload_bid': {'message': {'block_hash': PAYLOAD_BLOCK_HASH, 'unknown_field': '1'}}}

    block = BlockDetailsResponse.from_response(**block_data(body))

    bid = block.message.body.signed_execution_payload_bid
    assert bid.message.block_hash == PAYLOAD_BLOCK_HASH
    assert bid.message.builder_index == ''
    assert bid.signature == ''


def test_fork_version_is_taken_from_the_response_envelope():
    client = ConsensusClient(['http://localhost:5052'])
    client.get = MagicMock(return_value=(block_data(PAYLOAD_BID), {'version': 'gloas'}))

    assert client.get_block_details('head').version == 'gloas'


def test_fork_version_is_empty_when_it_is_not_reported():
    client = ConsensusClient(['http://localhost:5052'])
    client.get = MagicMock(return_value=(block_data(INLINE_PAYLOAD_AND_REQUESTS), {}))

    assert client.get_block_details('head').version == ''


def test_vebo_exit_requests_lookup_is_skipped_without_el_block_number():
    watcher = MagicMock()
    watcher.keys_source = MagicMock(spec=KeysApiSource)
    exits_info = ValidatorExitsInfo(last_total_requests_processed=7, last_requested_exit_indexes={})

    result = get_last_requested_validator_exit_indexes(watcher, None, exits_info)

    assert result == exits_info
    watcher.execution.lido_contracts.validators_exit_bus_oracle.functions.getTotalRequestsProcessed.assert_not_called()
