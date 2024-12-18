import pytest

from src.keys_source.base_source import NamedKey
from tests.eip7251.helpers import gen_random_address
from tests.eip7251.stubs import TestValidator, WatcherStub


@pytest.fixture
def user_keys() -> dict[str, NamedKey]:
    return {}


@pytest.fixture
def validator():
    return TestValidator.random()


@pytest.fixture
def lido_validator(user_keys):
    random_validator = TestValidator.random()
    user_keys[random_validator.pubkey] = NamedKey(
        key=random_validator.pubkey,
        operatorName='Dimon operator',
        operatorIndex='1',
        moduleIndex='1'
    )
    return random_validator


@pytest.fixture
def watcher(user_keys) -> WatcherStub:
    return WatcherStub(
        user_keys=user_keys
    )


@pytest.fixture
def lido_withdrawal_vault(watcher: WatcherStub) -> str:
    address = gen_random_address()
    watcher.suspicious_addresses.add(address)
    return address
