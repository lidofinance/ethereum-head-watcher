from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.keys_source.base_source import NamedKey
from src.providers.consensus.typings import WithdrawalRequest
from tests.execution_requests.helpers import create_sample_block, gen_random_address
from tests.execution_requests.stubs import WatcherStub, TestValidator


def test_user_validator_full_withdrawal_from_valid_source_triggers_info_alert(
    user_validator: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(
                source_address=withdrawal_address,
                validator_pubkey=user_validator.pubkey,
                amount='0',
            )
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherFullELWithdrawalObserved')
    assert alert.labels.severity == 'info'
    assert alert.annotations.summary == "⚠️ Full withdrawal (exit) requested for our validator(s)"
    assert user_validator.pubkey in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert '0' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_user_validator_full_withdrawal_unknown_source_triggers_alert(
    user_validator: TestValidator, watcher: WatcherStub
):
    random_address = gen_random_address()
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=random_address, validator_pubkey=user_validator.pubkey, amount='0')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherELRequestFromUnknownSourceForOurValidators')
    assert alert.labels.severity == 'info'
    assert (
        alert.annotations.summary == "⚠️ Withdrawal request from unknown source address for our validator(s) observed"
    )
    assert user_validator.pubkey in alert.annotations.description
    assert random_address in alert.annotations.description
    assert '0' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_user_validator_partial_withdrawal_from_valid_source(
    user_validator: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=withdrawal_address, validator_pubkey=user_validator.pubkey, amount='32')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherPartialELWithdrawalObserved')
    assert alert.labels.severity == 'critical'
    assert alert.annotations.summary == "🚨 Partial withdrawal observed for our validator(s) (unsupported)"
    assert user_validator.pubkey in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert '32' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_no_alerts_for_foreign_validator(validator: TestValidator, watcher: WatcherStub):
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=gen_random_address(), validator_pubkey=validator.pubkey, amount='32')
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_from_user_withdrawal_address_for_foreign_validator_triggers_alert(
    validator: TestValidator, withdrawal_address: str, watcher: WatcherStub
):
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
    assert alert.labels.alertname.startswith('HeadWatcherELRequestFromOurSourceForForeignValidators')
    assert alert.labels.severity == 'critical'
    assert (
        alert.annotations.summary == "🚨️ Withdrawal request from our source address for non-user validator(s) observed"
    )
    assert validator.pubkey in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert '32' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_no_withdrawals_produce_no_alerts(watcher: WatcherStub):
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


def test_group_similar_partial_withdrawal_alerts():
    validator1 = TestValidator.random()
    validator2 = TestValidator.random()

    addr1 = gen_random_address()
    addr2 = gen_random_address()

    watcher = WatcherStub(
        user_keys={
            validator1.pubkey: NamedKey(
                operatorName='test operator 1', key=validator1.pubkey, operatorIndex='1', moduleIndex='1'
            ),
            validator2.pubkey: NamedKey(
                operatorName='test operator 2', key=validator2.pubkey, operatorIndex='2', moduleIndex='1'
            ),
        },
        valid_withdrawal_addresses={addr1, addr2},
    )
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(
                source_address=addr1,
                validator_pubkey=validator1.pubkey,
                amount='10',
            ),
            WithdrawalRequest(
                source_address=addr2,
                validator_pubkey=validator2.pubkey,
                amount='20',
            ),
        ]
    )
    handler = ElTriggeredExitHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherPartialELWithdrawalObserved')
    assert alert.labels.severity == 'critical'
    assert alert.annotations.summary == "🚨 Partial withdrawal observed for our validator(s) (unsupported)"
    assert validator1.pubkey in alert.annotations.description
    assert validator2.pubkey in alert.annotations.description
    assert 'test operator 1' in alert.annotations.description
    assert 'test operator 2' in alert.annotations.description
    assert '10' in alert.annotations.description
    assert '20' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_multiple_full_withdrawals_grouped_into_one_alert(user_validator: TestValidator, watcher: WatcherStub):
    second_validator = TestValidator.random()
    addr = gen_random_address()
    watcher.user_keys[second_validator.pubkey] = NamedKey(
        key=second_validator.pubkey, operatorName='op2', operatorIndex='2', moduleIndex='1'
    )
    watcher.valid_withdrawal_addresses.add(addr)
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=addr, validator_pubkey=user_validator.pubkey, amount='0'),
            WithdrawalRequest(source_address=addr, validator_pubkey=second_validator.pubkey, amount='0'),
        ]
    )

    handler = ElTriggeredExitHandler()
    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherFullELWithdrawalObserved')
    assert alert.labels.severity == 'info'
    assert user_validator.pubkey in alert.annotations.description
    assert second_validator.pubkey in alert.annotations.description
    assert '0' in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_mixed_user_full_and_partial_generate_two_alerts(
    user_validator: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    second_validator = TestValidator.random()
    watcher.user_keys[second_validator.pubkey] = NamedKey(
        key=second_validator.pubkey, operatorName='op2', operatorIndex='2', moduleIndex='1'
    )
    watcher.valid_withdrawal_addresses.add(withdrawal_address)
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=withdrawal_address, validator_pubkey=user_validator.pubkey, amount='0'),
            WithdrawalRequest(source_address=withdrawal_address, validator_pubkey=second_validator.pubkey, amount='5'),
        ]
    )

    handler = ElTriggeredExitHandler()
    task = handler.handle(watcher, block)
    task.result()

    kinds = sorted(
        (a.labels.alertname, a.labels.severity, a.annotations.summary) for a in watcher.alertmanager.sent_alerts
    )
    assert len(kinds) == 2
    assert any(k[0].startswith('HeadWatcherFullELWithdrawalObserved') and k[1] == 'info' for k in kinds)
    assert any(k[0].startswith('HeadWatcherPartialELWithdrawalObserved') and k[1] == 'critical' for k in kinds)
    joined_desc = '\n'.join(a.annotations.description for a in watcher.alertmanager.sent_alerts)
    assert user_validator.pubkey in joined_desc
    assert second_validator.pubkey in joined_desc
    assert '0' in joined_desc
    assert '5' in joined_desc
    assert block.message.slot in joined_desc


def test_mixed_unknown_source_for_our_and_our_source_for_foreign_generate_two_alerts(
    user_validator: TestValidator, validator: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    unknown_addr = gen_random_address()
    watcher.valid_withdrawal_addresses.add(withdrawal_address)
    block = create_sample_block(
        withdrawals=[
            WithdrawalRequest(source_address=unknown_addr, validator_pubkey=user_validator.pubkey, amount='1'),
            WithdrawalRequest(source_address=withdrawal_address, validator_pubkey=validator.pubkey, amount='2'),
        ]
    )

    handler = ElTriggeredExitHandler()
    task = handler.handle(watcher, block)
    task.result()

    kinds = sorted(
        (a.labels.alertname, a.labels.severity, a.annotations.summary) for a in watcher.alertmanager.sent_alerts
    )
    assert len(kinds) == 2
    assert any(
        k[0].startswith('HeadWatcherELRequestFromUnknownSourceForOurValidators')
        and k[1] == 'info'
        and "unknown source address" in k[2]
        for k in kinds
    )
    assert any(
        k[0].startswith('HeadWatcherELRequestFromOurSourceForForeignValidators')
        and k[1] == 'critical'
        and "our source address" in k[2]
        for k in kinds
    )
    joined_desc = '\n'.join(a.annotations.description for a in watcher.alertmanager.sent_alerts)
    assert user_validator.pubkey in joined_desc
    assert validator.pubkey in joined_desc
    assert unknown_addr in joined_desc
    assert withdrawal_address in joined_desc
    assert '1' in joined_desc
    assert '2' in joined_desc
    assert block.message.slot in joined_desc
