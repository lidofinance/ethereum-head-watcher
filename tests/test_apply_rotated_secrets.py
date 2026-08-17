"""
The rotation is applied to live client objects, so these tests build real ones — a real Web3 with
the real fallback provider, and the real HTTP clients. Nothing here talks to a node: a swap is a
change of endpoint lists, and asserting on the lists is the whole point.

The regression worth naming: `Web3.provider` has no setter in web3 6.x, so an obvious-looking
`web3.provider = ...` raises AttributeError. It would be swallowed by the watcher's callback guard
and logged as a failed reload — a rotation that quietly never lands. That is what
test_execution_endpoints_are_swapped covers.
"""

import pytest

from src import variables
from src.main import _split, apply_rotated_secrets
from src.providers.alertmanager.client import AlertmanagerClient
from src.providers.consensus.client import ConsensusClient
from src.providers.keys_api.client import KeysAPIClient
from src.web3py.extensions import FallbackProviderModule
from src.web3py.typings import Web3


class KeysApiSourceStub:
    def __init__(self, hosts):
        self.keys_api = KeysAPIClient(hosts)


class FileSourceStub:
    """The keys-from-file mode has no Keys API client at all — and no web3 either."""


class WatcherStub:
    def __init__(self, keys_source=None, execution=None):
        self.consensus = ConsensusClient(['https://cl-old'])
        self.alertmanager = AlertmanagerClient(['http://am-old:9093'])
        self.keys_source = keys_source if keys_source is not None else KeysApiSourceStub(['http://kapi-old:3000'])
        self.execution = execution


@pytest.fixture
def execution_uri_restored():
    original = variables.EXECUTION_CLIENT_URI
    yield
    variables.EXECUTION_CLIENT_URI = original


def test_consensus_endpoints_are_swapped():
    watcher = WatcherStub()

    changed = apply_rotated_secrets({'CONSENSUS_CLIENT_URI': 'https://cl-a,https://cl-b'}, watcher)

    assert changed == ['CONSENSUS_CLIENT_URI']
    assert watcher.consensus.hosts == ['https://cl-a', 'https://cl-b']


def test_keys_api_and_alertmanager_endpoints_are_swapped():
    watcher = WatcherStub()

    changed = apply_rotated_secrets(
        {'KEYS_API_URI': 'http://kapi-new:3000', 'ALERTMANAGER_URI': 'http://am-new:9093'}, watcher
    )

    assert sorted(changed) == ['ALERTMANAGER_URI', 'KEYS_API_URI']
    assert watcher.keys_source.keys_api.hosts == ['http://kapi-new:3000']
    assert watcher.alertmanager.hosts == ['http://am-new:9093']


def test_execution_endpoints_are_swapped(execution_uri_restored):
    web3 = Web3(FallbackProviderModule(['https://el-old'], request_kwargs={'timeout': 5}))
    watcher = WatcherStub(execution=web3)
    variables.EXECUTION_CLIENT_URI = ['https://el-old']

    changed = apply_rotated_secrets({'EXECUTION_CLIENT_URI': 'https://el-new'}, watcher)

    assert changed == ['EXECUTION_CLIENT_URI']
    assert web3.provider._hosts_uri == ['https://el-new']
    assert variables.EXECUTION_CLIENT_URI == ['https://el-new']


def test_middlewares_survive_the_execution_swap(execution_uri_restored):
    def marker_middleware(make_request, _w3):
        return make_request

    web3 = Web3(FallbackProviderModule(['https://el-old'], request_kwargs={'timeout': 5}))
    web3.middleware_onion.add(marker_middleware, 'marker')
    watcher = WatcherStub(execution=web3)
    variables.EXECUTION_CLIENT_URI = ['https://el-old']

    apply_rotated_secrets({'EXECUTION_CLIENT_URI': 'https://el-new'}, watcher)

    # The metrics collector and the cache are attached this way; losing them on rotation would
    # silently stop the EL metrics rather than break anything visible.
    assert 'marker' in web3.middleware_onion


def test_unchanged_values_are_not_reapplied():
    watcher = WatcherStub()

    changed = apply_rotated_secrets({'CONSENSUS_CLIENT_URI': 'https://cl-old'}, watcher)

    assert changed == []


def test_missing_and_empty_keys_are_left_alone():
    watcher = WatcherStub()

    changed = apply_rotated_secrets({'CONSENSUS_CLIENT_URI': '', 'KEYS_API_URI': '  '}, watcher)

    # An empty value in a rendered secret is a rotation gone wrong, not an instruction to point a
    # client at nothing — the previous endpoints stay.
    assert changed == []
    assert watcher.consensus.hosts == ['https://cl-old']
    assert watcher.keys_source.keys_api.hosts == ['http://kapi-old:3000']


def test_file_keys_source_has_no_keys_api_to_swap():
    watcher = WatcherStub(keys_source=FileSourceStub())

    changed = apply_rotated_secrets({'KEYS_API_URI': 'http://kapi-new:3000'}, watcher)

    assert changed == []


def test_split_trims_and_drops_empties():
    assert _split(' https://a , https://b ,') == ['https://a', 'https://b']
    assert _split(None) == []
