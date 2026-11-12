"""Credentials an error or a response body names by key or header, from an endpoint nobody registered."""

import pytest

from src.utils.urls import redact_text

VALUE = 'SECRETVALUE1'


@pytest.mark.parametrize('field', ['api_key', 'apiKey', 'access_token', 'client_secret', 'password', 'Authorization'])
@pytest.mark.parametrize(
    'shape', ['{{"{field}": "{value}"}}', "{{'{field}': '{value}', 'user': 'bot'}}", 'a=1&{field}={value}&b=2']
)
def test_a_named_secret_is_masked(field, shape):
    redacted = redact_text(shape.format(field=field, value=VALUE))

    assert VALUE not in redacted
    assert '****' in redacted


@pytest.mark.parametrize('shape', ['Authorization: Bearer {value}', 'token rejected: Bearer {value}'])
def test_a_bearer_token_is_masked(shape):
    redacted = redact_text(shape.format(value=VALUE))

    assert VALUE not in redacted
    assert 'Bearer' in redacted or 'Authorization' in redacted


def test_the_rest_of_the_message_survives():
    field = 'api_key'
    redacted = redact_text(f'403 from provider: {{"message": "forbidden", "{field}": "{VALUE}", "slot": 12345}}')

    assert redacted == f'403 from provider: {{"message": "forbidden", "{field}": "****", "slot": 12345}}'


def test_keys_and_hashes_are_not_secrets():
    # Validator pubkeys and roots are what makes an alert or an error readable.
    text = "{'key': '0xa1a1', 'pubkey': '0xa2a2', 'root': '0xabc123', 'msg': 'Keys are not loaded'}"

    assert redact_text(text) == text
