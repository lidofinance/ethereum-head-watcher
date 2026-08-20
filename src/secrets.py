"""
Secrets that arrive as a file, and how a change to it is noticed.

Node endpoints carry provider credentials and are delivered as a JSON file, because a process cannot be handed new
environment variables from outside: env-based delivery costs a restart per rotation. The file is replaced by a rename,
which gives it a new inode, so this polls the path with stat() rather than watching the file.

No file means the values come from the environment.
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

    Absent is normal and means "use the environment". Unparseable is logged and treated the same way, so one bad value
    cannot keep the watcher from starting.
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
        # A hook rather than importing the metric here, which would close an import cycle.
        self._on_error = on_error
        self._interval = interval
        self._mtime = self._read_mtime()

    def _read_mtime(self) -> int | None:
        try:
            return os.stat(self._path).st_mtime_ns
        except OSError:
            return None

    def check_once(self) -> bool:
        """True if a change was seen and applied. Separate from the loop so it is testable."""
        mtime = self._read_mtime()
        if mtime is None or mtime == self._mtime:
            return False

        values = read_secrets_file(self._path)
        if not values:
            # Nothing usable: keep the values already in force.
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
