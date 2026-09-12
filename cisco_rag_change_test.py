"""Read, index, change, and deploy the Cisco simulator configuration.

The workflow is:
    Cisco agent -> current running configuration
    local RAG store -> current configuration with citation metadata
    orchestrator -> vendor-specific candidate change
    Cisco agent -> Cisco simulator

Example:
    python cisco_rag_change_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.rag import ingest_text


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url.rstrip("/"),
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError) as exc:
        detail = exc.read().decode(errors="replace") if isinstance(exc, HTTPError) else str(exc)
        raise RuntimeError(f"{method} {url} failed: {detail}") from exc


def run(args: argparse.Namespace) -> None:
    agent_url = args.agent_url.rstrip("/")
    base_url = args.base_url.rstrip("/")

    print("[1/5] Reading current Cisco simulator configuration")
    current = request_json(f"{agent_url}/current-config")
    if current.get("status") != "success":
        raise RuntimeError(f"Cisco agent could not read configuration: {current}")
    running_config = current.get("config", "").strip()
    if not running_config:
        running_config = "! Cisco simulator has an empty running configuration"
    print(running_config)

    print("[2/5] Storing current configuration in the local RAG knowledge base")
    indexed = ingest_text(
        "cisco",
        "ASR 9000",
        running_config,
        "cisco-simulator://running-config",
        args.version,
    )
    print(f"      {indexed['status']}: {indexed['document_id']}")

    print("[3/5] Creating a change based on the observed configuration")
    candidate_request = {
        "vendor": "cisco",
        "product": "ASR 9000",
        "format": "cli",
        "description": args.description,
        "nb_payload": {
            "interface": args.interface,
            "ip": args.ip,
            "subnet": args.subnet,
            "description": args.description,
            "admin_state": "up",
        },
    }
    candidate = request_json(f"{base_url}/generate-config", "POST", candidate_request)
    config = candidate.get("config")
    if not config:
        raise RuntimeError(f"Orchestrator did not return a candidate: {candidate}")
    print(config)

    if args.no_push:
        print("[4/5] Push skipped (--no-push)")
        print("[5/5] TEST PASSED")
        return

    print("[4/5] Pushing the change through the Cisco agent")
    result = request_json(
        f"{base_url}/push-to-sim",
        "POST",
        {"device": "cisco_asr9000_ssh", "config": config},
    )
    if result.get("status") != "success":
        raise RuntimeError(f"Cisco simulator push failed: {result}")
    print(result.get("message", "Configuration pushed"))

    print("[5/5] TEST PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--agent-url", default="http://localhost:5003")
    parser.add_argument("--interface", default="GigabitEthernet0/10")
    parser.add_argument("--ip", default="192.0.2.10")
    parser.add_argument("--subnet", default="255.255.255.0")
    parser.add_argument("--description", default="RAG-backed Cisco simulator change")
    parser.add_argument("--version", default="runtime")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()
    try:
        run(args)
    except (RuntimeError, ValueError) as exc:
        print(f"TEST FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
