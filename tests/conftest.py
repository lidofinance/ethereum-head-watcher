import pytest

from src import variables
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler


@pytest.fixture
def mock_slot_range(monkeypatch):
    monkeypatch.setattr(variables, "SLOTS_RANGE", "6213851-6213858")


@pytest.fixture
def watcher(mock_slot_range, caplog):
    from src.watcher import Watcher  # pylint: disable=import-outside-toplevel

    with caplog.at_level("INFO"):
        yield Watcher([SlashingHandler(), ForkHandler()])
