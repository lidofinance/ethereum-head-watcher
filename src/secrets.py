"""
Secrets that arrive as a file, and how a rotation is noticed.

Node endpoints carry provider credentials, so they are delivered by the OpenBao agent as a JSON
file under /vault/secrets rather than as environment variables. The reason is not aesthetics: a
process cannot be handed new environment variables from outside, so any env-based delivery costs
a pod restart per rotation — and a restart here costs minutes of re-reading the validator set and
every Lido key, during which nothing is watched.

The agent updates the file by writing a temp file and renaming it over the path. The rename is
atomic, so a reader never sees half a file — but it also creates a new inode, which is why this
polls the path with stat() instead of watching the file. A watcher attached to the file itself
(inotify, watchdog) goes silent after the first rotation.

When the file is absent everything falls back to environment variables, which is how the VM
deployment runs.
"""

import json
import logging
import os
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_IN_SECONDS = 10


def read_secrets_file(path: str) -> dict[str, str]:
    """
    The file's contents, or an empty mapping if there is no usable file.

    Absent is a normal state — it means "no agent here, use the environment". Present but
    unparseable is not, so it is logged loudly and then treated the same way: refusing to start
    would turn a bad render of one key into an outage of the whole watcher.
    """
    if not path:
        return {}
    try:
        with open(path) as file:
            values = json.load(file)
    except FileNotFoundError:
        logger.info({'msg': f'No secrets file at {path}, reading configuration from the environment'})
        return {}
    except (OSError, ValueError) as error:
        logger.error({'msg': f'Can not read secrets file {path}', 'exception': str(error)})
        return {}

    if not isinstance(values, dict):
        logger.error({'msg': f'Secrets file {path} is not a JSON object, ignoring it'})
        return {}

    return {key: str(value) for key, value in values.items()}


class SecretsWatcher:
    """Re-reads the secrets file when its mtime changes and hands the new values to a callback."""

    def __init__(
        self,
        path: str,
        on_change: Callable[[dict[str, str]], None],
        interval: int = DEFAULT_POLL_INTERVAL_IN_SECONDS,
        on_error: Callable[[], None] | None = None,
    ):
        self._path = path
        self._on_change = on_change
        # A hook rather than a metric import: metrics read variables, and variables read this
        # module at import time, so importing metrics here would close a cycle.
        self._on_error = on_error
        self._interval = interval
        self._mtime = self._read_mtime()

    def _read_mtime(self) -> int | None:
        try:
            return os.stat(self._path).st_mtime_ns
        except OSError:
            return None

    def check_once(self) -> bool:
        """
        True if a change was seen and applied. Kept separate from the loop so the behaviour is
        testable without waiting on a thread.
        """
        mtime = self._read_mtime()
        if mtime is None or mtime == self._mtime:
            return False

        values = read_secrets_file(self._path)
        if not values:
            # A rotation that renders to nothing is not something to apply over working values.
            logger.error(
                {'msg': f'Secrets file {self._path} changed but has no usable values, keeping the previous ones'}
            )
            self._mtime = mtime
            self._report_error()
            return False

        try:
            self._on_change(values)
        except Exception as error:  # pylint: disable=broad-except
            logger.error({'msg': 'Can not apply rotated secrets, keeping the previous ones', 'exception': str(error)})
            self._mtime = mtime
            self._report_error()
            return False

        self._mtime = mtime
        logger.info({'msg': f'Secrets reloaded from {self._path}'})
        return True

    def _report_error(self):
        if self._on_error is not None:
            self._on_error()

    def start(self) -> threading.Thread:
        def _watch():
            while True:
                time.sleep(self._interval)
                self.check_once()

        thread = threading.Thread(target=_watch, daemon=True, name='secrets-watcher')
        thread.start()
        return thread
