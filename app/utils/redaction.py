import logging
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = {
    "authorization",
    "authorizationheader",
    "accesstoken",
    "admintoken",
    "bearertoken",
    "databasesecret",
    "databaseurl",
    "dbpassword",
    "dburl",
    "discordwebhook",
    "discordwebhookurl",
    "hashedpassword",
    "jwttoken",
    "key",
    "password",
    "passwordhash",
    "privatekey",
    "proxycredentials",
    "proxypassword",
    "proxyurl",
    "secret",
    "secretkey",
    "sslkey",
    "subscriptiontoken",
    "subscriptionurl",
    "telegramapitoken",
    "telegrambottoken",
    "tlskey",
    "tlsprivatekey",
    "tlspassword",
    "tlssecret",
    "token",
    "webhook",
    "webhookaddress",
    "webhooksecret",
    "webhookurl",
}

_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "apikey",
    "api_key",
    "auth",
    "authorization",
    "key",
    "password",
    "secret",
    "signature",
    "token",
}

_URL_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>'\"]+")
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----.*?"
    r"-----END(?: [A-Z0-9]+)? PRIVATE KEY-----",
    re.DOTALL,
)
_JWT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r"(?![A-Za-z0-9_-])"
)
_PASSWORD_HASH_RE = re.compile(
    r"(?<!\S)(?:"
    r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"
    r"|\$argon2(?:id|i|d)\$[^\s,;]+"
    r"|\$[156]\$[^\s,;]+"
    r")"
)
_AUTHORIZATION_RE = re.compile(
    r"(?i)(\bauthorization\s*[:=]\s*)(?:bearer|basic)\s+[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_LABELED_SECRET_RE = re.compile(
    r"(?ix)"
    r"(\b(?:"
    r"access[_-]?token|api[_-]?key|database[_-]?(?:password|url)|db[_-]?(?:password|url)|"
    r"hashed[_-]?password|jwt[_-]?token|password(?:[_-]?hash)?|private[_-]?key|"
    r"proxy[_-]?(?:credentials|password|url)|secret(?:[_-]?key)?|subscription[_-]?(?:token|url)|"
    r"telegram[_-]?(?:api|bot)[_-]?token|tls[_-]?(?:key|password|secret)|token|"
    r"webhook[_-]?(?:address|secret|url)"
    r")\b\s*[:=]\s*)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)


def _normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).casefold())


def _is_sensitive_key(key: Any) -> bool:
    normalized = _normalized_key(key)
    if normalized in _SENSITIVE_KEYS:
        return True
    return (
        normalized.endswith("password")
        or normalized.endswith("passwordhash")
        or normalized.endswith("privatekey")
        or normalized.endswith("webhooksecret")
    )


def _redact_url(match: re.Match[str]) -> str:
    raw_url = match.group(0)
    trailing = ""
    while raw_url and raw_url[-1] in ".,;:!?)]}":
        trailing = raw_url[-1] + trailing
        raw_url = raw_url[:-1]

    try:
        parsed = urlsplit(raw_url)
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        return REDACTED + trailing

    path = parsed.path.casefold()
    if (
        "/api/webhooks/" in path
        or (
            parsed.hostname
            and parsed.hostname.casefold() == "api.telegram.org"
            and re.match(r"/bot[^/]+/", path)
        )
        or re.search(
            r"/(?:sub|subscribe|subscription)(?:/|$)", path
        )
    ):
        return REDACTED + trailing

    hostname = parsed.hostname or ""
    netloc = parsed.netloc
    if parsed.username is not None or parsed.password is not None:
        netloc = f"{REDACTED}@{hostname}{port}"

    query = parse_qsl(parsed.query, keep_blank_values=True)
    if query:
        query = [
            (key, REDACTED if key.casefold() in _SENSITIVE_QUERY_KEYS else value)
            for key, value in query
        ]

    return urlunsplit(
        (parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment)
    ) + trailing


def redact_text(value: str) -> str:
    """Return text with common credential forms removed."""
    redacted = _PRIVATE_KEY_RE.sub(REDACTED, value)
    redacted = _AUTHORIZATION_RE.sub(rf"\1{REDACTED}", redacted)
    redacted = _BEARER_RE.sub(rf"\1{REDACTED}", redacted)
    redacted = _JWT_RE.sub(REDACTED, redacted)
    redacted = _PASSWORD_HASH_RE.sub(REDACTED, redacted)
    redacted = _URL_RE.sub(_redact_url, redacted)
    return _LABELED_SECRET_RE.sub(rf"\1{REDACTED}", redacted)


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redact secrets from values before external output."""
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        value = model_dump()

    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    if isinstance(value, set):
        return {redact_sensitive_data(item) for item in value}
    if isinstance(value, str):
        return redact_text(value)
    return value


def _redact_log_arg(value: Any) -> Any:
    if isinstance(value, (str, bytes)):
        text = value.decode(errors="replace") if isinstance(value, bytes) else value
        return redact_text(text)
    if isinstance(value, (Mapping, list, tuple, set)):
        return redact_sensitive_data(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_text(str(value))


class RedactingFilter(logging.Filter):
    """Redact secrets from a log record before any handler emits it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if isinstance(record.args, Mapping):
            record.args = redact_sensitive_data(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(_redact_log_arg(value) for value in record.args)
        elif record.args:
            record.args = _redact_log_arg(record.args)
        if record.exc_info:
            record.exc_text = redact_text(
                logging.Formatter().formatException(record.exc_info)
            )
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = redact_text(record.exc_text)
        return True


def install_redaction_filter(*logger_names: str) -> None:
    """Install one redaction filter on each named logger."""
    for logger_name in logger_names:
        target = logging.getLogger(logger_name)
        if not any(isinstance(item, RedactingFilter) for item in target.filters):
            target.addFilter(RedactingFilter())
