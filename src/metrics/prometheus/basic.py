from enum import Enum

from prometheus_client import Counter, Gauge, Histogram, Info

from src.variables import PROMETHEUS_PREFIX


class Status(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'
    # A key changed that nothing here knows how to apply live. Not a failure — the file was read
    # and the rest of it applied — and not a success either, because that key is still the old one.
    NOT_APPLIED = 'not_applied'


BUILD_INFO = Info(
    'build',
    'Build info',
    namespace=PROMETHEUS_PREFIX,
)

# Rotating a node endpoint is invisible otherwise: the old URL keeps answering until the provider revokes it, so "the
# new key never reached the process" and "everything is fine" look identical.
SECRETS_RELOADS = Counter(
    'secrets_reloads',
    'Rotated secrets picked up from the secrets file',
    ['status'],
    namespace=PROMETHEUS_PREFIX,
)

# The counter above moves once per rotation and resets with the process.
SECRETS_FILE_MTIME = Gauge(
    'secrets_file_mtime_seconds',
    'mtime of the secrets file in force, 0 when the configuration came from the environment',
    namespace=PROMETHEUS_PREFIX,
)

FUNCTIONS_DURATION = Histogram(
    'functions_duration',
    'Duration of watcher daemon tasks',
    ['name', 'status'],
    namespace=PROMETHEUS_PREFIX,
)

CL_REQUESTS_DURATION = Histogram(
    'cl_requests_duration',
    'Duration of requests to CL API',
    ['endpoint', 'code', 'domain'],
    namespace=PROMETHEUS_PREFIX,
)

EL_REQUESTS_DURATION = Histogram(
    'el_requests_duration',
    'Duration of requests to EL API',
    ['endpoint', 'code', 'domain', 'call_method', 'call_to'],
    namespace=PROMETHEUS_PREFIX,
)

KEYS_API_REQUESTS_DURATION = Histogram(
    'keys_api_requests_duration',
    'Duration of requests to Keys API',
    ['endpoint', 'code', 'domain'],
    namespace=PROMETHEUS_PREFIX,
)

ALERTMANAGER_REQUESTS_DURATION = Histogram(
    'alertmanager_requests_duration',
    'Duration of requests to Alertmanager',
    ['endpoint', 'code', 'domain'],
    namespace=PROMETHEUS_PREFIX,
)
