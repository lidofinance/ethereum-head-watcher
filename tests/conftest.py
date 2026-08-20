import os

import pytest

from src import variables
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.keys_source.keys_api_source import KeysApiSource
from src.watcher import Watcher
from src.web3py.extensions import FallbackProviderModule, LidoContracts
from src.web3py.typings import Web3


# The default EL timeout is tuned for head processing. Replaying historical ranges means
# eth_getLogs over thousands of blocks, which a provider can take much longer to answer.
REPLAY_EL_REQUEST_TIMEOUT = float(os.getenv('REPLAY_EL_REQUEST_TIMEOUT', 60))


@pytest.fixture
def watcher(request, monkeypatch):
    web3 = Web3(
        FallbackProviderModule(variables.EXECUTION_CLIENT_URI, request_kwargs={'timeout': REPLAY_EL_REQUEST_TIMEOUT})
    )
    web3.attach_modules(
        {
            'lido_contracts': LidoContracts,
        }
    )

    return Watcher([SlashingHandler(), ForkHandler(), ExitsHandler()], KeysApiSource(), web3)
