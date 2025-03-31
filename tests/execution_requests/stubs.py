from dataclasses import dataclass

from src.keys_source.base_source import NamedKey
from src.providers.alertmanager.typings import AlertBody
from tests.execution_requests.helpers import gen_random_address, gen_random_pubkey


@dataclass
class TestValidator:
    __test__ = False
    pubkey: str
    withdrawal_address: str

    @staticmethod
    def random():
        return TestValidator(pubkey=gen_random_pubkey(), withdrawal_address=gen_random_address())


class AlertmanagerStub:
    sent_alerts: list[AlertBody]

    def __init__(self):
        self.sent_alerts = []

    def send_alerts(self, alerts: list[AlertBody]):
        self.sent_alerts.extend(alerts)


class WatcherStub:
    alertmanager: AlertmanagerStub
    user_keys: dict[str, NamedKey]
    indexed_validators_keys: dict[str, str]
    valid_withdrawal_addresses: set[str]

    def __init__(
        self,
        user_keys: dict[str, NamedKey] = None,
        indexed_validators_keys: dict[str, str] = None,
        valid_withdrawal_addresses: set[str] = None,
    ):
        self.alertmanager = AlertmanagerStub()
        self.user_keys = user_keys or {}
        self.indexed_validators_keys = indexed_validators_keys or {}
        self.valid_withdrawal_addresses = valid_withdrawal_addresses or set()
