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

SLASHINGS = Gauge(
    "slashings",
    "Slashings by duty and validator owner",
    ["duty", "owner"],
    namespace=PROMETHEUS_PREFIX,
)
