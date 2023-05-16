from typing import cast

from requests import Response

from src.metrics.prometheus.basic import KEYS_API_REQUESTS_DURATION
from src.providers.http_provider import HTTPProvider
from src.providers.keys.typings import KeysApiStatus
from src.variables import (
    KEYS_API_REQUEST_TIMEOUT,
    KEYS_API_REQUEST_RETRY_COUNT,
    KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS,
)


class KeysOutdatedException(Exception):
    pass


class KeysAPIClient(HTTPProvider):
    """
    Lido Keys are stored in different modules in on-chain and off-chain format.
    Keys API service fetches all lido keys and provide them in convenient format.
    Keys could not be deleted, so the amount of them always increasing.
    One thing to check before use data from Keys API service is that latest fetched block in meta field is greater
    than the block we are fetching on.

    Keys API specification can be found here https://keys-api.lido.fi/api/static/index.html
    """

    PROMETHEUS_HISTOGRAM = KEYS_API_REQUESTS_DURATION

    HTTP_REQUEST_TIMEOUT = KEYS_API_REQUEST_TIMEOUT
    HTTP_REQUEST_RETRY_COUNT = KEYS_API_REQUEST_RETRY_COUNT
    HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS

    USED_KEYS = 'v1/keys?used=true'
    OPERATORS = 'v1/operators'
    MODULES = 'v1/modules'
    STATUS = 'v1/status'

    def get_used_lido_keys_stream(self) -> Response:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/keys/KeysController_get"""
        return self._get_stream(self.USED_KEYS)

    def get_operators_stream(self) -> Response:
        return self._get_stream(self.OPERATORS)

    def get_modules(self) -> list[dict]:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/modules/SRModulesController_getModules"""
        return cast(list[dict], self._get(self.MODULES))

    def get_status(self) -> KeysApiStatus:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/status/StatusController_get"""
        data, _ = self._get(self.STATUS)
        return KeysApiStatus.from_response(**cast(dict, data))
