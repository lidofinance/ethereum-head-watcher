from enum import Enum

from prometheus_client import Gauge, Histogram, Info

from src.variables import PROMETHEUS_PREFIX


class Status(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'


BUILD_INFO = Info(
    'build',
    'Build info',
    namespace=PROMETHEUS_PREFIX,
)

GENESIS_TIME = Gauge(
    'genesis_time',
    'Genesis time',
    namespace=PROMETHEUS_PREFIX,
)

WATCHER_SLOT_NUMBER = Gauge(
    "slot_number",
    "Watcher head slot number",
    namespace=PROMETHEUS_PREFIX,
)

WATCHER_BLOCK_NUMBER = Gauge(
    "block_number",
    "Watcher head block number",
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

KEYS_API_REQUESTS_DURATION = Histogram(
    'keys_api_requests_duration',
    'Duration of requests to Keys API',
    ['endpoint', 'code', 'domain'],
    namespace=PROMETHEUS_PREFIX,
)

KEYS_API_LATEST_BLOCKNUMBER = Gauge(
    'keys_api_latest_blocknumber',
    'Latest blocknumber from Keys API metadata',
    namespace=PROMETHEUS_PREFIX,
)
