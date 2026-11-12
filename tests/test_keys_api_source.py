"""When the Keys API source decides the keys have not changed."""

from types import SimpleNamespace

import pytest

from src.keys_source.keys_api_source import KeysApiSource


class KeysApiStub:
    def __init__(self):
        self.operator_reads = 0

    def get_status(self):
        return SimpleNamespace(elBlockSnapshot={'timestamp': 1})

    def get_modules(self):
        return [{'nonce': 5}], None

    def get_operators_stream(self):
        self.operator_reads += 1
        raise ConnectionError('Keys API dropped the stream')


def test_a_failed_load_is_retried_rather_than_taken_as_unchanged():
    source = KeysApiSource()
    source.keys_api = KeysApiStub()

    for _ in range(2):
        with pytest.raises(ConnectionError):
            source.update_keys()

    assert source.keys_api.operator_reads == 2
