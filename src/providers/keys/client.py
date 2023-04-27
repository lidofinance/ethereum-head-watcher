from time import sleep
from typing import Optional, cast

from src.metrics.prometheus.basic import KEYS_API_REQUESTS_DURATION, KEYS_API_LATEST_BLOCKNUMBER
from src.providers.http_provider import HTTPProvider
from src.providers.keys.typings import LidoKey, KeysApiStatus, LidoModuleOperators, LidoModule
from src import variables
from src.typings import BlockNumber
from src.utils.dataclass import list_of_dataclasses


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

    USED_KEYS = 'v1/keys?used=true'
    OPERATORS = 'v1/operators'
    STATUS = 'v1/status'

    def _get_with_blockstamp(self, url: str, block_number: BlockNumber, params: Optional[dict] = None) -> dict | list:
        """
        Returns response if blockstamp < blockNumber from response
        """
        for i in range(variables.HTTP_REQUEST_RETRY_COUNT):
            data, meta = self._get(url, query_params=params)
            if meta.get('meta'):
                blocknumber_meta = meta['meta']['elBlockSnapshot']['blockNumber']
            else:
                blocknumber_meta = meta['elBlockSnapshot']['blockNumber']
            KEYS_API_LATEST_BLOCKNUMBER.set(blocknumber_meta)
            if blocknumber_meta >= block_number:
                return data

            if i != variables.HTTP_REQUEST_RETRY_COUNT - 1:
                sleep(variables.HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS)

        raise KeysOutdatedException(
            f'Keys API Service stuck, no updates for {variables.HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS * variables.HTTP_REQUEST_RETRY_COUNT} seconds.'
        )

    def get_used_lido_keys(self, block_number: BlockNumber) -> list[dict]:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/keys/KeysController_get"""
        return cast(list[dict], self._get_with_blockstamp(self.USED_KEYS, block_number))

    @list_of_dataclasses(LidoModuleOperators.from_response)
    def get_operators(self, block_number: BlockNumber) -> list[dict]:
        return cast(list[dict], self._get_with_blockstamp(self.OPERATORS, block_number))

    @list_of_dataclasses(LidoModule.from_response)
    def get_modules(self, block_number: BlockNumber) -> list[dict]:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/modules/SRModulesController_getModules"""
        return cast(list[dict], self._get_with_blockstamp('v1/modules', block_number))

    def get_status(self) -> KeysApiStatus:
        """Docs: https://keys-api.lido.fi/api/static/index.html#/status/StatusController_get"""
        data, _ = self._get(self.STATUS)
        return KeysApiStatus.from_response(**cast(dict, data))
