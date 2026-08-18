import json
import os

from src.secrets import DEFAULT_POLL_INTERVAL_IN_SECONDS, read_secrets_file

# Where the OpenBao agent writes the secrets file, and how often it is re-read. Absent file means
# every setting comes from the environment, which is how the VM deployment runs. See src/secrets.py.
SECRETS_FILE_PATH = os.getenv('SECRETS_FILE_PATH', '/vault/secrets/config')
SECRETS_POLL_INTERVAL_IN_SECONDS = int(os.getenv('SECRETS_POLL_INTERVAL_IN_SECONDS', DEFAULT_POLL_INTERVAL_IN_SECONDS))

_secrets = read_secrets_file(SECRETS_FILE_PATH)
# Whether that file was there, for main() to report. This module is imported before logging is
# configured, so anything read_secrets_file logs at import time is dropped — and "where did this
# process get its endpoints" is the first question when a rotated key does not seem to have landed.
SECRETS_FILE_LOADED = bool(_secrets)


def setting(name: str, default: str = '') -> str:
    """The secrets file wins over the environment, so a rotated value is not shadowed by a stale env."""
    value = _secrets.get(name)
    if value:
        return value
    return os.getenv(name, default)


def parse_enabled_handlers(value: str | None) -> list[str] | None:
    """Parse handler names, using ``None`` to represent the default handler set."""
    if value is None:
        return None
    handlers = [handler.strip() for handler in value.split(',') if handler.strip()]
    if not handlers:
        raise ValueError('ENABLED_HANDLERS must contain at least one handler name')
    return handlers


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# - Providers-
# The two node endpoints carry provider credentials in the URL, so they are the values the
# secrets file exists for. The other two are read the same way so that a deployment can choose
# where to keep them without a code change.
CONSENSUS_CLIENT_URI = setting('CONSENSUS_CLIENT_URI').split(',')
EXECUTION_CLIENT_URI = setting('EXECUTION_CLIENT_URI').split(',')
KEYS_API_URI = setting('KEYS_API_URI').split(',')
ALERTMANAGER_URI = setting('ALERTMANAGER_URI').split(',')

NETWORK_NAME = os.getenv('NETWORK_NAME', 'mainnet')

# Additional labels for alerts for our validators. Must be in JSON string format.
# For example - '{"a":"valueA","b":"valueB"}'
ADDITIONAL_ALERTMANAGER_LABELS = json.loads(os.getenv('ADDITIONAL_ALERTMANAGER_LABELS', '{}'))

DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

SLOTS_RANGE = os.getenv('SLOTS_RANGE')

CYCLE_SLEEP_IN_SECONDS = int(os.getenv('CYCLE_SLEEP_IN_SECONDS', 1))

KEYS_SOURCE = os.getenv('KEYS_SOURCE', 'keys_api')

KEYS_FILE_PATH = os.getenv('KEYS_FILE_PATH', './docker/validators/keys.yml')

KEYS_API_REQUEST_TIMEOUT = int(os.getenv('KEYS_API_REQUEST_TIMEOUT', 3 * 60))
KEYS_API_REQUEST_RETRY_COUNT = int(os.getenv('KEYS_API_REQUEST_RETRY_COUNT', 3))
KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = int(os.getenv('KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS', 5))

ALERTMANAGER_REQUEST_TIMEOUT = int(os.getenv('ALERTMANAGER_REQUEST_TIMEOUT', 2))
ALERTMANAGER_REQUEST_RETRY_COUNT = int(os.getenv('ALERTMANAGER_REQUEST_RETRY_COUNT', 2))
ALERTMANAGER_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = int(
    os.getenv('ALERTMANAGER_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS', 1)
)

CL_REQUEST_TIMEOUT = float(os.getenv('CL_REQUEST_TIMEOUT', 3 * 60))
CL_REQUEST_RETRY_COUNT = int(os.getenv('CL_REQUEST_RETRY_COUNT', 3))
CL_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = float(os.getenv('CL_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS', 5))

EL_REQUEST_TIMEOUT = float(os.getenv('EL_REQUEST_TIMEOUT', 5))
EVENTS_SEARCH_STEP = int(os.getenv('EVENTS_SEARCH_STEP', 10000))

LIDO_LOCATOR_ADDRESS = os.getenv('LIDO_LOCATOR_ADDRESS', '')
LIDO_CONSOLIDATION_BUS_ADDRESS = os.getenv('LIDO_CONSOLIDATION_BUS_ADDRESS', '')

VALID_WITHDRAWAL_ADDRESSES = [x.lower() for x in os.getenv('VALID_WITHDRAWAL_ADDRESSES', '').split(',') if x]

DISABLE_UNEXPECTED_EXIT_ALERTS = [x.strip() for x in os.getenv('DISABLE_UNEXPECTED_EXIT_ALERTS', '').split(',') if x]

ENABLED_HANDLERS = os.getenv('ENABLED_HANDLERS')

# - Metrics -
PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 9000))
PROMETHEUS_PREFIX = os.getenv("PROMETHEUS_PREFIX", "ethereum_head_watcher")

HEALTHCHECK_SERVER_PORT = int(os.getenv('HEALTHCHECK_SERVER_PORT', 9010))
HEALTHCHECK_SERVER_HOST = os.getenv('HEALTHCHECK_SERVER_HOST', '0.0.0.0')

MAX_CYCLE_LIFETIME_IN_SECONDS = int(os.getenv("MAX_CYCLE_LIFETIME_IN_SECONDS", 3000))


def check_uri_required_variables():
    errors = []
    if '' in CONSENSUS_CLIENT_URI:
        errors.append('CONSENSUS_CLIENT_URI')
    if not DRY_RUN and '' in ALERTMANAGER_URI:
        errors.append('ALERTMANAGER_URI')
    if KEYS_SOURCE == 'keys_api':
        if '' in KEYS_API_URI:
            errors.append('KEYS_API_URI')
        if '' == LIDO_LOCATOR_ADDRESS:
            errors.append('LIDO_LOCATOR_ADDRESS')
        if '' in EXECUTION_CLIENT_URI:
            errors.append('EXECUTION_CLIENT_URI')
    return errors


def raise_from_errors(errors):
    if errors:
        raise ValueError(
            "The following variables are required: "
            + ", ".join(errors)
            + f" (read from {SECRETS_FILE_PATH} when it exists, otherwise from the environment)"
        )
