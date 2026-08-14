from unittest.mock import MagicMock

from prometheus_client import REGISTRY

from src.handlers.execution_requests import (
    UNAVAILABLE_ALERT_REPEAT_IN_BLOCKS,
    UNAVAILABLE_BLOCKS_BEFORE_ALERT,
    ExecutionRequestsHandler,
)
from src.providers.consensus.typings import FullBlockInfo
from src.utils.execution_requests import resolve_execution_requests
from src.variables import PROMETHEUS_PREFIX
from tests.execution_requests.helpers import (
    GLOAS_HEAD_SLOT,
    GLOAS_PARENT_SLOT,
    create_gloas_head_with_envelope,
    create_sample_block,
    random_hex,
)
from tests.execution_requests.stubs import WatcherStub

SOURCE_METRIC = f'{PROMETHEUS_PREFIX}_execution_requests_source_total'


def unavailable_head(watcher: WatcherStub, slot: str = GLOAS_HEAD_SLOT, parent_slot: str = GLOAS_PARENT_SLOT):
    """Head whose parent payload was applied, but the envelope with its requests can not be read"""
    head = create_gloas_head_with_envelope(watcher, slot=slot, parent_slot=parent_slot)
    watcher.consensus.get_execution_payload_envelope = MagicMock(return_value=None)
    return head


def handle(handler: ExecutionRequestsHandler, watcher: WatcherStub, head: FullBlockInfo, times: int = 1):
    for _ in range(times):
        handler.handle(watcher, head).result()


def test_no_alert_while_the_requests_are_readable(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()

    handle(handler, watcher, create_sample_block(), times=UNAVAILABLE_BLOCKS_BEFORE_ALERT * 2)
    handle(handler, watcher, create_gloas_head_with_envelope(watcher), times=UNAVAILABLE_BLOCKS_BEFORE_ALERT * 2)

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_no_alert_when_nothing_was_applied(watcher: WatcherStub):
    """A payload the builder never revealed is not a gap in monitoring"""
    handler = ExecutionRequestsHandler()
    head = create_gloas_head_with_envelope(watcher)
    head.message.body.signed_execution_payload_bid.message.parent_block_hash = random_hex(32)

    handle(handler, watcher, head, times=UNAVAILABLE_BLOCKS_BEFORE_ALERT * 2)

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_no_alert_before_the_outage_is_confirmed(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()

    handle(handler, watcher, unavailable_head(watcher), times=UNAVAILABLE_BLOCKS_BEFORE_ALERT - 1)

    assert len(watcher.alertmanager.sent_alerts) == 0


def test_alert_when_the_outage_is_confirmed(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()
    head = unavailable_head(watcher)

    handle(handler, watcher, head, times=UNAVAILABLE_BLOCKS_BEFORE_ALERT)

    assert len(watcher.alertmanager.sent_alerts) == 1
    alert = watcher.alertmanager.sent_alerts[0]
    assert alert.labels.alertname.startswith('HeadWatcherExecutionRequestsUnavailable')
    assert alert.labels.severity == 'info'
    assert alert.annotations.summary == "**🕶️ Execution requests can not be read**"
    assert f'Blocks in a row: {UNAVAILABLE_BLOCKS_BEFORE_ALERT}' in alert.annotations.description
    assert f'[{GLOAS_PARENT_SLOT}]' in alert.annotations.description
    assert head.message.slot in alert.annotations.description


def test_alert_is_not_repeated_on_every_block(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()

    handle(handler, watcher, unavailable_head(watcher), times=UNAVAILABLE_ALERT_REPEAT_IN_BLOCKS)

    assert len(watcher.alertmanager.sent_alerts) == 1


def test_alert_is_repeated_while_the_outage_lasts(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()
    blocks = UNAVAILABLE_BLOCKS_BEFORE_ALERT + UNAVAILABLE_ALERT_REPEAT_IN_BLOCKS

    handle(handler, watcher, unavailable_head(watcher), times=blocks)

    assert len(watcher.alertmanager.sent_alerts) == 2
    assert f'Blocks in a row: {blocks}' in watcher.alertmanager.sent_alerts[1].annotations.description


def test_recovery_resets_the_outage(watcher: WatcherStub):
    handler = ExecutionRequestsHandler()

    handle(handler, watcher, unavailable_head(watcher), times=UNAVAILABLE_BLOCKS_BEFORE_ALERT)
    handle(handler, watcher, create_sample_block())

    # A later outage happens at other slots, so its alert is not taken for an already sent one
    later = unavailable_head(watcher, slot='43', parent_slot='42')
    handle(handler, watcher, later, times=UNAVAILABLE_BLOCKS_BEFORE_ALERT - 1)

    assert len(watcher.alertmanager.sent_alerts) == 1

    handle(handler, watcher, later)

    assert len(watcher.alertmanager.sent_alerts) == 2
    assert '[42]' in watcher.alertmanager.sent_alerts[1].annotations.description


def test_source_of_the_requests_is_counted(watcher: WatcherStub):
    before = REGISTRY.get_sample_value(SOURCE_METRIC, {'source': 'envelope'}) or 0

    resolve_execution_requests(watcher, create_gloas_head_with_envelope(watcher))

    assert REGISTRY.get_sample_value(SOURCE_METRIC, {'source': 'envelope'}) == before + 1


def test_unavailable_source_is_counted(watcher: WatcherStub):
    before = REGISTRY.get_sample_value(SOURCE_METRIC, {'source': 'unavailable'}) or 0

    resolve_execution_requests(watcher, unavailable_head(watcher))

    assert REGISTRY.get_sample_value(SOURCE_METRIC, {'source': 'unavailable'}) == before + 1
