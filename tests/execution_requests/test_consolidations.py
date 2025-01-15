from src.handlers.consolidation import ConsolidationHandler
from src.providers.consensus.typings import ConsolidationRequest
from tests.execution_requests.helpers import gen_random_pubkey, create_sample_block, gen_random_address

from tests.execution_requests.stubs import TestValidator, WatcherStub


def test_source_is_valid_withdrawal_address(withdrawal_address: str, watcher: WatcherStub):
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

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
    assert alert.labels.severity == 'critical'
    assert alert.annotations.summary == "‼️⛔️Validator consolidation was requested from Withdrawal Vault source address"
    assert random_source_pubkey in alert.annotations.description
    assert random_target_pubkey in alert.annotations.description
    assert withdrawal_address in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_consolidate_user_validator(user_validator: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator.pubkey,
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
    assert alert.annotations.summary == "⚠️Consolidation was requested for our validators"
    assert random_source_address in alert.annotations.description
    assert random_target_pubkey in alert.annotations.description
    assert user_validator.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_donation(user_validator: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_source_pubkey = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=user_validator.pubkey,
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
    assert alert.annotations.summary == "⚠️Someone attempts to consolidate their validators to our validators"
    assert random_source_address in alert.annotations.description
    assert random_source_pubkey in alert.annotations.description
    assert user_validator.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_absence_of_alerts_on_foreign_validators(watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()
    random_source_pubkey = gen_random_pubkey()

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


def test_group_similar_alerts(user_validator: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey1 = gen_random_pubkey()
    random_target_pubkey2 = gen_random_pubkey()

    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator.pubkey,
                target_pubkey=random_target_pubkey1,
            ),
            ConsolidationRequest(
                source_address=random_source_address,
                source_pubkey=user_validator.pubkey,
                target_pubkey=random_target_pubkey2,
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
    assert alert.annotations.summary == "⚠️Consolidation was requested for our validators"
    assert random_source_address in alert.annotations.description
    assert random_target_pubkey1 in alert.annotations.description
    assert random_target_pubkey2 in alert.annotations.description
    assert user_validator.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description
