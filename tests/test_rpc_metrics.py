"""
The cross-service RPC metrics, and the labels that decide whether they are readable.

Two things: a label never carries a credential or a per-request value, and only the node providers report these.
"""

import pytest
from prometheus_client import REGISTRY
from urllib3 import Retry

from src.metrics.prometheus import rpc
from src.metrics.prometheus.rpc import LAYER_CL, normalize_provider, response_code_class
from src.providers.alertmanager.client import AlertmanagerClient
from src.providers.consensus.client import ConsensusClient
from src.providers.keys_api.client import KeysAPIClient
from src.utils.build import user_agent
from tests.node_fake import BeaconNodeFake

NO_RETRIES = Retry(total=0)


@pytest.fixture
def node():
    fake = BeaconNodeFake(chain_id=17000).start()
    yield fake
    fake.stop()


@pytest.fixture(autouse=True)
def restore_chain_ids():
    before = dict(rpc._chain_ids)  # pylint: disable=protected-access
    yield
    rpc._chain_ids.update(before)  # pylint: disable=protected-access


def requests_total(**labels) -> float:
    return REGISTRY.get_sample_value('http_rpc_requests_total', labels) or 0.0


def calls_total(**labels) -> float:
    return REGISTRY.get_sample_value('rpc_request_total', labels) or 0.0


def response_count(**labels) -> float:
    return REGISTRY.get_sample_value('http_rpc_response_seconds_count', labels) or 0.0


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('https://lb.drpc.org/ogrpc?network=ethereum&key=SECRET', 'drpc.org'),
        ('https://eth-mainnet.provider.com/v2/SECRET', 'provider.com'),
        ('https://Provider.COM', 'provider.com'),
        ('https://user:pass@provider.com/v2', 'provider.com'),
        # No second-level domain to cut to, so the port stays: it is the only thing telling two
        # in-cluster services on one host apart.
        ('http://beacon-fake:5052', 'beacon-fake:5052'),
        ('http://beacon-fake', 'beacon-fake'),
        ('http://127.0.0.1:8545', '127.0.0.1:8545'),
        ('http://[::1]:8545', '[::1]:8545'),
    ],
)
def test_provider_label_keeps_the_provider_and_nothing_else(url, expected):
    assert normalize_provider(url) == expected


@pytest.mark.parametrize(('status', 'expected'), [(200, '2xx'), (404, '4xx'), (503, '5xx'), (None, '')])
def test_response_code_is_aggregated_to_a_class(status, expected):
    assert response_code_class(status) == expected


def test_a_consensus_call_is_counted_with_its_endpoint_as_the_method(node):
    rpc.set_chain_id(LAYER_CL, 17000)
    labels = {'network': 'ethereum', 'layer': 'cl', 'chain_id': '17000', 'provider': normalize_provider(node.url)}
    before = requests_total(**labels, batched='false', response_code='2xx', result='success')
    before_calls = calls_total(**labels, method=ConsensusClient.API_GET_GENESIS, result='success', rpc_error_code='')
    before_observations = response_count(**labels)

    ConsensusClient([node.url]).get_genesis()

    assert requests_total(**labels, batched='false', response_code='2xx', result='success') == before + 1
    assert (
        calls_total(**labels, method=ConsensusClient.API_GET_GENESIS, result='success', rpc_error_code='')
        == before_calls + 1
    )
    assert response_count(**labels) == before_observations + 1


def test_a_not_found_is_a_failure_with_its_status_class(node):
    labels = {'network': 'ethereum', 'layer': 'cl', 'chain_id': 'unknown', 'provider': normalize_provider(node.url)}
    before = requests_total(**labels, batched='false', response_code='4xx', result='fail')

    with pytest.raises(Exception):
        ConsensusClient([node.url]).get(ConsensusClient.API_GET_SPEC + '/nothing-here', retry_strategy=NO_RETRIES)

    assert requests_total(**labels, batched='false', response_code='4xx', result='fail') == before + 1


def test_an_unreachable_endpoint_is_counted_without_a_response_code():
    unreachable = 'http://127.0.0.1:1'
    labels = {'network': 'ethereum', 'layer': 'cl', 'chain_id': 'unknown', 'provider': '127.0.0.1:1'}
    before = requests_total(**labels, batched='false', response_code='', result='fail')

    with pytest.raises(Exception):
        ConsensusClient([unreachable]).get(ConsensusClient.API_GET_GENESIS, retry_strategy=NO_RETRIES)

    assert requests_total(**labels, batched='false', response_code='', result='fail') == before + 1


def test_the_chain_id_comes_from_the_consensus_spec(node):
    assert ConsensusClient([node.url]).get_deposit_chain_id() == 17000


def test_the_chain_id_is_unknown_until_it_is_resolved():
    assert rpc.chain_id('cl') == 'unknown'


def test_the_keys_api_and_the_alertmanager_are_not_rpc(node):
    """Nothing about them is a node call, and a `layer` label would have to lie about which one they are."""
    before = sum(
        sample.value for metric in REGISTRY.collect() if metric.name == 'http_rpc_requests' for sample in metric.samples
    )

    for client in (KeysAPIClient([node.url]), AlertmanagerClient([node.url])):
        with pytest.raises(Exception):
            client.get('v1/nothing-here', retry_strategy=NO_RETRIES)

    after = sum(
        sample.value for metric in REGISTRY.collect() if metric.name == 'http_rpc_requests' for sample in metric.samples
    )
    assert after == before


def test_requests_identify_this_application_to_the_provider(node):
    ConsensusClient([node.url]).get_genesis()

    assert node.user_agents == [user_agent()]
    assert node.user_agents[0].startswith('ethereum-head-watcher/')
