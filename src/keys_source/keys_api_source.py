import logging

import json_stream.requests

from src import variables
from src.keys_source.base_source import BaseSource
from src.providers.keys_api.client import KeysAPIClient
from src.providers.keys_api.typings import KeysApiStatus

logger = logging.getLogger()


class KeysApiSource(BaseSource):
    def __init__(self):
        self.keys_api = KeysAPIClient(variables.KEYS_API_URI)
        self.keys_api_status: KeysApiStatus | None = None
        self.keys_api_nonce: int = 0
        self.modules_operators_dict: dict[str, list[str]] = {}

    def update_keys(self):
        """
        Returns updated keys if keys api nonce was changed and keys were updated
        """
        current_keys_status = self.keys_api.get_status()
        if self.keys_api_status is not None and (
            self.keys_api_status.elBlockSnapshot['timestamp'] >= current_keys_status.elBlockSnapshot['timestamp']
        ):
            return None

        # Get modules and calculate current nonce
        # If nonce is not changed - we don't need to update keys
        modules = self.keys_api.get_modules()[0]

        current_nonce = sum(module['nonce'] for module in modules)
        if self.keys_api_nonce == current_nonce:
            return None
        self.keys_api_nonce = current_nonce

        logger.info({'msg': 'Updating User keys'})
        modules_operators_stream = self.keys_api.get_operators_stream()
        module_operators_name, self.modules_operators_dict = KeysAPIClient.parse_modules(
            json_stream.requests.load(modules_operators_stream)['data']
        )

        fetched_lido_keys_stream = self.keys_api.get_used_lido_keys_stream()
        user_keys = KeysAPIClient.parse_keys(
            json_stream.requests.load(fetched_lido_keys_stream)['data'], module_operators_name
        )

        self.keys_api_status = current_keys_status

        return user_keys
