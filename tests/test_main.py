import pytest

from src.handlers.consolidation import ConsolidationHandler
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.execution_requests import ExecutionRequestsHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.main import build_handlers
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
        ExecutionRequestsHandler,
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
