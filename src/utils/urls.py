import re
import threading
from typing import Iterable
from urllib.parse import urlparse

URL_IN_TEXT = re.compile(r'https?://[^\s\'"]+')

_LOCK = threading.Lock()
# Registered substring -> what it is replaced with. Readers take `_redaction` in a single load, writers
# swap a whole new tuple, so the secrets watcher thread cannot be seen half-way through an update.
_parts: dict[str, str] = {}
_redaction: tuple[re.Pattern[str], dict[str, str]] | None = None


def mask_url(url: str) -> str:
    """Scheme and host only: keys travel as `?key=` or as a path segment; the host says which provider failed."""
    parsed = urlparse(url)
    if not parsed.netloc:
        return url
    return f'{parsed.scheme}://{parsed.netloc}'


def mask_urls_in(text: str) -> str:
    """`mask_url` for every URL inside a text, such as an exception string from `requests`."""
    return URL_IN_TEXT.sub(lambda match: mask_url(match.group()), text)


def credential_parts(url: str) -> dict[str, str]:
    """The substrings of one endpoint that must not be logged, with replacements; none for a bare host."""
    endpoint = url.strip()
    parsed = urlparse(endpoint)
    if not parsed.netloc:
        return {}

    parts: dict[str, str] = {}
    userinfo, _, host = parsed.netloc.rpartition('@')
    if userinfo:
        parts[userinfo] = '****'
    # Trailing slash off, so a base path also matches the longer request path built on top of it.
    if path := parsed.path.rstrip('/'):
        parts[path] = '/****'
    if parsed.query:
        parts[parsed.query] = '****'
        parts[f'{parsed.path}?{parsed.query}'] = '/****'
    if not parts:
        return {}

    parts[endpoint] = f'{parsed.scheme}://{host}'
    return parts


def register_credential_urls(*endpoint_lists: Iterable[str]) -> None:
    """Teach `redact_text` the path, query and userinfo of every configured endpoint, by value.
    Only ever adds: a key rotated out an hour ago is still a key in an exception logged now."""
    global _redaction  # pylint: disable=global-statement
    with _LOCK:
        added = False
        for endpoints in endpoint_lists:
            for endpoint in endpoints:
                for part, replacement in credential_parts(endpoint).items():
                    if part and part not in _parts:
                        _parts[part] = replacement
                        added = True
        if not added:
            return
        # Longest first, so a whole URL is not consumed by the path registered from it.
        pattern = '|'.join(re.escape(part) for part in sorted(_parts, key=len, reverse=True))
        _redaction = (re.compile(pattern), dict(_parts))


def redact_registered_parts(text: str) -> str:
    """Redaction by value: `requests` names a failed request by its path alone (`url: /v2/<key>/...`),
    with no `https://` for `mask_urls_in` to match."""
    redaction = _redaction
    if redaction is None:
        return text
    pattern, replacements = redaction
    return pattern.sub(lambda match: replacements[match.group()], text)


def redact_text(text: str) -> str:
    """Value redaction first, so a URL whose path became `/****` still collapses to scheme and host."""
    return mask_urls_in(redact_registered_parts(text))
