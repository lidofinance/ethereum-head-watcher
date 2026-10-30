import signal
from dataclasses import MISSING, fields

import pytest

from src.alerts.common import CommonAlert
from src.handlers.consolidation import ConsolidationHandler
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.main import build_handlers, install_signal_handlers
from src.providers.alertmanager.typings import Labels
from src.variables import (
    SUPPORTED_ALERTMANAGER_LABELS,
    parse_additional_alertmanager_labels,
    parse_enabled_handlers,
    parse_slots_range,
)


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (None, None),
        ('fork', ['fork']),
        (' slashing, exits ', ['slashing', 'exits']),
    ],
)
def test_parse_enabled_handlers(value, expected):
    assert parse_enabled_handlers(value) == expected


@pytest.mark.parametrize('value', ['', '  ', ',', ', ,'])
def test_parse_enabled_handlers_rejects_lists_without_names(value):
    with pytest.raises(ValueError, match='ENABLED_HANDLERS must contain at least one handler name'):
        parse_enabled_handlers(value)


@pytest.mark.parametrize('value', [None, '', '   '])
def test_slots_range_is_none_when_nothing_is_configured(value):
    assert parse_slots_range(value) is None


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('100-200', '100-200'),
        ('5-5', '5-5'),
        (' 100 - 200 ', '100-200'),
        ('0007-0008', '7-8'),
    ],
)
def test_slots_range_is_parsed(value, expected):
    assert parse_slots_range(value) == expected


@pytest.mark.parametrize('value', ['100', 'abc', '100-', '-200', '100-200-300', '-', '1.5-2'])
def test_slots_range_rejects_malformed_values(value):
    with pytest.raises(ValueError, match='SLOTS_RANGE must look like'):
        parse_slots_range(value)


def test_slots_range_rejects_an_inverted_range():
    with pytest.raises(ValueError, match='SLOTS_RANGE must start before it ends'):
        parse_slots_range('200-100')


@pytest.mark.parametrize('value', [None, '', '   ', '{}'])
def test_additional_labels_are_empty_when_nothing_is_configured(value):
    assert parse_additional_alertmanager_labels(value) == {}


def test_additional_labels_are_parsed():
    assert parse_additional_alertmanager_labels('{"mentions":"@here"}') == {'mentions': '@here'}


@pytest.mark.parametrize('value', ['{', 'not json', '{"mentions":}'])
def test_additional_labels_reject_malformed_json(value):
    with pytest.raises(ValueError, match='ADDITIONAL_ALERTMANAGER_LABELS must be a JSON object'):
        parse_additional_alertmanager_labels(value)


@pytest.mark.parametrize('value', ['[]', '"mentions"', '7'])
def test_additional_labels_reject_json_that_is_not_an_object(value):
    with pytest.raises(ValueError, match='must be a JSON object, got'):
        parse_additional_alertmanager_labels(value)


def test_additional_labels_reject_unsupported_keys():
    with pytest.raises(ValueError, match='Unsupported labels in ADDITIONAL_ALERTMANAGER_LABELS: a, b'):
        parse_additional_alertmanager_labels('{"b":"1","a":"2","mentions":"@here"}')


def test_supported_labels_match_the_alert_body():
    """Pins the hardcoded set to the dataclass it stands for, so the two can not drift apart"""
    # `alertname` and `severity` are the required ones, filled in by the code itself
    settable_by_config = {field.name for field in fields(Labels) if field.default is not MISSING}

    assert SUPPORTED_ALERTMANAGER_LABELS == settable_by_config


def test_every_supported_label_is_accepted_by_the_alert_body():
    labels = {name: 'x' for name in SUPPORTED_ALERTMANAGER_LABELS}

    body = CommonAlert(name='Test', severity='critical').build_body('summary', 'description', labels)

    for name, value in labels.items():
        assert getattr(body.labels, name) == value


def test_build_handlers_defaults_to_all_handlers():
    handlers = build_handlers()

    assert [type(handler) for handler in handlers] == [
        ForkHandler,
        SlashingHandler,
        ExitsHandler,
        ConsolidationHandler,
        ElTriggeredExitHandler,
    ]


def test_build_handlers_uses_selected_handlers_and_mandatory_fork_handler():
    handlers = build_handlers(['exits'])

    assert [type(handler) for handler in handlers] == [ForkHandler, ExitsHandler]


def test_build_handlers_rejects_empty_handler_list():
    with pytest.raises(ValueError, match='ENABLED_HANDLERS must contain at least one handler name'):
        build_handlers([])


def test_build_handlers_rejects_unknown_handler():
    with pytest.raises(ValueError, match='Unknown handlers in ENABLED_HANDLERS: finality'):
        build_handlers(['finality'])


def test_build_handlers_rejects_configuring_mandatory_fork_handler():
    with pytest.raises(ValueError, match='Unknown handlers in ENABLED_HANDLERS: fork'):
        build_handlers(['fork'])


def test_build_handlers_rejects_duplicate_handler():
    with pytest.raises(ValueError, match='Duplicate handlers in ENABLED_HANDLERS: exits'):
        build_handlers(['exits', 'exits'])


def test_install_signal_handlers_routes_termination_onto_the_sigint_path():
    """Without a handler the signal is dropped, and the container is killed instead of stopping."""
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGHUP)}
    try:
        install_signal_handlers()
        for sig in (signal.SIGTERM, signal.SIGHUP):
            assert signal.getsignal(sig) is signal.default_int_handler
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def test_default_int_handler_raises_keyboard_interrupt():
    """Why the loop needs no stop flag: `except Exception` does not catch KeyboardInterrupt."""
    with pytest.raises(KeyboardInterrupt):
        signal.default_int_handler(signal.SIGTERM, None)
