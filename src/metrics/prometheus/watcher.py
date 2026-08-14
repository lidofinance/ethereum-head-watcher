from prometheus_client import Counter, Gauge

from src.variables import PROMETHEUS_PREFIX

GENESIS_TIME = Gauge(
    'genesis_time',
    'Genesis time',
    namespace=PROMETHEUS_PREFIX,
)

SLOT_NUMBER = Gauge(
    "slot_number",
    "Watcher head slot number",
    namespace=PROMETHEUS_PREFIX,
)

KEYS_SOURCE_SLOT_NUMBER = Gauge(
    "keys_source_slot_number",
    "Keys source last updated slot number",
    namespace=PROMETHEUS_PREFIX,
)

VALIDATORS_INDEX_SLOT_NUMBER = Gauge(
    "validators_index_slot_number",
    "Validators index last updated slot number",
    namespace=PROMETHEUS_PREFIX,
)

EXECUTION_REQUESTS_SOURCE = Counter(
    "execution_requests_source",
    "Where the execution requests applied at a handled block were taken from",
    ['source'],
    namespace=PROMETHEUS_PREFIX,
)
