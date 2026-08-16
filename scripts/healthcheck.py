#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


HEALTH_PATH = "/api/marzhelp/compatibility"


def health_targets(env: dict[str, str] | None = None) -> tuple[str, str | None]:
    values = os.environ if env is None else env
    port = int(values.get("UVICORN_PORT", "8000"))
    tls_enabled = bool(
        values.get("UVICORN_SSL_CERTFILE", "").strip()
        and values.get("UVICORN_SSL_KEYFILE", "").strip()
    )
    scheme = "https" if tls_enabled else "http"
    internal = f"{scheme}://127.0.0.1:{port}{HEALTH_PATH}"
    explicit = values.get("HEISENBERG_PUBLIC_HEALTH_URL", "").strip()
    if explicit:
        return internal, explicit
    prefix = values.get("XRAY_SUBSCRIPTION_URL_PREFIX", "").strip().rstrip("/")
    if not prefix:
        return internal, None
    parsed = urlsplit(prefix)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("XRAY_SUBSCRIPTION_URL_PREFIX must be an absolute HTTP(S) URL")
    base_path = parsed.path.rstrip("/")
    public = urlunsplit(
        (parsed.scheme, parsed.netloc, f"{base_path}{HEALTH_PATH}", "", "")
    )
    return internal, public


def check(url: str, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Heisenberg-Health/1"})
    parsed = urlsplit(url)
    context = None
    if parsed.scheme == "https" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"health endpoint returned HTTP {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("internal", "public", "all"), default="all")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--print-targets", action="store_true")
    args = parser.parse_args()
    try:
        internal, public = health_targets()
        targets = []
        if args.mode in {"internal", "all"}:
            targets.append(("internal", internal))
        if args.mode in {"public", "all"} and public:
            targets.append(("public", public))
        if args.mode == "public" and not public:
            raise RuntimeError(
                "public health target is not configured; set "
                "HEISENBERG_PUBLIC_HEALTH_URL or XRAY_SUBSCRIPTION_URL_PREFIX"
            )
        if args.print_targets:
            print(json.dumps(dict(targets), separators=(",", ":")))
        for name, target in targets:
            print(f"health_check target={name} url={target}", file=sys.stderr)
            check(target, args.timeout)
    except (ValueError, RuntimeError, OSError, urllib.error.URLError) as exc:
        print(f"health_check_failed error={exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
