from src.handlers.consolidation import ConsolidationHandler
from src.providers.consensus.typings import ConsolidationRequest
from tests.execution_requests.helpers import gen_random_pubkey, create_sample_block, gen_random_address
from tests.execution_requests.stubs import TestValidator, WatcherStub


def test_consolidation_foreign_source_and_target_pubkey_from_user_withdrawal_address(
    withdrawal_address: str, watcher: WatcherStub
):
    random_source_pubkey = gen_random_pubkey()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=random_target_pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    general_user_withdrawal_address_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert general_user_withdrawal_address_alert is not None

    assert general_user_withdrawal_address_alert.labels.severity == 'critical'
    assert (
        general_user_withdrawal_address_alert.annotations.summary
        == "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault source address"
    )
    assert withdrawal_address in general_user_withdrawal_address_alert.annotations.description
    assert random_source_pubkey in general_user_withdrawal_address_alert.annotations.description
    assert random_target_pubkey in general_user_withdrawal_address_alert.annotations.description
    assert block.message.slot in general_user_withdrawal_address_alert.annotations.description

    foreign_source_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignSourcePubkey')
        ),
        None,
    )
    assert foreign_source_alert is not None

    foreign_target_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignTargetPubkey')
        ),
        None,
    )
    assert foreign_target_alert is not None


def test_consolidation_foreign_source_pubkey_from_user_withdrawal_address(
    withdrawal_address: str, user_validator_2: TestValidator, watcher: WatcherStub
):
    random_source_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 2

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    foreign_source_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignSourcePubkey')
        ),
        None,
    )
    assert foreign_source_alert is not None
    assert foreign_source_alert.labels.severity == 'critical'
    assert (
        foreign_source_alert.annotations.summary
        == "🚨🚨🚨 Validator consolidation was requested for foreign source validator from Withdrawal Vault address"
    )
    assert withdrawal_address in foreign_source_alert.annotations.description
    assert random_source_pubkey in foreign_source_alert.annotations.description
    assert user_validator_2.pubkey in foreign_source_alert.annotations.description
    assert block.message.slot in foreign_source_alert.annotations.description


def test_consolidation_foreign_target_pubkey_from_user_withdrawal_address(
    withdrawal_address: str, user_validator_1: TestValidator, watcher: WatcherStub
):
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=random_target_pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 2

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    foreign_target_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignTargetPubkey')
        ),
        None,
    )
    assert foreign_target_alert is not None
    assert foreign_target_alert.labels.severity == 'critical'
    assert (
        foreign_target_alert.annotations.summary
        == "🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault address to foreign target validator"
    )
    assert withdrawal_address in foreign_target_alert.annotations.description
    assert user_validator_1.pubkey in foreign_target_alert.annotations.description
    assert random_target_pubkey in foreign_target_alert.annotations.description
    assert block.message.slot in foreign_target_alert.annotations.description


def test_consolidation_foreign_withdrawal_address_user_source_pubkey(
    user_validator_1: TestValidator, watcher: WatcherStub
):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=random_target_pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationUserSourcePubkey')
    assert alert.labels.severity == 'info'
    assert (
        alert.annotations.summary
        == "⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)"
    )
    assert random_source_address in alert.annotations.description
    assert user_validator_1.pubkey in alert.annotations.description
    assert random_target_pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_consolidation_foreign_withdrawal_address_user_target_pubkey(
    user_validator_2: TestValidator, watcher: WatcherStub
):
    random_source_address = gen_random_address()
    random_source_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationUserTargetPubkey')
    assert alert.labels.severity == 'info'
    assert (
        alert.annotations.summary
        == "⚠️⚠️⚠️ Someone attempts to consolidate their validators to our validators (not from Withdrawal Vault address)"
    )
    assert random_source_address in alert.annotations.description
    assert random_source_pubkey in alert.annotations.description
    assert user_validator_2.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_absence_of_alerts_on_foreign_validators(watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_source_pubkey = gen_random_pubkey()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=random_target_pubkey,
            )
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_group_similar_alerts(user_validator_1: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey_1 = gen_random_pubkey()
    random_target_pubkey_2 = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=random_target_pubkey_1,
            ),
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=random_target_pubkey_2,
            ),
        ]
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationUserSourcePubkey')
    assert alert.labels.severity == 'info'
    assert (
        alert.annotations.summary
        == "⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)"
    )
    assert random_source_address in alert.annotations.description
    assert user_validator_1.pubkey in alert.annotations.description
    assert random_target_pubkey_1 in alert.annotations.description
    assert random_target_pubkey_2 in alert.annotations.description
    assert block.message.slot in alert.annotations.description
