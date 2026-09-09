"""
Blockchain RPC metrics in the shape every Lido service reports them: no application prefix, fixed label names.

The `ethereum_head_watcher_*_requests_duration` histograms next door are unchanged — dashboards read them today.
"""

import ipaddress
from typing import Final
from urllib.parse import urlparse

from prometheus_client import Counter, Histogram

# The chain family, not the deployment's network label: NETWORK_NAME says mainnet or hoodi, this says which chain the
# metric names are about.
NETWORK: Final = 'ethereum'

LAYER_CL: Final = 'cl'
LAYER_EL: Final = 'el'

RESULT_SUCCESS: Final = 'success'
RESULT_FAIL: Final = 'fail'

UNKNOWN_CHAIN_ID: Final = 'unknown'

_COMMON_LABELS = ['network', 'layer', 'chain_id', 'provider']

HTTP_RPC_REQUESTS = Counter(
    'http_rpc_requests',
    'HTTP requests to a blockchain node',
    [*_COMMON_LABELS, 'batched', 'response_code', 'result'],
)

HTTP_RPC_RESPONSE_SECONDS = Histogram(
    'http_rpc_response_seconds',
    'Time to a response from a blockchain node',
    _COMMON_LABELS,
)

RPC_REQUESTS = Counter(
    'rpc_request',
    'Calls to a blockchain node, by method',
    [*_COMMON_LABELS, 'method', 'result', 'rpc_error_code'],
)

_chain_ids: dict[str, str] = {LAYER_CL: UNKNOWN_CHAIN_ID, LAYER_EL: UNKNOWN_CHAIN_ID}


def set_chain_id(layer: str, value: int | str | None) -> None:
    _chain_ids[layer] = UNKNOWN_CHAIN_ID if value is None else str(value)


def chain_id(layer: str) -> str:
    return _chain_ids.get(layer, UNKNOWN_CHAIN_ID)


def normalize_provider(url: str) -> str:
    """
    Which provider answered, with nothing in it that could identify a request or carry a credential.

    A DNS name is cut to its last two labels; an address or a single-label in-cluster name keeps its port instead,
    since that is the only thing telling two of them on one host apart.
    """
    netloc = urlparse(url).netloc.lower() or url.lower()
    netloc = netloc.rpartition('@')[2]
    if netloc.startswith('['):
        return netloc
    host, separator, port = netloc.partition(':')
    labels = host.split('.')
    if len(labels) >= 2 and not _is_ipv4(host):
        return '.'.join(labels[-2:])
    return f'{host}{separator}{port}'


def response_code_class(status: int | None) -> str:
    """`2xx`, `5xx`, and an empty string when the request never got a response."""
    if status is None:
        return ''
    return f'{status // 100}xx'


def observe_rpc_request(
    layer: str,
    provider_url: str,
    method: str,
    duration: float,
    status: int | None,
    result: str,
    rpc_error_code: str = '',
) -> None:
    """One round trip to a node, in all three metrics."""
    common = {
        'network': NETWORK,
        'layer': layer,
        'chain_id': chain_id(layer),
        'provider': normalize_provider(provider_url),
    }
    HTTP_RPC_REQUESTS.labels(
        **common,
        # Both callers send one request per call; nothing here batches.
        batched='false',
        response_code=response_code_class(status),
        result=result,
    ).inc()
    HTTP_RPC_RESPONSE_SECONDS.labels(**common).observe(duration)
    RPC_REQUESTS.labels(**common, method=method, result=result, rpc_error_code=rpc_error_code).inc()


def _is_ipv4(host: str) -> bool:
    try:
        ipaddress.IPv4Address(host)
    except ValueError:
        return False
    return True
