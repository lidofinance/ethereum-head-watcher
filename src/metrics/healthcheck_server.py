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
# Unlike _last_pulse, starts cold: readiness waits for the first completed cycle, which reads every validator key.
_first_pulse_registered = False


def pulse():
    """Tell the healthcheck server the watcher is progressing. Never raises: a ping must not break the cycle."""
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
    """Docker HEALTHCHECK handler. The watcher POSTs progress and the check reads it with GET:
    while GET did both, every check refreshed the deadline it checked, and a stuck watcher stayed healthy."""

    def do_POST(self):
        register_pulse()
        self._respond(HTTPStatus.OK, ALIVE_BODY)

    def do_GET(self):
        if self.path == LIVENESS_PATH:
            # Liveness ignores staleness: a restart re-reads every validator and key, and a degraded upstream
            # would turn it into a restart loop.
            self._respond(HTTPStatus.OK, SERVING_BODY)
        elif self.path == READINESS_PATH:
            # One-way gate: failing it later drops the pod from the Service and from Prometheus' targets,
            # turning a flat metric into an absent one.
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
    This is simple server for bots without any API. If bot didn't call pulse for a while (5 minutes but should be
    changed individually) healthcheck in docker returns 1 and bot will be restarted.
    """
    server = HTTPServer(
        (variables.HEALTHCHECK_SERVER_HOST, variables.HEALTHCHECK_SERVER_PORT),
        RequestHandlerClass=PulseRequestHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
