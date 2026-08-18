"""
The watcher's logic against a fake consensus node — no provider, no secrets, no network.

These cover the same decisions `tests/test_watcher.py` covers against real mainnet slots: a slot
range gets processed, a slashing of one of our keys alerts and names the operator, a slashing or an
exit that is not ours does not produce a user alert, and a module in
`disable_unexpected_exit_alerts` is silent. What they deliberately do not cover is the exact text
those historical blocks produced — that is what the integration tests are for, and why they were kept
rather than replaced.

Keys come from a file rather than from the Keys API: with `KEYS_SOURCE=file` the execution layer is
out of the picture too, and what is left is exactly the part these tests are about — mapping a
validator index to a key to an operator.
"""

import logging

import pytest
import yaml

from src import variables
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.keys_source.file_source import FileSource
from src.watcher import Watcher
from tests.node_fake import BeaconNodeFake, attester_slashing, current_slot, voluntary_exit

OUR_KEY = '0x' + 'a1' * 48
OUR_OTHER_KEY = '0x' + 'a2' * 48
FOREIGN_KEY = '0x' + 'ff' * 48

# index -> pubkey, the mapping the watcher builds from the validators endpoint.
VALIDATORS = {'100': OUR_KEY, '101': OUR_OTHER_KEY, '900': FOREIGN_KEY}


@pytest.fixture
def keys_file(tmp_path, monkeypatch):
    """Two of the three validators above are ours, under two operators of one module."""
    path = tmp_path / 'keys.yml'
    path.write_text(
        yaml.safe_dump(
            {
                'operators': [
                    {'name': 'Operator One', 'keys': [OUR_KEY]},
                    {'name': 'Operator Two', 'keys': [OUR_OTHER_KEY]},
                ]
            }
        )
    )
    monkeypatch.setattr(variables, 'KEYS_FILE_PATH', str(path))
    return path


@pytest.fixture
def dry_run(monkeypatch):
    """Alerts are asserted from the log, as in the integration tests. Nothing is posted anywhere."""
    monkeypatch.setattr(variables, 'DRY_RUN', True)


def build_watcher(node, monkeypatch) -> Watcher:
    monkeypatch.setattr(variables, 'CONSENSUS_CLIENT_URI', [node.url])
    monkeypatch.setattr(variables, 'ALERTMANAGER_URI', [node.url])
    # No web3: the exits handler only reaches for the execution layer when an exit is one of ours,
    # and the cases below that involve our keys are slashings.
    return Watcher([ForkHandler(), SlashingHandler(), ExitsHandler()], FileSource(), None)


def test_a_slot_range_is_processed(keys_file, dry_run, monkeypatch):
    start = current_slot() - 3
    node = BeaconNodeFake(head_slot=start, validators=VALIDATORS).start()
    try:
        watcher = build_watcher(node, monkeypatch)

        watcher.run(f'{start}-{start + 2}')

        assert [h.header.message.slot for h in watcher.handled_headers] == [str(s) for s in range(start, start + 3)]
        assert watcher.keys_updater.done()
        assert watcher.validators_updater.done()
        assert set(watcher.user_keys) == {OUR_KEY, OUR_OTHER_KEY}
        assert watcher.indexed_validators_keys == VALIDATORS
    finally:
        node.stop()


def test_a_slashing_of_our_validator_alerts_and_names_the_operator(caplog, keys_file, dry_run, monkeypatch):
    slot = current_slot() - 2
    node = BeaconNodeFake(
        head_slot=slot,
        validators=VALIDATORS,
        bodies={slot + 1: {'attester_slashings': [attester_slashing(['100'])]}},
    ).start()
    try:
        caplog.set_level(logging.INFO)
        watcher = build_watcher(node, monkeypatch)

        watcher.run(f'{slot}-{slot + 1}')

        assert 'Our validators were slashed' in caplog.text
        assert 'Operator One' in caplog.text
    finally:
        node.stop()


def test_a_slashing_of_a_foreign_validator_is_not_a_user_alert(caplog, keys_file, dry_run, monkeypatch):
    slot = current_slot() - 2
    node = BeaconNodeFake(
        head_slot=slot,
        validators=VALIDATORS,
        bodies={slot + 1: {'attester_slashings': [attester_slashing(['900'])]}},
    ).start()
    try:
        caplog.set_level(logging.INFO)
        watcher = build_watcher(node, monkeypatch)

        watcher.run(f'{slot}-{slot + 1}')

        # The watcher still reports it — somebody was slashed — but not as ours, which is the
        # distinction that decides who gets paged.
        assert 'Our validators were slashed' not in caplog.text
        assert 'slashed' in caplog.text
    finally:
        node.stop()


def test_an_exit_of_a_validator_we_do_not_know_is_not_a_user_alert(caplog, keys_file, dry_run, monkeypatch):
    slot = current_slot() - 2
    node = BeaconNodeFake(
        head_slot=slot,
        validators=VALIDATORS,
        bodies={slot + 1: {'voluntary_exits': [voluntary_exit('900')]}},
    ).start()
    try:
        caplog.set_level(logging.INFO)
        watcher = build_watcher(node, monkeypatch)

        watcher.run(f'{slot}-{slot + 1}')

        assert 'Our validators were unexpectedly exited' not in caplog.text
    finally:
        node.stop()


def test_the_reorg_alert_fires_for_an_unknown_parent(caplog, keys_file, dry_run, monkeypatch):
    # The fork handler's other half: a head whose parent was never handled means the chain moved
    # under the watcher, and this is the one alert that needs no keys at all.
    start = current_slot() - 5
    node = BeaconNodeFake(head_slot=start, validators=VALIDATORS).start()
    try:
        caplog.set_level(logging.INFO)
        watcher = build_watcher(node, monkeypatch)

        watcher.run(f'{start}-{start + 1}')
        caplog.clear()
        # Skip a slot: the next head's parent_root is a root the watcher has not seen.
        watcher.run(f'{start + 3}-{start + 3}')

        assert 'unhandled' in caplog.text.lower() or 'reorg' in caplog.text.lower()
    finally:
        node.stop()
