from prometheus_client import Gauge

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

KEYS_API_SLOT_NUMBER = Gauge(
    "keys_api_slot_number",
    "Keys API last updated slot number",
    namespace=PROMETHEUS_PREFIX,
)

VALIDATORS_INDEX_SLOT_NUMBER = Gauge(
    "validators_index_slot_number",
    "Validators index last updated slot number",
    namespace=PROMETHEUS_PREFIX,
)
