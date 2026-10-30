import time
from http import HTTPStatus
from typing import Any, Callable

from requests import HTTPError
from web3 import Web3
from web3.types import RPCEndpoint, RPCResponse
from web3_multi_provider import FallbackProvider

from src.metrics.prometheus.rpc import (
    LAYER_EL,
    RESULT_FAIL,
    RESULT_SUCCESS,
    observe_rpc_request,
)
from src.providers.consistency import ProviderConsistencyModule


class FallbackProviderModule(ProviderConsistencyModule, FallbackProvider):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Measured per endpoint: from outside, a call that fell back looks like one call to the first endpoint
        for provider in self._providers:  # type: ignore[attr-defined]
            provider.make_request = self._observed(provider)

    def get_all_providers(self) -> list[Any]:
        return self._providers  # type: ignore[attr-defined]

    def _get_chain_id_with_provider(self, provider_index: int) -> int:
        return Web3.to_int(hexstr=self._providers[provider_index].make_request("eth_chainId", []).get('result'))  # type: ignore[attr-defined]

    def _observed(self, provider: Any) -> Callable[[RPCEndpoint, Any], RPCResponse]:
        make_request = provider.make_request

        def observed(method: RPCEndpoint, params: Any) -> RPCResponse:
            started = time.monotonic()

            def observe(status: int | None, result: str, rpc_error_code: str = '') -> None:
                observe_rpc_request(
                    layer=LAYER_EL,
                    provider_url=provider.endpoint_uri,
                    method=method,
                    duration=time.monotonic() - started,
                    status=status,
                    result=result,
                    rpc_error_code=rpc_error_code,
                )

            try:
                response = make_request(method, params)
            except HTTPError as ex:
                observe(ex.response.status_code if ex.response is not None else None, RESULT_FAIL)
                raise
            except Exception:
                observe(None, RESULT_FAIL)
                raise

            # https://www.jsonrpc.org/specification#error_object
            error = response.get("error")
            if isinstance(error, dict):
                observe(HTTPStatus.OK, RESULT_FAIL, str(error.get("code") or 0))
            else:
                observe(HTTPStatus.OK, RESULT_SUCCESS)
            # Read by the metrics middleware for the `domain` label
            self.endpoint_uri = provider.endpoint_uri
            return response

        return observed
