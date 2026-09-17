from enum import Enum

from prometheus_client import Histogram, Info

from src.variables import PROMETHEUS_PREFIX


class Status(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'


BUILD_INFO = Info(
    'build',
    'Build info',
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
