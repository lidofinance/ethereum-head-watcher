"""
The Kubernetes half of the healthcheck server.

`tests/test_healthcheck.py` covers the POST/GET split on `/pulse/` — the fix for a healthcheck that
refreshed the deadline it was about to check. What is covered here is what Kubernetes needs on top of
it: a bind address probes can reach, and two read-only paths that answer different questions.
"""

import socket

import pytest
import requests

from src import variables
from src.metrics import healthcheck_server


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture
def health_server(monkeypatch):
    """A running server on a free port, with no cycle completed yet."""
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_HOST', '127.0.0.1')
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_PORT', _free_port())
    monkeypatch.setattr(healthcheck_server, '_first_pulse_registered', False)

    server = healthcheck_server.start_pulse_server()
    yield f'http://127.0.0.1:{variables.HEALTHCHECK_SERVER_PORT}'
    server.shutdown()
    server.server_close()


def test_the_server_is_reachable_on_a_non_loopback_bind(monkeypatch):
    # The reason this test exists: bound to localhost, the server answers the container and not the
    # kubelet, which probes the pod IP. The assertion is that the bind address is configurable at
    # all — a probe against a real pod IP is not something a unit test can do.
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_HOST', '0.0.0.0')
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_PORT', _free_port())

    server = healthcheck_server.start_pulse_server()
    try:
        assert server.server_address[0] == '0.0.0.0'
        response = requests.get(f'http://127.0.0.1:{variables.HEALTHCHECK_SERVER_PORT}/healthz', timeout=5)
        assert response.status_code == 200
    finally:
        server.shutdown()
        server.server_close()


def test_liveness_is_up_before_the_first_cycle(health_server):
    # A cold start reads the whole validator set and every Lido key; liveness must not restart the
    # pod over that.
    response = requests.get(f'{health_server}/healthz', timeout=5)

    assert response.status_code == 200
    assert 'serving' in response.text


def test_readiness_is_closed_before_the_first_cycle(health_server):
    response = requests.get(f'{health_server}/readyz', timeout=5)

    assert response.status_code == 503
    assert 'no cycle completed yet' in response.text


def test_readiness_opens_after_a_cycle(health_server):
    healthcheck_server.register_pulse()

    response = requests.get(f'{health_server}/readyz', timeout=5)

    assert response.status_code == 200


def test_probes_do_not_register_progress(health_server):
    # The bug the POST/GET split fixed, guarded from the other side: neither probe may stand in for
    # the watcher.
    requests.get(f'{health_server}/healthz', timeout=5)
    requests.get(f'{health_server}/readyz', timeout=5)

    assert healthcheck_server.is_ready() is False


def test_pulse_still_reports_liveness_to_docker(health_server):
    requests.post(f'{health_server}/pulse/', timeout=5)

    response = requests.get(f'{health_server}/pulse/', timeout=5)

    assert response.status_code == 200
