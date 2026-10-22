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

ALIVE_BODY = b'{"metrics": "ok", "reason": "ok"}\n'
TIMEOUT_BODY = b'{"metrics": "fail", "reason": "timeout exceeded"}\n'

_last_pulse = datetime.now()


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
    global _last_pulse
    _last_pulse = datetime.now()


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
        if is_alive():
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


def start_pulse_server():
    """
    This is simple server for bots without any API.
    If bot didn't call pulse for a while (5 minutes but should be changed individually)
    healthcheck in docker returns 1 and bot will be restarted
    """
    server = HTTPServer(('localhost', variables.HEALTHCHECK_SERVER_PORT), RequestHandlerClass=PulseRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
