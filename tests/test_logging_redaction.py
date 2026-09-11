"""
The formatter is the only thing between a provider key and stdout.

Everything a call site can hand a logger goes through it: a message dict, a plain string with lazy `%s` arguments, a
traceback from a dependency that never heard of masking — and a credential named without the scheme that would make
it look like a URL.
"""

import json
import logging
import sys
import threading

import pytest

from src import variables
from src.metrics.logging import JsonFormatter, log_uncaught
from src.utils import urls

ENDPOINT = 'https://provider.org/ogrpc?network=ethereum&key=SECRETKEYVALUE'


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    """The registry is process-wide and only ever grows, so each test starts from nothing."""
    monkeypatch.setattr(urls, '_parts', {})
    monkeypatch.setattr(urls, '_redaction', None)


def render(record: logging.LogRecord) -> dict:
    return json.loads(JsonFormatter().format(record))


def make_record(msg, args=(), exc_info=None) -> logging.LogRecord:
    return logging.LogRecord('test', logging.ERROR, 'test.py', 1, msg, args, exc_info)


def test_url_in_a_message_dict_field_is_masked():
    rendered = render(make_record({'msg': 'Provider responded with error', 'error': f'timed out on {ENDPOINT}'}))

    assert 'SECRETKEYVALUE' not in json.dumps(rendered)
    assert rendered['error'] == 'timed out on https://provider.org'


def test_url_nested_in_a_message_dict_is_masked():
    rendered = render(make_record({'msg': 'Effective configuration', 'config': {'CONSENSUS_CLIENT_URI': ENDPOINT}}))

    assert rendered['config']['CONSENSUS_CLIENT_URI'] == 'https://provider.org'


def test_url_in_a_list_inside_a_message_dict_is_masked():
    rendered = render(make_record({'msg': 'Endpoints', 'hosts': [ENDPOINT, 'http://kapi-server:3000/v1/keys']}))

    assert rendered['hosts'] == ['https://provider.org', 'http://kapi-server:3000']


def test_url_in_a_plain_message_is_masked():
    rendered = render(make_record('could not reach %s', args=(ENDPOINT,)))

    assert rendered['msg'] == 'could not reach https://provider.org'


def test_url_in_a_rendered_traceback_is_masked():
    """A dependency logging with exc_info is a call site nobody here can reach."""
    error = ConnectionError(f'Max retries exceeded with url: {ENDPOINT}')

    rendered = render(make_record({'msg': 'failed'}, exc_info=(type(error), error, error.__traceback__)))
    last_line = rendered['exc_info'].splitlines()[-1]

    assert 'SECRETKEYVALUE' not in rendered['exc_info']
    # Whole line, not a substring: containment against a host reads as URL validation to the code scanner.
    assert last_line == 'ConnectionError: Max retries exceeded with url: https://provider.org'


def test_the_caller_s_message_dict_is_not_rewritten():
    """Masking is for the log line, not for the dict a caller may still be holding."""
    message = {'msg': 'Provider responded with error', 'error': ENDPOINT}

    render(make_record(message))

    assert message['error'] == ENDPOINT


def test_non_url_text_survives():
    rendered = render(make_record({'msg': 'Block 0xabc123 not found at slot 12345', 'value': 12345}))

    assert rendered['msg'] == 'Block 0xabc123 not found at slot 12345'
    assert rendered['value'] == '12345'


PATH_KEY_ENDPOINT = 'http://provider.invalid:5052/v2/SECRETKEY123/'
QUERY_KEY_ENDPOINT = 'https://provider.invalid/ogrpc?network=ethereum&key=SECRETQUERY'


def test_a_path_segment_key_named_without_a_scheme_is_redacted():
    """What `requests` and `urllib3` actually produce: the failed request named by its path, with no scheme in sight."""
    urls.register_credential_urls([PATH_KEY_ENDPOINT])

    rendered = render(
        make_record(
            'Max retries exceeded with url: /v2/SECRETKEY123/eth/v1/beacon/headers/head (Caused by NameResolutionError)'
        )
    )

    assert 'SECRETKEY123' not in json.dumps(rendered)
    assert rendered['msg'] == (
        'Max retries exceeded with url: /****/eth/v1/beacon/headers/head (Caused by NameResolutionError)'
    )


def test_a_query_string_key_without_a_scheme_is_redacted():
    urls.register_credential_urls([QUERY_KEY_ENDPOINT])

    rendered = render(make_record({'msg': 'failed', 'request': '/ogrpc?network=ethereum&key=SECRETQUERY'}))

    assert 'SECRETQUERY' not in json.dumps(rendered)
    assert rendered['request'] == '/****'


def test_registered_parts_are_redacted_in_nested_fields_and_in_a_traceback():
    urls.register_credential_urls([PATH_KEY_ENDPOINT])
    error = ConnectionError('Max retries exceeded with url: /v2/SECRETKEY123/eth/v1/config/spec')

    rendered = render(
        make_record(
            {'msg': 'failed', 'hosts': {'cl': ['/v2/SECRETKEY123/eth/v1/config/spec']}},
            exc_info=(type(error), error, error.__traceback__),
        )
    )

    assert 'SECRETKEY123' not in json.dumps(rendered)
    assert rendered['hosts']['cl'] == ['/****/eth/v1/config/spec']
    assert '/****/eth/v1/config/spec' in rendered['exc_info']


def test_userinfo_is_redacted():
    urls.register_credential_urls(['https://reader:SECRETPASS@provider.invalid/v2'])

    rendered = render(make_record('rejected by https://reader:SECRETPASS@provider.invalid/v2/eth/v1'))

    assert 'SECRETPASS' not in rendered['msg']
    assert rendered['msg'] == 'rejected by https://provider.invalid'


def test_an_endpoint_with_no_path_registers_nothing():
    """Otherwise a beacon endpoint named in any message would be redacted as if it were a credential."""
    urls.register_credential_urls(['http://beacon-fake:5052'])

    rendered = render(make_record({'msg': 'reading /eth/v1/beacon/headers/head'}))

    assert rendered['msg'] == 'reading /eth/v1/beacon/headers/head'


def test_rotation_registers_the_new_key_and_keeps_the_old_one():
    urls.register_credential_urls([PATH_KEY_ENDPOINT])
    urls.register_credential_urls(['http://provider.invalid:5052/v2/ROTATEDKEY456/'])

    rendered = render(make_record('url: /v2/SECRETKEY123/eth/v1 then url: /v2/ROTATEDKEY456/eth/v1'))

    assert rendered['msg'] == 'url: /****/eth/v1 then url: /****/eth/v1'


def test_the_effective_config_dump_still_shows_scheme_and_host(monkeypatch):
    monkeypatch.setattr(variables, 'CONSENSUS_CLIENT_URI', [PATH_KEY_ENDPOINT])
    urls.register_credential_urls([PATH_KEY_ENDPOINT])

    rendered = render(make_record({'msg': 'Effective configuration', 'config': variables.effective_config()}))

    assert rendered['config']['CONSENSUS_CLIENT_URI'] == 'http://provider.invalid:5052'


def test_a_crash_is_routed_through_the_logger_instead_of_stderr(caplog):
    """Python's default hooks write a traceback straight to stderr, where no formatter can redact it."""
    assert sys.excepthook is log_uncaught
    assert threading.excepthook is not threading.__excepthook__
    urls.register_credential_urls([PATH_KEY_ENDPOINT])
    error = ConnectionError('Max retries exceeded with url: /v2/SECRETKEY123/eth/v1/beacon/genesis')

    with caplog.at_level(logging.CRITICAL):
        log_uncaught(type(error), error, error.__traceback__)

    rendered = render(caplog.records[-1])
    assert 'SECRETKEY123' not in json.dumps(rendered)
    assert '/****/eth/v1/beacon/genesis' in rendered['exc_info']
