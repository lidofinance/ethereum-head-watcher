import signal

import pytest

from src.handlers.consolidation import ConsolidationHandler
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.main import build_handlers, install_signal_handlers
from src.variables import parse_enabled_handlers


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
    """
    SIGTERM is what a pod termination is, and this process is PID 1 in its container -- with no
    handler installed the kernel applies no default action and the signal is dropped, which costs
    a SIGKILL after the grace period on every rollout.
    """
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGHUP)}
    try:
        install_signal_handlers()
        for sig in (signal.SIGTERM, signal.SIGHUP):
            assert signal.getsignal(sig) is signal.default_int_handler
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def test_default_int_handler_raises_keyboard_interrupt():
    """
    The reason the loop needs no stop flag: the cycle's `except Exception` does not catch
    KeyboardInterrupt, so it unwinds run() and main() logs the shutdown.
    """
    with pytest.raises(KeyboardInterrupt):
        signal.default_int_handler(signal.SIGTERM, None)
