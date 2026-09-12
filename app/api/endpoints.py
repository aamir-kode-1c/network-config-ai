from fastapi import APIRouter, HTTPException, Request, Body
import shutil
import shutil
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from typing import Any
from app.core.config_generator import generate_config
from app.core.gitops import commit_config, rollback_config
from app.core.gitops_utils import get_config_history, get_config_content
from app.core.vendor_catalog import (
    catalog_as_product_mapping,
    discover_catalog,
    get_payload_templates,
    load_catalog,
)
from app.core.observability import increment, metric_value, set_gauge
import subprocess, sys, os

router = APIRouter()

class ConfigRequest(BaseModel):
    vendor: str = Field(min_length=1, max_length=64)
    product: str = Field(min_length=1, max_length=128)
    nb_payload: dict
    description: str = Field(default="", max_length=500)
    format: Literal["cli", "json", "xml", "yang"] = "cli"

    @field_validator("vendor", "product", "description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("text fields may not contain control characters")
        return value.strip()

    @field_validator("nb_payload")
    @classmethod
    def limit_payload(cls, value: dict) -> dict:
        if len(json.dumps(value, default=str)) > 64 * 1024:
            raise ValueError("nb_payload exceeds the 64 KiB limit")
        return value

class ConfigResponse(BaseModel):
    vendor: str
    config: Any

class RollbackResponse(BaseModel):
    vendor: str
    rolled_back_config: Any

@router.post("/generate-config", response_model=ConfigResponse, summary="Generate vendor-specific config", response_description="Generated config for the vendor")
def generate_vendor_config(request: ConfigRequest):
    """
    Generate a southbound configuration for a specific vendor based on a standard NB API payload.
    - **vendor**: The target vendor (nokia, ericsson, openet, cisco, etc)
    - **nb_payload**: The northbound API payload (as dict)
    - **description**: Optional description for version control
    - **format**: Output config format (cli, json, xml, yang)
    """
    try:
        config = generate_config(request.vendor, request.nb_payload, request.format, request.product)
        commit_config(request.vendor, config, request.description, request.product)
        increment("configuration_commits_total", {"vendor": request.vendor, "product": request.product, "status": "success"})
        return {"vendor": request.vendor, "config": config}
    except Exception as e:
        increment("configuration_commits_total", {"vendor": request.vendor, "product": request.product, "status": "failure"})
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run-agentic-update")
def run_agentic_update(request: Request):
    try:
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'agentic_update.py')], capture_output=True, text=True, check=True)
        return JSONResponse({"status": "Agentic update complete.", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return JSONResponse({"status": "Agentic update failed.", "error": e.stderr}, status_code=500)

@router.post("/push-to-sim")
async def push_to_sim(request: Request):
    import json
    import socket
    try:
        data = await request.json()
    except Exception:
        try:
            body = await request.body()
            data = json.loads(body.decode()) if body else None
        except Exception:
            data = None
    config = data.get('config') if data else None
    device = data.get('device') if data else None
    if not config or not device:
        return JSONResponse({"status": "No config or device provided."}, status_code=400)
    try:
        output_lines = []
        # SSH/CLI simulation (vendor-specific ports)
        if device == "cisco_asr9000_ssh":
            import httpx
            import os
            response = httpx.post(
                os.getenv("CISCO_AGENT_URL", "http://agent-cisco:5003") + "/push-config",
                json={"config": config},
                timeout=30,
            )
            push_status = "success" if response.is_success and response.json().get("status") == "success" else "failure"
            increment("simulated_deployments_total", {"vendor": "cisco", "agent": "cisco-agent", "device_id": "cisco-simulator", "transport": "agent", "status": push_status})
            return JSONResponse(response.json(), status_code=response.status_code)
        elif device == "nokia_7750sr_ssh":
            HOST, PORT = "localhost", 2223
        elif device == "ericsson_router6000_ssh":
            HOST, PORT = "localhost", 2224
        elif device == "huawei_ne40e_ssh":
            HOST, PORT = "localhost", 2225
        elif device == "openet_pm_ssh":
            HOST, PORT = "localhost", 2226
        else:
            HOST, PORT = None, None
        if HOST and PORT:
            with socket.create_connection((HOST, PORT), timeout=5) as s:
                s.recv(1024)  # Read initial prompt
                for line in config.splitlines():
                    s.sendall(line.encode() + b"\n")
                    resp = s.recv(1024)
                    output_lines.append(resp.decode().strip())
                s.sendall(b"exit\n")
                resp = s.recv(1024)
                output_lines.append(resp.decode().strip())
            vendor = device.split("_", 1)[0]
            increment("simulated_deployments_total", {"vendor": vendor, "agent": f"{vendor}-agent", "device_id": device, "transport": "ssh", "status": "success"})
            return JSONResponse({"status": f"Config pushed to simulated device ({device}).", "output": '\n'.join(output_lines)})
        # NETCONF simulation
        elif device in ["cisco_asr9000_netconf", "nokia_7750sr_netconf"]:
            # Simulate NETCONF session (in real usage, use ncclient or similar)
            output_lines.append("[NETCONF] Simulated push: " + config.replace('\n', ' | '))
            vendor = device.split("_", 1)[0]
            increment("simulated_deployments_total", {"vendor": vendor, "agent": f"{vendor}-agent", "device_id": device, "transport": "netconf", "status": "success"})
            return JSONResponse({"status": f"Config pushed via NETCONF to {device} (simulated)", "output": '\n'.join(output_lines)})
        else:
            vendor = device.split("_", 1)[0] if "_" in device else "unknown"
            increment("simulated_deployments_total", {"vendor": vendor, "agent": f"{vendor}-agent", "device_id": device, "transport": "unknown", "status": "failure"})
            return JSONResponse({"status": f"Unknown device/protocol: {device}"}, status_code=400)
    except Exception as e:
        increment("simulated_deployments_total", {"vendor": "unknown", "agent": "unknown", "device_id": "unknown", "transport": "unknown", "status": "failure"})
        return JSONResponse({"status": f"Push failed: {str(e)}"}, status_code=500)
        
@router.post("/rollback", response_model=RollbackResponse, summary="Rollback vendor config", response_description="Rolled back config for the vendor")
def rollback(request: ConfigRequest):
    """
    Rollback to the previous configuration for a specific vendor and product.
    - **vendor**: The target vendor (nokia, ericsson, openet, etc)
    - **product**: The specific product (e.g., 7750 SR, ASR 9000, etc)
    """
    try:
        config = rollback_config(request.vendor, request.product)
        increment("configuration_rollbacks_total", {"vendor": request.vendor, "status": "success"})
        attempts = metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "success"}) + metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "failure"})
        set_gauge("configuration_rollback_rate", float(metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "success"})) / attempts if attempts else 0, {"vendor": request.vendor})
        return {"vendor": request.vendor, "rolled_back_config": config}
    except Exception as e:
        increment("configuration_rollbacks_total", {"vendor": request.vendor, "status": "failure"})
        attempts = metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "success"}) + metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "failure"})
        set_gauge("configuration_rollback_rate", float(metric_value("configuration_rollbacks_total", {"vendor": request.vendor, "status": "success"})) / attempts if attempts else 0, {"vendor": request.vendor})
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/vendor-products")
def get_vendor_products():
    """
    Returns the vendor-product mapping from vendor_products.json as JSON.
    """
    try:
        return JSONResponse(content=catalog_as_product_mapping(load_catalog()))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/api/vendor-products/details")
def get_vendor_product_details():
    """Return product metadata, documentation links, formats, and payload examples."""
    try:
        return JSONResponse(content=load_catalog())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/vendor-products/{vendor}/{product}/payloads")
def get_vendor_product_payloads(vendor: str, product: str):
    """Return payload templates for every supported output format."""
    try:
        return JSONResponse(content=get_payload_templates(vendor, product))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class CatalogDiscoveryRequest(BaseModel):
    source_url: str


@router.post("/api/vendor-products/discover")
def discover_vendor_products(request: CatalogDiscoveryRequest):
    """Pull a normalized vendor/product catalog from a JSON documentation/API endpoint."""
    try:
        return JSONResponse(content=load_catalog(request.source_url))
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.post("/api/test-simulator")
def test_simulator(
    vendor: str = Body(...),
    product: str = Body(...),
    config: str = Body(...),
    format: str = Body("cli")
):
    """
    Simulate pushing the given config to the specified vendor/product simulator.
    Returns the simulated output/result.
    """
    try:
        # Dynamically import the correct vendor module
        import importlib
        vendor_mod = importlib.import_module(f"app.vendor.{vendor}")
        # Use the generate function as the simulator (for now, just echo config)
        # In a real scenario, you might have a 'simulate' function per vendor
        # Here, we just echo the config as the simulated output for demonstration
        output = f"[SIMULATOR] {vendor.title()} {product}:\n" + config
        return JSONResponse(content={"output": output, "status": "Simulated output generated."})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
