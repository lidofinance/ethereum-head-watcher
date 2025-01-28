from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.keys_source.base_source import NamedKey
from src.providers.consensus.typings import WithdrawalRequest
from tests.execution_requests.helpers import create_sample_block, gen_random_address
from tests.execution_requests.stubs import WatcherStub, TestValidator


def test_user_validator(user_validator: TestValidator, watcher: WatcherStub):
    random_address = gen_random_address()
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=random_address, validator_pubkey=user_validator.pubkey, amount='32')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherUserELWithdrawal')
    assert alert.labels.severity == 'info'
    assert alert.annotations.summary == "⚠️⚠️⚠️ Our validator triggered withdrawal was requested"
    assert user_validator.pubkey in alert.annotations.description
    assert random_address in alert.annotations.description
    assert '32' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_absence_of_alerts_for_foreign_validator(validator: TestValidator, watcher: WatcherStub):
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=gen_random_address(), validator_pubkey=validator.pubkey, amount='32')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_from_user_withdrawal_address(validator: TestValidator, withdrawal_address: str, watcher: WatcherStub):
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=withdrawal_address, validator_pubkey=validator.pubkey, amount='32')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherELWithdrawalFromUserWithdrawalAddress')
    assert alert.labels.severity == 'critical'
    assert (
        alert.annotations.summary
        == "🚨🚨🚨 Our validator triggered withdrawal was requested from our Withdrawal Vault address"
    )
    assert validator.pubkey in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert '32' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_works_on_dencun(watcher: WatcherStub):
    handler = ElTriggeredExitHandler()
    block = create_sample_block()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_absense_of_alerts_for_foreign_validator():
    validator_pubkey = (
        '0x84a687ffdf21a0ad754d0164d1e2c03035613ab76359e7f5cf51ea4a425a6ee026725ec0a0dbd336f7dab759596f0bf8'
    )
    amount = "32"
    watcher = WatcherStub(
        user_keys={
            validator_pubkey: NamedKey(
                key=validator_pubkey, operatorName='Test operator', operatorIndex='1', moduleIndex='1'
            )
        }
    )
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(
                source_address='0x0048281f02e108ec495e48a25d2adb4732df75bf5750c060ff31c864c053d28d',
                validator_pubkey='0xaaf6c1251e73fb600624937760fef218aace5b253bf068ed45398aeb29d821e4d2899343ddcbbe37cb3f6cf500dff26c',
                amount=amount,
            )
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_group_similar_alerts():
    validator1 = TestValidator.random()
    validator2 = TestValidator.random()
    withdrawal_address = gen_random_address()

    watcher = WatcherStub(
        user_keys={
            validator1.pubkey: NamedKey(
                operatorName='test operator', key=validator1.pubkey, operatorIndex='1', moduleIndex='1'
            )
        },
        valid_withdrawal_addresses={withdrawal_address},
    )
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(
                source_address=withdrawal_address,
                validator_pubkey=validator1.pubkey,
                amount='32',
            ),
            WithdrawalRequest(
                source_address=withdrawal_address,
                validator_pubkey=validator2.pubkey,
                amount='32',
            ),
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherELWithdrawalFromUserWithdrawalAddress')
    assert alert.labels.severity == 'critical'
    assert (
        alert.annotations.summary
        == "🚨🚨🚨 Our validator triggered withdrawal was requested from our Withdrawal Vault address"
    )
    assert validator1.pubkey in alert.annotations.description
    assert validator2.pubkey in alert.annotations.description
    assert 'test operator' in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert '32' in alert.annotations.description
    assert block.message.slot in alert.annotations.description
