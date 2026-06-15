#!/usr/bin/env python3
"""Minimal, dependency-free webhook forwarder for Cognis findings.

Reads JSON findings on stdin and POSTs them to a URL (SIEM/Slack/Jira bridge).
Usage:  <tool> scan . --format json | python integrations/webhook.py --url URL
"""
from __future__ import annotations

import argparse
import sys
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(
        description="POST milstdlint JSON findings to a webhook URL."
    )
    ap.add_argument("--url", required=True, help="Destination URL (http/https).")
    ap.add_argument(
        "--header", action="append", default=[],
        help="Extra request header in 'Key: Value' form (repeatable).",
    )
    args = ap.parse_args()

    # Validate URL scheme before making a network call.
    if not args.url.startswith(("http://", "https://")):
        print(
            f"webhook: invalid URL {args.url!r}; must start with http:// or https://",
            file=sys.stderr,
        )
        return 2

    try:
        payload = sys.stdin.read().encode("utf-8")
    except OSError as exc:
        print(f"webhook: failed to read stdin: {exc}", file=sys.stderr)
        return 2

    if not payload.strip():
        print("webhook: stdin is empty; nothing to post", file=sys.stderr)
        return 2

    req = urllib.request.Request(args.url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    for h in args.header:
        if ":" not in h:
            print(
                f"webhook: malformed --header value {h!r}; expected 'Key: Value'",
                file=sys.stderr,
            )
            return 2
        k, _, v = h.partition(":")
        req.add_header(k.strip(), v.strip())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"posted {len(payload)} bytes -> {r.status}")
        return 0
    except OSError as exc:
        print(f"webhook: network error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
