import json
import os

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# - Providers-
CONSENSUS_CLIENT_URI = os.getenv('CONSENSUS_CLIENT_URI', '').split(',')
EXECUTION_CLIENT_URI = os.getenv('EXECUTION_CLIENT_URI', '').split(',')
KEYS_API_URI = os.getenv('KEYS_API_URI', '').split(',')
ALERTMANAGER_URI = os.getenv('ALERTMANAGER_URI', '').split(',')

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

LIDO_LOCATOR_ADDRESS = os.getenv('LIDO_LOCATOR_ADDRESS', '')

VALID_WITHDRAWAL_ADDRESSES = os.getenv('VALID_WITHDRAWAL_ADDRESSES', '').split(',')

# - Metrics -
PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 9000))
PROMETHEUS_PREFIX = os.getenv("PROMETHEUS_PREFIX", "ethereum_head_watcher")

HEALTHCHECK_SERVER_PORT = int(os.getenv('HEALTHCHECK_SERVER_PORT', 9010))

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
        raise ValueError("The following variables are required: " + ", ".join(errors))
