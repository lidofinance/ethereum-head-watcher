from typing import cast

from json_stream.base import TransientStreamingJSONList
from requests import Response

from src.metrics.prometheus.basic import KEYS_API_REQUESTS_DURATION
from src.providers.http_provider import HTTPProvider
from src.providers.keys.typings import KeysApiStatus, LidoNamedKey
from src.variables import (
    KEYS_API_REQUEST_RETRY_COUNT,
    KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS,
    KEYS_API_REQUEST_TIMEOUT,
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
        return self.get_stream(self.USED_KEYS)

    def get_operators_stream(self) -> Response:
        return self.get_stream(self.OPERATORS)

    def get_modules(self) -> list[dict]:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/modules/SRModulesController_getModules"""
        return cast(list[dict], self.get(self.MODULES))

    def get_status(self) -> KeysApiStatus:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/status/StatusController_get"""
        data, _ = self.get(self.STATUS)
        return KeysApiStatus.from_response(**cast(dict, data))

    @staticmethod
    def parse_modules(
        data: TransientStreamingJSONList,
    ) -> tuple[dict[tuple[str, str], tuple[str, str]], dict[str, list[str]],]:
        module_operators: dict[str, list[str]] = {}
        module_operator_name: dict[tuple[str, str], tuple[str, str]] = {}
        for module in data.persistent():
            staking_module_index = module["module"]["id"]
            staking_module_address = module["module"]["stakingModuleAddress"]
            for operator in module["operators"]:
                module_operator_name[(staking_module_address, operator["index"])] = (
                    staking_module_index,
                    operator["name"],
                )
                module_operators.setdefault(module["module"]["id"], []).append(operator["index"])
        return module_operator_name, module_operators

    @staticmethod
    def parse_keys(
        data: TransientStreamingJSONList, modules_operators_dict: dict[tuple[str, str], tuple[str, str]]
    ) -> dict[str, LidoNamedKey]:
        keys = {}
        for lido_key in data.persistent():
            pubkey = lido_key['key']
            module_index, operator_name = modules_operators_dict[(lido_key['moduleAddress'], lido_key['operatorIndex'])]
            keys[pubkey] = LidoNamedKey(
                key=pubkey,
                operatorIndex=lido_key['operatorIndex'],
                operatorName=operator_name,
                moduleIndex=module_index,
            )
        return keys
