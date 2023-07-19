import pytest

from src import variables
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.web3py.extensions import FallbackProviderModule, LidoContracts
from src.web3py.typings import Web3


@pytest.fixture
def slot_range_param():
    return "6213851-6213858"


@pytest.fixture
def mock_slot_range(monkeypatch, slot_range_param):
    monkeypatch.setattr(variables, "SLOTS_RANGE", slot_range_param)


@pytest.fixture
def watcher(mock_slot_range, caplog):
    from src.watcher import Watcher  # pylint: disable=import-outside-toplevel

    web3 = Web3(
        FallbackProviderModule(variables.EXECUTION_CLIENT_URI, request_kwargs={'timeout': variables.EL_REQUEST_TIMEOUT})
    )
    web3.attach_modules(
        {
            'lido_contracts': LidoContracts,
        }
    )
    with caplog.at_level("INFO"):
        yield Watcher([SlashingHandler(), ForkHandler(), ExitsHandler()], web3)
