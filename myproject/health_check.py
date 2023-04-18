import os
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler

import requests  # type: ignore

SERVER_PORT = int(os.getenv("PULSE_SERVER_PORT", "9010"))

_last_pulse = datetime.now()


def pulse():
    """Ping to healthcheck server that application is ok"""
    requests.get(f"http://localhost:{SERVER_PORT}/pulse/")


class PulseRequestHandler(SimpleHTTPRequestHandler):
    """Request handler for Docker HEALTHCHECK"""

    def do_GET(self):
        global _last_pulse  # pylint: disable=W0603,C0103

        if self.path == "/pulse/":
            _last_pulse = datetime.now()

        # Change 5 minutes to 2*usual_bot_cycle_time
        if datetime.now() - _last_pulse > timedelta(minutes=5):
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'{"status": "fail", "reason": "timeout exceeded"}\n')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "reason": "ok"}\n')

    def log_request(self, *args, **kwargs):
        # Disable non-error logs
        pass


def start_pulse_server():
    """
    This is simple server for bots without any API.
    If bot didn't call pulse for a while (5 minutes but should be changed individually)
    healthcheck in docker returns 1 and bot will be restarted
    """
    server = HTTPServer(
        ("localhost", SERVER_PORT), RequestHandlerClass=PulseRequestHandler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
