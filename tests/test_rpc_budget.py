"""
What a day of following the head costs the consensus-layer provider.

The shape is borrowed from keys-api-versioned's rpc_quota_test.go, and so is the reason for it: a
provider limit is a property of the deployment, and the only version of that number worth trusting
is one measured from the code rather than remembered. A new call added anywhere under a cycle shows
up here on its own.

One honest difference from the Go original: it converts requests into the provider's compute units,
because dRPC documents CU weights for the JSON-RPC methods the indexer uses. **No published CU
weights exist for the beacon API**, and the consensus layer is where essentially all of this
application's spend is — its execution-layer traffic is a handful of calls at startup and then
nothing until a user exit. So this asserts the request profile and projects requests per day, and
the CU translation stays an open question to be closed with the provider's own dashboard. Until it
is, the projection here is compared against a ceiling we set ourselves: not a provider limit, a
no-regression line.
"""

import pytest

from src import variables
from src.handlers.fork import ForkHandler
from src.keys_source.file_source import FileSource
from src.watcher import Watcher
from tests.node_fake import BeaconNodeFake

# The deployment being checked. Change these together with the values file — that is the point of
# them being here.
#
# cycleSleep must match CYCLE_SLEEP_IN_SECONDS in helm-charts-vroom/vroom-head-watcher/
# values-k8s-dev.yaml (unset there, so the application default applies).
CYCLE_SLEEP_IN_SECONDS = 1
SLOT_TIME_IN_SECONDS = 12
EPOCH_TIME_IN_SECONDS = 384  # 12 s × 32 slots

# Not a provider limit — a line drawn where today's behaviour sits, so that a change in the polling
# shape has to be argued for rather than merged. Today: one header read per cycle (86 400/day), one
# block read per slot (7 200/day), one validators stream per epoch (225/day).
MAX_CL_REQUESTS_PER_DAY = 95_000


@pytest.fixture
def node():
    fake = BeaconNodeFake(validators={'1': '0x' + 'aa' * 48}).start()
    yield fake
    fake.stop()


@pytest.fixture
def watcher(node, monkeypatch):
    """
    A watcher wired to the fake, with keys read from a file.

    KEYS_SOURCE=file on purpose: it removes the Keys API and the execution layer from the picture,
    which is what leaves the consensus-layer profile visible. Their cost is separate and, in the
    steady state, close to zero — the execution layer is only touched at startup and when a user
    exit appears in a block.
    """
    monkeypatch.setattr(variables, 'CONSENSUS_CLIENT_URI', [node.url])
    monkeypatch.setattr(variables, 'KEYS_FILE_PATH', 'docker/validators/keys.yml')
    return Watcher([ForkHandler()], FileSource(), None)


def profile(node, watcher, slots_advanced: int) -> dict:
    """Requests made by one cycle, with the head advanced by `slots_advanced` slots first."""
    node.head_slot += slots_advanced
    node.reset_counts()
    watcher.run_cycle()
    if watcher.keys_updater is not None:
        watcher.keys_updater.result()
    if watcher.validators_updater is not None:
        watcher.validators_updater.result()
    return dict(node.requests)


def test_a_cycle_that_sees_no_new_head_reads_only_the_header(node, watcher):
    profile(node, watcher, slots_advanced=1)  # warm up: the first cycle has no previous head

    idle = profile(node, watcher, slots_advanced=0)

    # The short-circuit the whole budget rests on: an unchanged head costs one request, not two.
    # It is also only half a short-circuit — the header itself is read every cycle, so at a 1 s
    # interval that is twelve reads per slot of which eleven see nothing.
    assert idle == {'headers/{slot}': 1}


def test_a_cycle_that_sees_a_new_head_reads_the_block_too(node, watcher):
    profile(node, watcher, slots_advanced=1)

    moved = profile(node, watcher, slots_advanced=1)

    assert moved == {'headers/{slot}': 1, 'blocks/{root}': 1}


def test_the_validator_set_is_read_once_an_epoch(node, watcher):
    # First cycle of all: the set is empty, so it is read regardless of where in the epoch we are.
    first = profile(node, watcher, slots_advanced=1)
    assert first.get('states/{state}/validators') == 1

    within_epoch = profile(node, watcher, slots_advanced=1)

    assert 'states/{state}/validators' not in within_epoch


def test_a_day_of_following_the_head_stays_under_the_ceiling(node, watcher):
    profile(node, watcher, slots_advanced=1)
    idle = profile(node, watcher, slots_advanced=0)
    moved = profile(node, watcher, slots_advanced=1)

    cycles_per_day = 24 * 60 * 60 // CYCLE_SLEEP_IN_SECONDS
    blocks_per_day = 24 * 60 * 60 // SLOT_TIME_IN_SECONDS
    epochs_per_day = 24 * 60 * 60 // EPOCH_TIME_IN_SECONDS

    # Below the slot time every block is still observed exactly once — whichever poll sees it
    # first — so the expensive cycles are a function of the chain and only the empty polls scale
    # with the interval.
    moved_cycles = min(blocks_per_day, cycles_per_day)
    idle_cycles = cycles_per_day - moved_cycles

    per_day: dict[str, int] = {}
    for endpoint, count in moved.items():
        per_day[endpoint] = per_day.get(endpoint, 0) + count * moved_cycles
    for endpoint, count in idle.items():
        per_day[endpoint] = per_day.get(endpoint, 0) + count * idle_cycles
    # The validator set is epoch-paced, and neither sampled cycle lands on an epoch boundary.
    per_day['states/{state}/validators'] = epochs_per_day

    total = sum(per_day.values())
    breakdown = '\n'.join(f'  {endpoint:26} {count:>8}/day' for endpoint, count in sorted(per_day.items()))

    assert total <= MAX_CL_REQUESTS_PER_DAY, (
        f'a day of following the head no longer fits the ceiling.\n\n'
        f'  projected  {total} requests/day at a {CYCLE_SLEEP_IN_SECONDS}s interval\n'
        f'  ceiling    {MAX_CL_REQUESTS_PER_DAY} requests/day\n\n'
        f'{breakdown}\n\n'
        'Either a call was added under the cycle, or the polling interval changed. Raising the\n'
        'ceiling is a decision about provider spend and about how fast a slashing is noticed —\n'
        'the interval is the latency of the whole detector, not only its price. Take the real\n'
        'numbers from the provider dashboard before moving this line.'
    )
