# pylint: disable=too-many-lines
from unittest.mock import MagicMock

from src.handlers.consolidation import ConsolidationHandler
from src.providers.consensus.typings import (
    ConsolidationRequest,
    PendingConsolidation,
    Validator,
    ValidatorState,
    ValidatorStatus,
)
from tests.execution_requests.helpers import (
    GLOAS_HEAD_SLOT,
    GLOAS_PARENT_SLOT,
    gen_random_pubkey,
    create_gloas_head_with_parent_requests,
    create_sample_block,
    create_validator,
    gen_random_address,
    random_hex,
)
from tests.execution_requests.stubs import TestValidator, WatcherStub


def test_consolidation_foreign_source_and_target_pubkey_from_user_withdrawal_address(
    watcher: WatcherStub, withdrawal_address: str
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
        == "**🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault source address**"
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
    user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
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
        == "**🚨🚨🚨 Validator consolidation was requested for foreign source validator from Withdrawal Vault address**"
    )
    assert withdrawal_address in foreign_source_alert.annotations.description
    assert random_source_pubkey in foreign_source_alert.annotations.description
    assert user_validator_2.pubkey in foreign_source_alert.annotations.description
    assert block.message.slot in foreign_source_alert.annotations.description


def test_consolidation_foreign_target_pubkey_from_user_withdrawal_address(
    user_validator_1: TestValidator, watcher: WatcherStub, withdrawal_address: str
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
        == "**🚨🚨🚨 Validator consolidation was requested from Withdrawal Vault address to foreign target validator**"
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
        == "**⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)**"
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
        == "**⚠️⚠️⚠️ Someone attempts to consolidate their validators to our validators (not from Withdrawal Vault address)**"
    )
    assert random_source_address in alert.annotations.description
    assert random_source_pubkey in alert.annotations.description
    assert user_validator_2.pubkey in alert.annotations.description
    assert block.message.slot in alert.annotations.description


def test_gloas_alerts_are_built_from_the_requests_of_the_parent_payload(watcher: WatcherStub, withdrawal_address: str):
    """After Glamsterdam (EIP-7732) the same requests must produce the same alerts"""
    random_source_pubkey = gen_random_pubkey()
    random_target_pubkey = gen_random_pubkey()

    head = create_gloas_head_with_parent_requests(
        watcher,
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=random_source_pubkey,
                target_pubkey=random_target_pubkey,
            )
        ],
    )
    handler = ConsolidationHandler()

    task = handler.handle(watcher, head)
    task.result()

    alert_names = [alert.labels.alertname for alert in watcher.alertmanager.sent_alerts]
    assert any(name.startswith('HeadWatcherConsolidationSourceWithdrawalAddress') for name in alert_names)
    assert any(
        name.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignSourcePubkey') for name in alert_names
    )
    assert any(
        name.startswith('HeadWatcherConsolidationUserWithdrawalAddressForeignTargetPubkey') for name in alert_names
    )

    description = watcher.alertmanager.sent_alerts[0].annotations.description
    assert withdrawal_address in description
    assert random_source_pubkey in description
    assert random_target_pubkey in description
    # The request was published in the parent slot and applied at the head slot, both are shown
    assert f'Slot: [{GLOAS_PARENT_SLOT}]' in description
    assert f'applied at [{GLOAS_HEAD_SLOT}]' in description


def test_gloas_validator_state_is_read_at_the_state_the_requests_were_applied_to(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    """
    A consolidation moves its source to `active_exiting` and gets queued only when it is applied,
    which happens one block after it was published, so the state to ask is the one left behind by
    the head. Reading the state of the parent instead would report every accepted consolidation as
    invalid and rejected.
    """
    head = create_gloas_head_with_parent_requests(
        watcher,
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ],
    )

    watcher.consensus.get_validators = MagicMock(
        return_value=[
            create_validator('1', user_validator_1.pubkey, ValidatorStatus.ACTIVE_EXITING),
            create_validator('2', user_validator_2.pubkey, ValidatorStatus.ACTIVE_ONGOING),
        ]
    )
    watcher.consensus.get_pending_consolidations = MagicMock(
        return_value=[PendingConsolidation(source_index='1', target_index='2')]
    )

    handler = ConsolidationHandler()

    task = handler.handle(watcher, head)
    task.result()

    assert watcher.consensus.get_validators.call_args.args[0] == head.message.state_root
    assert watcher.consensus.get_pending_consolidations.call_args.args[0] == head.message.state_root

    alert_names = [alert.labels.alertname for alert in watcher.alertmanager.sent_alerts]
    assert not any(name.startswith('HeadWatcherConsolidationInvalidStatus') for name in alert_names)
    assert not any(name.startswith('HeadWatcherConsolidationCLRejected') for name in alert_names)


def test_gloas_vebo_lookup_uses_the_el_block_number_the_state_has(
    user_validator_1: TestValidator,
    user_validator_2: TestValidator,
    watcher: WatcherStub,
    withdrawal_address: str,
    monkeypatch,
):
    """The payload the state already has is named by the parent block hash of the bid of the head"""
    head = create_gloas_head_with_parent_requests(
        watcher,
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ],
    )

    watcher.consensus.get_validators = MagicMock(
        return_value=[
            create_validator('1', user_validator_1.pubkey, ValidatorStatus.ACTIVE_EXITING),
            create_validator('2', user_validator_2.pubkey, ValidatorStatus.ACTIVE_ONGOING),
        ]
    )
    watcher.consensus.get_pending_consolidations = MagicMock(
        return_value=[PendingConsolidation(source_index='1', target_index='2')]
    )
    watcher.execution = MagicMock()
    watcher.execution.eth.get_block = MagicMock(return_value=MagicMock(number=31))

    lookup = MagicMock(side_effect=lambda _watcher, _el_block_number, exits_info: exits_info)
    monkeypatch.setattr('src.handlers.consolidation.get_last_requested_validator_exit_indexes', lookup)

    handler = ConsolidationHandler()

    task = handler.handle(watcher, head)
    task.result()

    assert lookup.call_args.args[1] == 31
    assert (
        watcher.execution.eth.get_block.call_args.args[0]
        == head.message.body.signed_execution_payload_bid.message.parent_block_hash
    )


def test_gloas_not_revealed_parent_payload_produces_no_alerts(watcher: WatcherStub, withdrawal_address: str):
    """The head is built on the branch without the parent payload, so its requests were not applied"""
    head = create_gloas_head_with_parent_requests(
        watcher,
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=gen_random_pubkey(),
                target_pubkey=gen_random_pubkey(),
            )
        ],
    )
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)

    handler = ConsolidationHandler()

    task = handler.handle(watcher, head)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_gloas_alerts_survive_a_parent_block_that_can_not_be_read(watcher: WatcherStub, withdrawal_address: str):
    """The requests are in the head block itself, so a failed lookup of the parent costs the slot only"""
    head = create_gloas_head_with_parent_requests(
        watcher,
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=gen_random_pubkey(),
                target_pubkey=gen_random_pubkey(),
            )
        ],
    )
    watcher.consensus.get_block_details = MagicMock(side_effect=ConnectionError('boom'))

    handler = ConsolidationHandler()

    task = handler.handle(watcher, head)
    task.result()

    alert_names = [alert.labels.alertname for alert in watcher.alertmanager.sent_alerts]
    assert any(name.startswith('HeadWatcherConsolidationSourceWithdrawalAddress') for name in alert_names)


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


def test_over_deposit_consolidation(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='1024000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='1025000000001',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='1024000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='1024000000001',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])

    pending_consolidation = PendingConsolidation(
        source_index='1',
        target_index='2',
    )
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[pending_consolidation])

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

    over_deposit_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationOverDeposit')
        ),
        None,
    )
    assert over_deposit_consolidation_alert is not None
    assert over_deposit_consolidation_alert.labels.severity == 'critical'
    assert (
        over_deposit_consolidation_alert.annotations.summary
        == "**⚠️⚠️⚠️ Total balance of source and target validators during consolidation is greater than 2049 ETH**"
    )
    assert withdrawal_address in over_deposit_consolidation_alert.annotations.description
    assert source_validator.index in over_deposit_consolidation_alert.annotations.description
    assert user_validator_1.pubkey in over_deposit_consolidation_alert.annotations.description
    assert source_validator.balance in over_deposit_consolidation_alert.annotations.description
    assert target_validator.index in over_deposit_consolidation_alert.annotations.description
    assert user_validator_2.pubkey in over_deposit_consolidation_alert.annotations.description
    assert target_validator.balance in over_deposit_consolidation_alert.annotations.description
    assert block.message.slot in over_deposit_consolidation_alert.annotations.description

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is None


def test_invalid_source_consolidation_status(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000',
        withdrawable_epoch='2000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.PENDING_INITIALIZED,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    invalid_status_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationInvalidStatus')
        ),
        None,
    )
    assert invalid_status_alert is not None
    assert invalid_status_alert.labels.severity == 'critical'
    assert (
        invalid_status_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators in unexpected status (source must be active_exiting, target must be active_ongoing)**"
    )
    assert withdrawal_address in invalid_status_alert.annotations.description
    assert source_validator.index in invalid_status_alert.annotations.description
    assert user_validator_1.pubkey in invalid_status_alert.annotations.description
    assert source_validator.status in invalid_status_alert.annotations.description
    assert source_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert target_validator.index in invalid_status_alert.annotations.description
    assert user_validator_2.pubkey in invalid_status_alert.annotations.description
    assert target_validator.status in invalid_status_alert.annotations.description
    assert target_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert block.message.slot in invalid_status_alert.annotations.description

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is not None


def test_invalid_target_consolidation_status(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000',
        withdrawable_epoch='2000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    invalid_status_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationInvalidStatus')
        ),
        None,
    )
    assert invalid_status_alert is not None
    assert invalid_status_alert.labels.severity == 'critical'
    assert (
        invalid_status_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators in unexpected status (source must be active_exiting, target must be active_ongoing)**"
    )
    assert withdrawal_address in invalid_status_alert.annotations.description
    assert source_validator.index in invalid_status_alert.annotations.description
    assert user_validator_1.pubkey in invalid_status_alert.annotations.description
    assert source_validator.status in invalid_status_alert.annotations.description
    assert source_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert target_validator.index in invalid_status_alert.annotations.description
    assert user_validator_2.pubkey in invalid_status_alert.annotations.description
    assert target_validator.status in invalid_status_alert.annotations.description
    assert target_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert block.message.slot in invalid_status_alert.annotations.description

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is not None


def test_slashed_source_consolidation(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=True,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000',
        withdrawable_epoch='2000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_SLASHED,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    invalid_status_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationInvalidStatus')
        ),
        None,
    )
    assert invalid_status_alert is not None
    assert invalid_status_alert.labels.severity == 'critical'
    assert (
        invalid_status_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators in unexpected status (source must be active_exiting, target must be active_ongoing)**"
    )
    assert withdrawal_address in invalid_status_alert.annotations.description
    assert source_validator.index in invalid_status_alert.annotations.description
    assert user_validator_1.pubkey in invalid_status_alert.annotations.description
    assert source_validator.status in invalid_status_alert.annotations.description
    assert source_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert target_validator.index in invalid_status_alert.annotations.description
    assert user_validator_2.pubkey in invalid_status_alert.annotations.description
    assert target_validator.status in invalid_status_alert.annotations.description
    assert target_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert block.message.slot in invalid_status_alert.annotations.description

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is not None


def test_slashed_target_consolidation(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=True,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000',
        withdrawable_epoch='2000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_SLASHED,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    invalid_status_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationInvalidStatus')
        ),
        None,
    )
    assert invalid_status_alert is not None
    assert invalid_status_alert.labels.severity == 'critical'
    assert (
        invalid_status_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators in unexpected status (source must be active_exiting, target must be active_ongoing)**"
    )
    assert withdrawal_address in invalid_status_alert.annotations.description
    assert source_validator.index in invalid_status_alert.annotations.description
    assert user_validator_1.pubkey in invalid_status_alert.annotations.description
    assert source_validator.status in invalid_status_alert.annotations.description
    assert source_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert target_validator.index in invalid_status_alert.annotations.description
    assert user_validator_2.pubkey in invalid_status_alert.annotations.description
    assert target_validator.status in invalid_status_alert.annotations.description
    assert target_validator.validator.exit_epoch in invalid_status_alert.annotations.description
    assert block.message.slot in invalid_status_alert.annotations.description

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is not None


def test_rejected_consolidation(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000',
        withdrawable_epoch='2000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.PENDING_INITIALIZED,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) >= 3

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    invalid_status_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationInvalidStatus')
        ),
        None,
    )
    assert invalid_status_alert is not None

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is not None
    assert rejected_consolidation_alert.labels.severity == 'critical'
    assert rejected_consolidation_alert.annotations.summary == "**🚨🚨🚨 Validator consolidation was rejected on CL**"
    assert withdrawal_address in rejected_consolidation_alert.annotations.description
    assert user_validator_1.pubkey in rejected_consolidation_alert.annotations.description
    assert user_validator_2.pubkey in rejected_consolidation_alert.annotations.description
    assert block.message.slot in rejected_consolidation_alert.annotations.description


def test_no_rejected_consolidation_alert_for_accepted_consolidations(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])

    pending_consolidation = PendingConsolidation(
        source_index='1',
        target_index='2',
    )
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[pending_consolidation])

    handler = ConsolidationHandler()

    task = handler.handle(watcher, block)
    task.result()

    assert len(watcher.alertmanager.sent_alerts) == 1

    user_wa_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationSourceWithdrawalAddress')
        ),
        None,
    )
    assert user_wa_alert is not None

    rejected_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationCLRejected')
        ),
        None,
    )
    assert rejected_consolidation_alert is None


def test_consolidation_for_source_requested_to_exit_by_vebo(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])

    pending_consolidation = PendingConsolidation(
        source_index='1',
        target_index='2',
    )
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[pending_consolidation])

    handler = ConsolidationHandler()
    handler.last_requested_exit_indexes = {1000: set()}
    handler.last_requested_exit_indexes[1000].add(1)

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

    requested_to_exit_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationRequestedToExit')
        ),
        None,
    )
    assert requested_to_exit_consolidation_alert is not None
    assert requested_to_exit_consolidation_alert.labels.severity == 'critical'
    assert (
        requested_to_exit_consolidation_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators that were requested to exit by VEBO**"
    )
    assert withdrawal_address in requested_to_exit_consolidation_alert.annotations.description
    assert source_validator.index in requested_to_exit_consolidation_alert.annotations.description
    assert user_validator_1.pubkey in requested_to_exit_consolidation_alert.annotations.description
    assert target_validator.index in requested_to_exit_consolidation_alert.annotations.description
    assert user_validator_2.pubkey in requested_to_exit_consolidation_alert.annotations.description


def test_consolidation_for_target_requested_to_exit_by_vebo(
    user_validator_1: TestValidator, user_validator_2: TestValidator, watcher: WatcherStub, withdrawal_address: str
):
    block = create_sample_block(
        consolidations=[
            ConsolidationRequest(
                source_address=withdrawal_address,
                source_pubkey=user_validator_1.pubkey,
                target_pubkey=user_validator_2.pubkey,
            )
        ]
    )

    source_validator_state = ValidatorState(
        pubkey=user_validator_1.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    source_validator = Validator(
        index='1',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_EXITING,
        validator=source_validator_state,
    )

    target_validator_state = ValidatorState(
        pubkey=user_validator_2.pubkey,
        withdrawal_credentials=withdrawal_address,
        effective_balance='32000000000',
        slashed=False,
        activation_eligibility_epoch='2048',
        activation_epoch='2048',
        exit_epoch='1000000000',
        withdrawable_epoch='1000000000',
    )
    target_validator = Validator(
        index='2',
        balance='32000000000',
        status=ValidatorStatus.ACTIVE_ONGOING,
        validator=target_validator_state,
    )

    watcher.consensus.get_validators = MagicMock(return_value=[source_validator, target_validator])

    pending_consolidation = PendingConsolidation(
        source_index='1',
        target_index='2',
    )
    watcher.consensus.get_pending_consolidations = MagicMock(return_value=[pending_consolidation])

    handler = ConsolidationHandler()
    handler.last_requested_exit_indexes = {1000: set()}
    handler.last_requested_exit_indexes[1000].add(2)

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

    requested_to_exit_consolidation_alert = next(
        (
            alert
            for alert in watcher.alertmanager.sent_alerts
            if alert.labels.alertname.startswith('HeadWatcherConsolidationRequestedToExit')
        ),
        None,
    )
    assert requested_to_exit_consolidation_alert is not None
    assert requested_to_exit_consolidation_alert.labels.severity == 'critical'
    assert (
        requested_to_exit_consolidation_alert.annotations.summary
        == "**⚠️⚠️⚠️ Attempt to consolidate validators that were requested to exit by VEBO**"
    )
    assert withdrawal_address in requested_to_exit_consolidation_alert.annotations.description
    assert source_validator.index in requested_to_exit_consolidation_alert.annotations.description
    assert user_validator_1.pubkey in requested_to_exit_consolidation_alert.annotations.description
    assert target_validator.index in requested_to_exit_consolidation_alert.annotations.description
    assert user_validator_2.pubkey in requested_to_exit_consolidation_alert.annotations.description


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
        == "**⚠️⚠️⚠️ Consolidation was requested for our validators (not from Withdrawal Vault address)**"
    )
    assert random_source_address in alert.annotations.description
    assert user_validator_1.pubkey in alert.annotations.description
    assert random_target_pubkey_1 in alert.annotations.description
    assert random_target_pubkey_2 in alert.annotations.description
    assert block.message.slot in alert.annotations.description
