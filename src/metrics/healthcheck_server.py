import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler

from src import variables

# None until the watcher has completed a cycle: "no cycle yet" and "cycle went stale" are
# different states, and the warm-up gate has to tell them apart.
_last_pulse: datetime | None = None


def record_pulse():
    """Called by the watcher when a cycle completes."""
    global _last_pulse
    _last_pulse = datetime.now()


def last_pulse() -> datetime | None:
    """When the watcher last completed a cycle, or None if it has not yet."""
    return _last_pulse


def _pulse_is_fresh() -> bool:
    if _last_pulse is None:
        return False
    return datetime.now() - _last_pulse <= timedelta(seconds=variables.MAX_CYCLE_LIFETIME_IN_SECONDS)


class PulseRequestHandler(SimpleHTTPRequestHandler):
    """
    Request handler for the Docker HEALTHCHECK and for Kubernetes probes.

    `/pulse/` predates both and doubles as an input: a GET on it *updates* the timer, so it
    cannot be probed for an answer about the watcher — any prober would refresh the very
    timestamp it is asking about. The Docker HEALTHCHECK on the VM deployment does exactly
    that, so the endpoint stays as it is; `/healthz` and `/readyz` are read-only and answer
    two narrower questions:

      * `/healthz` — this process is up and serving. Liveness.
      * `/readyz` — the watcher has finished its first cycle. Startup and readiness.

    Neither reports staleness, and that is deliberate:

      * a liveness probe that fails on a stale cycle restarts the pod, and a restart costs a
        full re-read of the validator set and of every Lido key — minutes during which nothing
        is watched. When the cause is a degraded upstream, that turns into a restart loop that
        makes the outage longer. `EHWStuckBotProcessing` already pages a human for this.
      * a readiness probe that fails on a stale cycle takes the pod out of the Service, which
        takes the pod out of Prometheus' targets — so the metric that would have proved the
        watcher is stuck goes absent instead of going flat. Absence is the harder signal to
        alert on, so readiness is a one-way gate: it opens after the first cycle and stays
        open. Staleness is `HeadBlockIsNotChanging` on the metric, not a kubelet decision.
    """

    def do_GET(self):
        if self.path == '/pulse/':
            record_pulse()
            self._respond_by_freshness()
        elif self.path == '/healthz':
            self._respond(200, 'ok', 'serving')
        elif self.path == '/readyz':
            if _last_pulse is None:
                self._respond(503, 'fail', 'no cycle completed yet')
            else:
                self._respond(200, 'ok', 'ok')
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_by_freshness(self):
        if _pulse_is_fresh():
            self._respond(200, 'ok', 'ok')
        else:
            self._respond(503, 'fail', 'timeout exceeded')

    def _respond(self, status: int, metrics: str, reason: str):
        self.send_response(status)
        self.end_headers()
        self.wfile.write(f'{{"metrics": "{metrics}", "reason": "{reason}"}}\n'.encode())

    def log_request(self, *args, **kwargs):
        # Disable non-error logs
        pass


def start_pulse_server() -> HTTPServer:
    """
    This is simple server for bots without any API.
    If bot didn't call pulse for a while (5 minutes but should be changed individually)
    healthcheck in docker returns 1 and bot will be restarted
    """
    server = HTTPServer(
        (variables.HEALTHCHECK_SERVER_HOST, variables.HEALTHCHECK_SERVER_PORT),
        RequestHandlerClass=PulseRequestHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
