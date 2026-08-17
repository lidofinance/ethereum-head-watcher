import socket
from datetime import datetime, timedelta

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
    """A running pulse server on a free port, with no cycle recorded yet."""
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_HOST', '127.0.0.1')
    monkeypatch.setattr(variables, 'HEALTHCHECK_SERVER_PORT', _free_port())
    monkeypatch.setattr(healthcheck_server, '_last_pulse', None)

    server = healthcheck_server.start_pulse_server()
    yield f'http://127.0.0.1:{variables.HEALTHCHECK_SERVER_PORT}'
    server.shutdown()
    server.server_close()


def test_healthz_is_up_before_the_first_cycle(health_server):
    # Liveness must not fail during a cold start: reading the validator set and every Lido key
    # takes minutes, and restarting the pod over it would never let the watcher finish.
    response = requests.get(f'{health_server}/healthz', timeout=5)

    assert response.status_code == 200


def test_readyz_is_not_ready_before_the_first_cycle(health_server):
    response = requests.get(f'{health_server}/readyz', timeout=5)

    assert response.status_code == 503
    assert 'no cycle completed yet' in response.text


def test_readyz_does_not_record_a_cycle(health_server):
    # The bug this guards: /pulse/ updates the timer, so probing it answers its own question.
    # A probe on /readyz must observe the watcher, not stand in for it.
    requests.get(f'{health_server}/readyz', timeout=5)
    requests.get(f'{health_server}/readyz', timeout=5)

    assert healthcheck_server._last_pulse is None


def test_healthz_does_not_record_a_cycle(health_server):
    requests.get(f'{health_server}/healthz', timeout=5)

    assert healthcheck_server._last_pulse is None


def test_readyz_is_ready_after_a_cycle(health_server):
    healthcheck_server.record_pulse()

    response = requests.get(f'{health_server}/readyz', timeout=5)

    assert response.status_code == 200


def test_readyz_stays_ready_when_the_cycle_goes_stale(health_server, monkeypatch):
    # Readiness is a one-way warm-up gate on purpose: dropping out of the Service would drop
    # the pod out of Prometheus' targets, and the metric that proves the watcher is stuck would
    # go absent instead of going flat. Staleness is an alert on the metric, not a kubelet call.
    monkeypatch.setattr(healthcheck_server, '_last_pulse', _stale_pulse())

    response = requests.get(f'{health_server}/readyz', timeout=5)

    assert response.status_code == 200


def test_healthz_stays_up_when_the_cycle_goes_stale(health_server, monkeypatch):
    monkeypatch.setattr(healthcheck_server, '_last_pulse', _stale_pulse())

    response = requests.get(f'{health_server}/healthz', timeout=5)

    assert response.status_code == 200


def test_pulse_endpoint_still_records_a_cycle(health_server):
    # The Docker HEALTHCHECK on the VM deployment keeps hitting /pulse/; it has to keep working.
    response = requests.get(f'{health_server}/pulse/', timeout=5)

    assert response.status_code == 200
    assert healthcheck_server._last_pulse is not None


def test_pulse_endpoint_reports_a_stale_cycle(health_server, monkeypatch):
    monkeypatch.setattr(healthcheck_server, '_last_pulse', _stale_pulse())
    monkeypatch.setattr(healthcheck_server, 'record_pulse', lambda: None)

    response = requests.get(f'{health_server}/pulse/', timeout=5)

    assert response.status_code == 503
    assert 'timeout exceeded' in response.text


def test_unknown_path_is_not_found(health_server):
    response = requests.get(f'{health_server}/', timeout=5)

    assert response.status_code == 404


def _stale_pulse() -> datetime:
    return datetime.now() - timedelta(seconds=variables.MAX_CYCLE_LIFETIME_IN_SECONDS + 1)
