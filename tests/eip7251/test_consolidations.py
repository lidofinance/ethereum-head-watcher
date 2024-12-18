from src.handlers.consolidation import ConsolidationHandler
from src.providers.consensus.typings import ConsolidationRequest
from tests.eip7251.helpers import gen_random_pubkey, create_sample_block, gen_random_address

from tests.eip7251.stubs import TestValidator, WatcherStub


def test_source_address_is_lido_withdrawal_vault(lido_withdrawal_vault: str, watcher: WatcherStub):
    random_source_pubkey = gen_random_pubkey()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(consolidations=[
        ConsolidationRequest(
            source_address=lido_withdrawal_vault,
            source_pubkey=random_source_pubkey,
            target_pubkey=random_target_pubkey
        )
    ])
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationSuspiciousSourceAddress')
    assert alert.labels.severity == 'critical'
    assert alert.annotations.summary == "🔗🤗 Highly suspicious source address"
    assert random_source_pubkey in alert.annotations.description
    assert random_target_pubkey in alert.annotations.description
    assert lido_withdrawal_vault in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_consolidate_lido(lido_validator: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()

    block = create_sample_block(consolidations=[
        ConsolidationRequest(
            source_address=random_source_address,
            source_pubkey=lido_validator.pubkey,
            target_pubkey=random_target_pubkey
        )
    ])
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationSourceLido')
    assert alert.labels.severity == 'moderate'
    assert alert.annotations.summary == "🔗🤗 Attempt to consolidate Lido validator"
    assert random_source_address in alert.annotations.description
    assert random_target_pubkey in alert.annotations.description
    assert lido_validator.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_donation_to_lido(lido_validator: TestValidator, watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()
    random_source_pubkey = gen_random_pubkey()

    block = create_sample_block(consolidations=[
        ConsolidationRequest(
            source_address=random_source_address,
            source_pubkey=random_source_pubkey,
            target_pubkey=lido_validator.pubkey
        )
    ])
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherConsolidationPossibleDonation')
    assert alert.labels.severity == 'moderate'
    assert alert.annotations.summary == "🔗🤗 Someone wants to donate to Lido"
    assert random_source_address in alert.annotations.description
    assert random_source_pubkey in alert.annotations.description
    assert lido_validator.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_non_lido(watcher: WatcherStub):
    random_source_address = gen_random_address()
    random_target_pubkey = gen_random_pubkey()
    random_source_pubkey = gen_random_pubkey()

    block = create_sample_block(consolidations=[
        ConsolidationRequest(
            source_address=random_source_address,
            source_pubkey=random_source_pubkey,
            target_pubkey=random_target_pubkey
        )
    ])
    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0
