import json
import os
import sys
from types import ModuleType

from src.secrets import DEFAULT_POLL_INTERVAL_IN_SECONDS, read_secrets_file
from src.utils.urls import mask_url, register_credential_urls

# Where the secrets agent writes the file, and how often it is re-read. No file: settings come from the environment.
SECRETS_FILE_PATH = os.getenv('SECRETS_FILE_PATH', '/vault/secrets/config')
SECRETS_POLL_INTERVAL_IN_SECONDS = int(os.getenv('SECRETS_POLL_INTERVAL_IN_SECONDS', DEFAULT_POLL_INTERVAL_IN_SECONDS))

_secrets = read_secrets_file(SECRETS_FILE_PATH)
# For main() to report: this module is imported before logging is set up, so read_secrets_file's logs are lost.
SECRETS_FILE_LOADED = bool(_secrets)


def secrets_in_force() -> dict[str, str]:
    """What the file held when this process read it, for a reload to compare a new render against."""
    return dict(_secrets)


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


def parse_slots_range(value: str | None) -> str | None:
    """
    Parse the range of slots to replay, using ``None`` to mean "follow the head".

    Unset and empty have to mean the same thing.
    """
    if value is None or not value.strip():
        return None

    start, separator, end = value.partition('-')
    if not separator or not start.strip().isdigit() or not end.strip().isdigit():
        raise ValueError(f'SLOTS_RANGE must look like "<start>-<end>", got {value!r}')

    if int(start) > int(end):
        raise ValueError(f'SLOTS_RANGE must start before it ends, got {value!r}')

    return f'{int(start)}-{int(end)}'


# Labels an alert may carry on top of the ones the code fills in itself.
# Source of truth is the optional field set of `src.providers.alertmanager.typings.Labels`, which is
# not imported here to keep this module free of dependencies on the rest of the package.
SUPPORTED_ALERTMANAGER_LABELS = frozenset({'mentions', 'slack_mentions'})


def parse_additional_alertmanager_labels(value: str | None) -> dict[str, str]:
    """
    Parse the extra labels put on alerts about our validators. Unset and empty have to mean the same thing.
    """
    if value is None or not value.strip():
        return {}

    try:
        labels = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f'ADDITIONAL_ALERTMANAGER_LABELS must be a JSON object: {error}') from error

    if not isinstance(labels, dict):
        raise ValueError(f'ADDITIONAL_ALERTMANAGER_LABELS must be a JSON object, got {type(labels).__name__}')

    if unsupported := sorted(set(labels) - SUPPORTED_ALERTMANAGER_LABELS):
        # Unknown keys reach `Labels(**additional_labels)` and fail there, which happens only once an
        # alert actually fires
        raise ValueError(
            f'Unsupported labels in ADDITIONAL_ALERTMANAGER_LABELS: {", ".join(unsupported)}. '
            f'Supported labels: {", ".join(sorted(SUPPORTED_ALERTMANAGER_LABELS))}'
        )

    return labels


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# - Providers-
# The node endpoints carry credentials in the URL, which is what the secrets file is for; all four read it alike.
CONSENSUS_CLIENT_URI = setting('CONSENSUS_CLIENT_URI').split(',')
EXECUTION_CLIENT_URI = setting('EXECUTION_CLIENT_URI').split(',')
KEYS_API_URI = setting('KEYS_API_URI').split(',')
ALERTMANAGER_URI = setting('ALERTMANAGER_URI').split(',')

# Here rather than in main(): this module is imported before logging is configured, and anything logged in between
# would otherwise print a credential the formatter does not yet know about.
register_credential_urls(CONSENSUS_CLIENT_URI, EXECUTION_CLIENT_URI, KEYS_API_URI, ALERTMANAGER_URI)

NETWORK_NAME = os.getenv('NETWORK_NAME', 'mainnet')

# Additional labels for alerts for our validators. Must be in JSON string format.
# For example - '{"mentions":"@here"}'
ADDITIONAL_ALERTMANAGER_LABELS = parse_additional_alertmanager_labels(os.getenv('ADDITIONAL_ALERTMANAGER_LABELS'))

DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# Range of slots to replay instead of following the head, as "<start>-<end>". Unset to follow head.
SLOTS_RANGE = parse_slots_range(os.getenv('SLOTS_RANGE'))

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


# The settings whose values carry provider credentials. An explicit list rather than a name pattern: KEYS_SOURCE,
# KEYS_FILE_PATH and KEYS_API_URI all read as secrets to a substring rule, and none of the first two is one.
_CREDENTIAL_BEARING_SETTINGS = ('CONSENSUS_CLIENT_URI', 'EXECUTION_CLIENT_URI', 'KEYS_API_URI', 'ALERTMANAGER_URI')


def effective_config() -> dict[str, str]:
    """Every setting this process runs with, safe to log: endpoint lists reduced to scheme and host."""
    config = {}
    for name, value in vars(sys.modules[__name__]).items():
        if name.startswith('_') or not name.isupper() or callable(value) or isinstance(value, ModuleType):
            continue
        if name in _CREDENTIAL_BEARING_SETTINGS:
            config[name] = ', '.join(mask_url(entry) for entry in value)
        else:
            config[name] = str(value)
    return dict(sorted(config.items()))


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
