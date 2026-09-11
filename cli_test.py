"""Run an end-to-end Cisco simulator test from the command line.

Example:
    python cli_test.py
    python cli_test.py --base-url http://localhost:8000 --interface GigabitEthernet0/2
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(base_url: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError) as exc:
        detail = exc.read().decode(errors="replace") if isinstance(exc, HTTPError) else str(exc)
        raise RuntimeError(f"{method} {path} failed: {detail}") from exc


def run_test(args: argparse.Namespace) -> None:
    print(f"[1/4] Checking {args.base_url}/health/ready")
    health = request_json(args.base_url, "/health/ready")
    if health.get("status") != "ready":
        raise RuntimeError(f"Application is not ready: {health}")
    print("      PASS: application is ready")

    payload = {
        "vendor": "cisco",
        "product": "ASR 9000",
        "format": "cli",
        "description": "CLI end-to-end simulator test",
        "nb_payload": {
            "interface": args.interface,
            "ip": args.ip,
            "subnet": args.subnet,
            "description": args.description,
            "admin_state": "up",
        },
    }
    print("[2/4] Generating Cisco candidate configuration")
    candidate = request_json(args.base_url, "/generate-config", "POST", payload)
    config = candidate.get("config")
    if not config:
        raise RuntimeError(f"Candidate response did not contain config: {candidate}")
    print("      PASS: candidate generated")
    print(config)

    if args.no_push:
        print("[3/4] Push skipped (--no-push)")
        print("[4/4] TEST PASSED")
        return

    print("[3/4] Pushing candidate through Cisco agent to simulator")
    result = request_json(
        args.base_url,
        "/push-to-sim",
        "POST",
        {"device": "cisco_asr9000_ssh", "config": config},
    )
    if result.get("status") != "success":
        raise RuntimeError(f"Device push failed: {result}")
    print(f"      PASS: {result.get('message', 'configuration pushed')}")
    print(result.get("output", "").strip())
    print("[4/4] TEST PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Cisco simulator end-to-end test.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--interface", default="GigabitEthernet0/2")
    parser.add_argument("--ip", default="192.0.2.10")
    parser.add_argument("--subnet", default="255.255.255.0")
    parser.add_argument("--description", default="cli end-to-end test")
    parser.add_argument("--no-push", action="store_true", help="Generate the candidate without sending it")
    args = parser.parse_args()
    try:
        run_test(args)
    except (RuntimeError, ValueError) as exc:
        print(f"TEST FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
