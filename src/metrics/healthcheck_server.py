import logging
import threading
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler

import requests

from src import variables
from src.variables import MAX_CYCLE_LIFETIME_IN_SECONDS

logger = logging.getLogger()

PULSE_PATH = '/pulse/'
# Kubernetes probes read state and must never write it, so they get their own paths. `/pulse/`
# stays exactly as the Docker HEALTHCHECK uses it.
LIVENESS_PATH = '/healthz'
READINESS_PATH = '/readyz'

ALIVE_BODY = b'{"metrics": "ok", "reason": "ok"}\n'
TIMEOUT_BODY = b'{"metrics": "fail", "reason": "timeout exceeded"}\n'
SERVING_BODY = b'{"metrics": "ok", "reason": "serving"}\n'
COLD_BODY = b'{"metrics": "fail", "reason": "no cycle completed yet"}\n'

_last_pulse = datetime.now()
# Distinct from _last_pulse, which starts warm so that the Docker HEALTHCHECK does not fail a
# container that is still starting. Readiness needs the opposite answer: a watcher that has not
# finished a cycle is not caught up, and its first cycle reads the whole validator set and every
# Lido key, which takes minutes.
_first_pulse_registered = False


def pulse():
    """
    Tell the healthcheck server that the watcher is still making progress.

    Never raises: a healthcheck ping must not break the head cycle. A server that can not be reached
    fails the Docker HEALTHCHECK on its own anyway.
    """
    try:
        requests.post(f'http://localhost:{variables.HEALTHCHECK_SERVER_PORT}{PULSE_PATH}', timeout=10)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning({'msg': 'Can not reach the healthcheck server', 'exception': str(e)})


def register_pulse() -> None:
    global _last_pulse, _first_pulse_registered
    _last_pulse = datetime.now()
    _first_pulse_registered = True


def is_ready() -> bool:
    """Whether the watcher has completed a cycle at least once"""
    return _first_pulse_registered


def is_alive() -> bool:
    """Whether the watcher reported progress recently enough"""
    return datetime.now() - _last_pulse <= timedelta(seconds=MAX_CYCLE_LIFETIME_IN_SECONDS)


class PulseRequestHandler(SimpleHTTPRequestHandler):
    """
    Request handler for Docker HEALTHCHECK.

    The watcher reports progress with POST while the healthcheck reads the state with GET, and the
    split matters: as long as both were served by GET, every healthcheck refreshed the very deadline
    it was about to check, so a stuck watcher stayed healthy forever.
    """

    def do_POST(self):
        register_pulse()
        self._respond(HTTPStatus.OK, ALIVE_BODY)

    def do_GET(self):
        if self.path == LIVENESS_PATH:
            # Serving, nothing more. Staleness deliberately does not fail liveness here: a restart
            # costs a full re-read of the validator set and of every Lido key, and when the cause is
            # a degraded upstream that turns into a restart loop which makes the outage longer.
            # `EHWStuckBotProcessing` pages a human for that instead.
            self._respond(HTTPStatus.OK, SERVING_BODY)
        elif self.path == READINESS_PATH:
            # A one-way gate: it opens after the first completed cycle and stays open. Failing it
            # later would take the pod out of the Service and therefore out of Prometheus' targets,
            # which turns a flat metric into an absent one — the harder signal to alert on.
            if is_ready():
                self._respond(HTTPStatus.OK, ALIVE_BODY)
            else:
                self._respond(HTTPStatus.SERVICE_UNAVAILABLE, COLD_BODY)
        elif is_alive():
            self._respond(HTTPStatus.OK, ALIVE_BODY)
        else:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, TIMEOUT_BODY)

    def _respond(self, status: HTTPStatus, body: bytes):
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    def log_request(self, *args, **kwargs):
        # Disable non-error logs
        pass


def start_pulse_server() -> HTTPServer:
    """
    This is simple server for bots without any API.
    If bot didn't call pulse for a while (5 minutes but should be changed individually)
    healthcheck in docker returns 1 and bot will be restarted
    """
    # Kubernetes probes arrive on the pod IP, so binding to localhost makes them unreachable.
    server = HTTPServer(
        (variables.HEALTHCHECK_SERVER_HOST, variables.HEALTHCHECK_SERVER_PORT),
        RequestHandlerClass=PulseRequestHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
