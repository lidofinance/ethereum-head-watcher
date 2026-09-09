"""
The startup dump answers "what is this process actually running with" without answering "and what is the key".

Both halves matter: a rotated endpoint that never landed looks exactly like one that did.
"""

import json

from src import variables


def config_with(monkeypatch, **settings) -> dict[str, str]:
    for name, value in settings.items():
        monkeypatch.setattr(variables, name, value)
    return variables.effective_config()


def test_endpoint_lists_are_reduced_to_scheme_and_host(monkeypatch):
    config = config_with(
        monkeypatch,
        CONSENSUS_CLIENT_URI=['https://provider.org/eth/v2/SECRETKEYVALUE', 'http://beacon-fake:5052'],
    )

    assert config['CONSENSUS_CLIENT_URI'] == 'https://provider.org, http://beacon-fake:5052'


def test_no_credential_from_any_endpoint_reaches_the_dump(monkeypatch):
    config = config_with(
        monkeypatch,
        CONSENSUS_CLIENT_URI=['https://cl.example/v2/CLKEYVALUE'],
        EXECUTION_CLIENT_URI=['https://el.example/?key=ELKEYVALUE'],
        KEYS_API_URI=['https://kapi.example/KAPIKEYVALUE'],
        ALERTMANAGER_URI=['https://am.example/AMKEYVALUE'],
    )

    dumped = json.dumps(config)
    for credential in ('CLKEYVALUE', 'ELKEYVALUE', 'KAPIKEYVALUE', 'AMKEYVALUE'):
        assert credential not in dumped


def test_settings_that_only_look_like_secrets_are_shown(monkeypatch):
    """A substring rule on "KEY" would blank both of these, and neither holds a credential."""
    config = config_with(monkeypatch, KEYS_SOURCE='file', KEYS_FILE_PATH='/keys/keys.yml')

    assert config['KEYS_SOURCE'] == 'file'
    assert config['KEYS_FILE_PATH'] == '/keys/keys.yml'


def test_the_dump_covers_the_settings_and_nothing_else():
    config = variables.effective_config()

    assert {'LOG_LEVEL', 'NETWORK_NAME', 'DRY_RUN', 'PROMETHEUS_PORT', 'SECRETS_FILE_PATH'} <= config.keys()
    assert not [name for name in config if name.startswith('_')]
    assert all(isinstance(value, str) for value in config.values())


def test_the_secrets_file_contents_are_not_in_the_dump(monkeypatch):
    monkeypatch.setattr(variables, '_secrets', {'CONSENSUS_CLIENT_URI': 'https://cl.example/v2/FILEKEYVALUE'})

    assert 'FILEKEYVALUE' not in json.dumps(variables.effective_config())
