from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.observability import increment
from app.core.config_generator import generate_config
from app.core.production import list_devices

router = APIRouter(prefix="/api/tests", tags=["test runner"])
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CISCO_RAG_CASE = "cisco_rag_change_test.py"
INVENTORY_CASE_PREFIX = "inventory:"

TEST_DESCRIPTIONS = {
    "test_e2e_change_execution.py": "Creates a vendor change, validates the candidate, requires separate approval, and executes simulated deployment.",
    "test_api.py": "Renders supported vendor/product configurations and validates invalid input handling.",
    "test_observability.py": "Checks labeled metrics and trace ID propagation.",
    "test_production_safety.py": "Checks authentication, device credential safety, NETCONF guards, and health endpoints.",
    "test_production_workflow.py": "Checks approval gating before a production deployment can proceed.",
    "test_rag.py": "Indexes a versioned document and verifies citation-rich retrieval.",
    "test_rollback_api.py": "Checks configuration rollback behavior across vendors.",
    "test_sbi_push.py": "Checks southbound Cisco simulator push behavior.",
    "test_vendor_catalog.py": "Checks catalog product names and payload format templates.",
}
E2E_TEST_FILE = "test_e2e_change_execution.py"


class TestCaseRequest(BaseModel):
    case: str


def _record_result(case: str, return_code: int) -> bool:
    passed = return_code == 0
    if case == CISCO_RAG_CASE:
        increment("ai_tool_invocations_total", {"tool": "local_knowledge_ingest"})
    increment(
        "test_cases_total",
        {"case": case, "status": "passed" if passed else "failed"},
    )
    if passed and case.startswith("tests/") and E2E_TEST_FILE in case:
        vendor_match = re.search(r"\[([^-]+)-", case)
        if vendor_match:
            vendor = vendor_match.group(1)
            increment(
                "production_change_deployments_total",
                {
                    "agent": f"{vendor}-agent",
                    "device_id": f"e2e-{vendor}-001",
                    "mode": "simulated",
                    "status": "success",
                    "vendor": vendor,
                },
            )
    return passed


def _pytest_cases() -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stdout + completed.stderr).strip())
    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    ]


@router.get("/cases")
def list_test_cases():
    try:
        cases = _pytest_cases()
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=f"Unable to collect test cases: {exc}") from exc
    test_cases = []
    for case in cases:
        test_file = case.split("/")[1].split("::")[0]
        test_name = case.split("::")[-1]
        is_e2e = test_file == E2E_TEST_FILE
        if is_e2e:
            vendor = case.rsplit("[", 1)[-1].split("-", 1)[0].title()
            display_name = f"Change E2E - {vendor} create, approve, and execute"
        else:
            display_name = test_name
        test_cases.append(
            {
                "id": case,
                "name": display_name,
                "kind": "pytest",
                "label": "change e2e" if is_e2e else None,
                "description": TEST_DESCRIPTIONS.get(test_file, "Runs a focused automated repository test."),
            }
        )
    test_cases += [
        {
            "id": f"{INVENTORY_CASE_PREFIX}{device.device_id}",
            "name": f"{device.device_id} ({device.vendor} / {device.product})",
            "kind": "inventory",
            "description": "Validates the registered device, resolves its vendor adapter, and renders a candidate without contacting the device.",
        }
        for device in list_devices()
    ]
    test_cases.append(
        {
            "id": CISCO_RAG_CASE,
            "name": "Cisco RAG read, store, change, and push",
            "kind": "workflow",
            "description": "Reads the Cisco simulator, stores the configuration in RAG, renders a change, and pushes it through the Cisco agent.",
        }
    )
    return {"cases": test_cases}


@router.post("/run")
def run_all_tests():
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests",
        ],
        [
            sys.executable,
            "cisco_rag_change_test.py",
            "--base-url",
            "http://127.0.0.1:8000",
            "--agent-url",
            os.getenv("CISCO_AGENT_URL", "http://agent-cisco:5003"),
        ],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        passed = _record_result(
            "full-suite" if command[-1] == "tests" else CISCO_RAG_CASE,
            completed.returncode,
        )
        results.append(
            {
                "command": " ".join(command),
                "passed": passed,
                "exit_code": completed.returncode,
                "output": output,
            }
        )
    return {
        "status": "passed" if all(result["passed"] for result in results) else "failed",
        "results": results,
    }


@router.post("/run-case")
def run_test_case(request: TestCaseRequest):
    if request.case.startswith(INVENTORY_CASE_PREFIX):
        device_id = request.case.removeprefix(INVENTORY_CASE_PREFIX)
        device = next((item for item in list_devices() if item.device_id == device_id), None)
        if device is None:
            raise HTTPException(status_code=404, detail="Unknown inventory device")
        try:
            config = generate_config(
                device.vendor,
                {
                    "interface": "GigabitEthernet0/1",
                    "ip": "192.0.2.1",
                    "subnet": "24",
                    "description": f"Inventory smoke test for {device_id}",
                    "admin_state": "up",
                },
                "cli",
                device.product,
            )
            passed = bool(config.strip())
            output = f"Inventory record validated: {device_id}\nProduct: {device.product}\nCandidate rendered:\n{config}"
        except (KeyError, ValueError) as exc:
            passed = False
            output = f"Inventory test failed for {device_id}: {exc}"
        _record_result(request.case, 0 if passed else 1)
        return {
            "status": "passed" if passed else "failed",
            "results": [{
                "command": f"inventory smoke test {device_id}",
                "passed": passed,
                "exit_code": 0 if passed else 1,
                "output": output,
            }],
        }
    if request.case == CISCO_RAG_CASE:
        command = [
            sys.executable,
            CISCO_RAG_CASE,
            "--base-url",
            "http://127.0.0.1:8000",
            "--agent-url",
            os.getenv("CISCO_AGENT_URL", "http://agent-cisco:5003"),
        ]
    else:
        try:
            cases = _pytest_cases()
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            raise HTTPException(status_code=500, detail=f"Unable to collect test cases: {exc}") from exc
        if request.case not in cases:
            raise HTTPException(status_code=404, detail="Unknown test case")
        command = [sys.executable, "-m", "pytest", "-q"]
        if E2E_TEST_FILE in request.case:
            command.append("-s")
        command.append(request.case)
    try:
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "failed",
            "results": [{
                "command": " ".join(command),
                "passed": False,
                "exit_code": 124,
                "output": f"Test timed out after 180 seconds: {exc}",
            }],
        }
    output = (completed.stdout + completed.stderr).strip()
    passed = _record_result(request.case, completed.returncode)
    return {
        "status": "passed" if passed else "failed",
        "results": [{
            "command": " ".join(command),
            "passed": passed,
            "exit_code": completed.returncode,
            "output": output,
        }],
    }
