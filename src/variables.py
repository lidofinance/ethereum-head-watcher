import os

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# - Providers-
CONSENSUS_CLIENT_URI = os.getenv('CONSENSUS_CLIENT_URI', '').split(',')
KEYS_API_URI = os.getenv('KEYS_API_URI', '').split(',')
ALERTMANAGER_URI = os.getenv('ALERTMANAGER_URI', '').split(',')


CYCLE_SLEEP_IN_SECONDS = int(os.getenv('CYCLE_SLEEP_IN_SECONDS', 1))

HTTP_REQUEST_RETRY_COUNT = int(os.getenv('HTTP_REQUEST_RETRY_COUNT', 5))
HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = int(os.getenv('HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS', 5))
HTTP_REQUEST_TIMEOUT = int(os.getenv('HTTP_REQUEST_TIMEOUT', 5 * 60))

# - Metrics -
PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 9000))
PROMETHEUS_PREFIX = os.getenv("PROMETHEUS_PREFIX", "ethereum_slashing_watcher")

HEALTHCHECK_SERVER_PORT = int(os.getenv('HEALTHCHECK_SERVER_PORT', 9010))

MAX_CYCLE_LIFETIME_IN_SECONDS = int(os.getenv("MAX_CYCLE_LIFETIME_IN_SECONDS", 3000))


def check_uri_required_variables():
    errors = []
    if '' in CONSENSUS_CLIENT_URI:
        errors.append('CONSENSUS_CLIENT_URI')
    if '' in KEYS_API_URI:
        errors.append('KEYS_API_URI')
    if '' in ALERTMANAGER_URI:
        errors.append('ALERTMANAGER_URI')
    return errors


def raise_from_errors(errors):
    if errors:
        raise ValueError("The following variables are required: " + ", ".join(errors))
