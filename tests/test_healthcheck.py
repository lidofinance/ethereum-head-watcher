import io
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from src.metrics import healthcheck_server
from src.metrics.healthcheck_server import PulseRequestHandler, is_alive, pulse
from src.variables import MAX_CYCLE_LIFETIME_IN_SECONDS


class HandlerStub(PulseRequestHandler):
    """Request handler without a socket behind it"""

    def __init__(self):  # pylint: disable=super-init-not-called
        self.statuses = []
        self.wfile = io.BytesIO()

    def send_response(self, code, message=None):
        self.statuses.append(code)

    def end_headers(self):
        pass


@pytest.fixture
def stale_pulse(monkeypatch):
    monkeypatch.setattr(
        healthcheck_server,
        '_last_pulse',
        datetime.now() - timedelta(seconds=MAX_CYCLE_LIFETIME_IN_SECONDS + 1),
    )


@pytest.fixture
def handler():
    return HandlerStub()


def test_a_watcher_reporting_progress_is_alive(handler: HandlerStub, stale_pulse):
    handler.do_POST()

    assert handler.statuses == [HTTPStatus.OK]
    assert is_alive()


def test_a_watcher_that_stopped_reporting_progress_is_not_alive(handler: HandlerStub, stale_pulse):
    handler.do_GET()

    assert handler.statuses == [HTTPStatus.SERVICE_UNAVAILABLE]
    assert handler.wfile.getvalue() == healthcheck_server.TIMEOUT_BODY


def test_reading_the_state_does_not_extend_the_deadline(handler: HandlerStub, stale_pulse):
    """
    The Docker HEALTHCHECK asks with GET. While the same request also refreshed the deadline, a
    stuck watcher stayed healthy forever, because every check reset the timer it was checking.
    """
    handler.do_GET()
    handler.do_GET()

    assert handler.statuses == [HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.SERVICE_UNAVAILABLE]


def test_a_pulse_makes_the_state_healthy_again(handler: HandlerStub, stale_pulse):
    handler.do_GET()
    handler.do_POST()
    handler.do_GET()

    assert handler.statuses == [HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.OK, HTTPStatus.OK]


def test_pulse_does_not_raise_when_the_server_is_unreachable(monkeypatch):
    """The head cycle must not be broken by a healthcheck ping"""
    monkeypatch.setattr(healthcheck_server.requests, 'post', MagicMock(side_effect=ConnectionError('boom')))

    pulse()


def test_pulse_is_sent_as_a_post(monkeypatch):
    post = MagicMock()
    monkeypatch.setattr(healthcheck_server.requests, 'post', post)

    pulse()

    assert post.call_args.args[0].endswith(healthcheck_server.PULSE_PATH)
