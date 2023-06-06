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

BLOCK_NUMBER = Gauge(
    "block_number",
    "Watcher head block number",
    namespace=PROMETHEUS_PREFIX,
)

KEYS_API_BLOCK_NUMBER = Gauge(
    "keys_api_block_number",
    "Keys API block number from status",
    namespace=PROMETHEUS_PREFIX,
)

VALIDATORS_INDEX_SLOT_NUMBER = Gauge(
    "validators_index_slot_number",
    "Validators index last updated slot number",
    namespace=PROMETHEUS_PREFIX,
)
