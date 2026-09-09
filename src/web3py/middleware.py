import json
import logging
import os
import time
from http import HTTPStatus
from typing import Any, Callable
from urllib.parse import urlparse

from requests import HTTPError, Response
from web3 import Web3
from web3.types import RPCEndpoint, RPCResponse
from web3_multi_provider import NoActiveProviderError

from src.metrics.prometheus.basic import EL_REQUESTS_DURATION
from src.metrics.prometheus.rpc import (
    LAYER_EL,
    RESULT_FAIL,
    RESULT_SUCCESS,
    observe_rpc_request,
)

logger = logging.getLogger(__name__)


def metrics_collector(
    make_request: Callable[[RPCEndpoint, Any], RPCResponse],
    w3: Web3,
) -> Callable[[RPCEndpoint, Any], RPCResponse]:
    """
    Works correctly with MultiProvider and vanilla Providers.

    EL_REQUESTS_DURATION - HISTOGRAM with requests time, count, response codes and request domain.
    """

    contracts = []

    abi_dir = './assets/'
    for filename in os.listdir(abi_dir):
        with open(os.path.join(abi_dir, filename), 'r') as f:
            try:
                contracts.append(w3.eth.contract(abi=json.load(f)))
            except json.JSONDecodeError:
                pass

    def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        try:
            # Works only with HTTP and Websocket Provider
            endpoint_uri = getattr(w3.provider, "endpoint_uri")
            domain = urlparse(endpoint_uri).netloc
        except:
            endpoint_uri = ''
            domain = 'unavailable'

        def observe(started: float, status: int | None, result: str, rpc_error_code: str = '') -> None:
            observe_rpc_request(
                layer=LAYER_EL,
                # FallbackProvider fixes `endpoint_uri` to the first configured endpoint and never moves it, so this
                # names the head of the list, not whichever endpoint answered. The `domain` label has the same flaw.
                provider_url=endpoint_uri,
                method=method,
                duration=time.monotonic() - started,
                status=status,
                result=result,
                rpc_error_code=rpc_error_code,
            )

        call_method = ''
        call_to = ''
        if method == 'eth_call':
            args = params[0]
            call_to = args['to']
            for contract in contracts:
                try:
                    call_method = contract.get_function_by_selector(args['data']).fn_name
                except ValueError:
                    pass
                if call_method:
                    break
        if method == 'eth_getBalance':
            call_to = params[0]

        started = time.monotonic()
        with EL_REQUESTS_DURATION.time() as t:
            try:
                response = make_request(method, params)
            except HTTPError as ex:
                failed: Response = ex.response
                t.labels(
                    endpoint=method,
                    call_method=call_method,
                    call_to=call_to,
                    code=failed.status_code,
                    domain=domain,
                )
                observe(started, failed.status_code, RESULT_FAIL)
                raise ex
            except NoActiveProviderError:
                t.labels(
                    endpoint=method,
                    call_method=call_method,
                    call_to=call_to,
                    code=None,
                    domain=domain,
                )
                observe(started, None, RESULT_FAIL)
                raise

            # https://www.jsonrpc.org/specification#error_object
            error = response.get("error")
            code: int = 0
            if isinstance(error, dict):
                code = error.get("code") or code

            t.labels(
                endpoint=method,
                call_method=call_method,
                call_to=call_to,
                code=code,
                domain=domain,
            )
            observe(
                started,
                # web3 raises on anything but a 2xx, so a response in hand was one.
                HTTPStatus.OK,
                RESULT_FAIL if isinstance(error, dict) else RESULT_SUCCESS,
                str(code) if isinstance(error, dict) else '',
            )

            return response

    return middleware
