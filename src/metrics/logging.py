import json
import logging
import sys
import threading
from types import TracebackType
from typing import Any

from src.utils.urls import redact_text
from src.variables import LOG_LEVEL


def mask_field(value: Any) -> Any:
    """Redaction for one log field, into the containers a message dict nests."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: mask_field(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(mask_field(item) for item in value)
    return value


class JsonFormatter(logging.Formatter):
    """
    The one place a provider credential is redacted, ours and our dependencies' lines alike.

    Both halves are needed: the registered endpoint parts catch a key named without a scheme, URL masking catches an
    endpoint this process was never configured with.
    """

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            message = mask_field(record.msg)
        else:
            message = {'msg': redact_text(record.getMessage())}

        if 'value' in message:
            message['value'] = str(message['value'])

        payload = {
            'name': record.name,
            'levelname': record.levelname,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'module': record.module,
            'pathname': record.pathname,
            **message,
        }

        if record.exc_info:
            payload['exc_info'] = redact_text(self.formatException(record.exc_info))

        return json.dumps(payload)


def log_uncaught(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """
    Route a crash through the logger.

    Python's default hook writes the traceback straight to stderr, past the formatter — and the traceback of a failed
    request carries the endpoint it failed on, credential included.
    """
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger().critical({'msg': 'Unhandled exception'}, exc_info=(exc_type, exc_value, exc_traceback))


def _log_uncaught_in_thread(args: threading.ExceptHookArgs) -> None:
    if args.exc_value is not None:
        log_uncaught(args.exc_type, args.exc_value, args.exc_traceback)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logging.basicConfig(
    level=LOG_LEVEL,
    handlers=[handler],
)

sys.excepthook = log_uncaught
# The secrets watcher runs in its own thread, and a thread's crash goes through a different hook.
threading.excepthook = _log_uncaught_in_thread
