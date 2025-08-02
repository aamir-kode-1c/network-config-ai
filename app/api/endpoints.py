from fastapi import APIRouter, HTTPException, Request, Body
import shutil
import shutil
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel
from typing import Any
from app.core.config_generator import generate_config
from app.core.gitops import commit_config, rollback_config
from app.core.gitops_utils import get_config_history, get_config_content
import subprocess, sys, os

router = APIRouter()

class ConfigRequest(BaseModel):
    vendor: str
    product: str
    nb_payload: dict
    description: str = ""
    format: str = "cli"  # New: allow format selection (cli, json, xml, yang)

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
        return {"vendor": request.vendor, "config": config}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run-agentic-update")
def run_agentic_update(request: Request):
    try:
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'agentic_update.py')], capture_output=True, text=True, check=True)
        return JSONResponse({"status": "Agentic update complete.", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return JSONResponse({"status": "Agentic update failed.", "error": e.stderr}, status_code=500)

@router.post("/push-to-sim")
def push_to_sim(request: Request):
    import json
    import socket
    try:
        data = request.json() if hasattr(request, 'json') else None
    except Exception:
        try:
            body = request.body() if hasattr(request, 'body') else None
            data = json.loads(body.decode()) if body else None
        except Exception:
            data = None
    config = data.get('config') if data else None
    device = data.get('device') if data else None
    if not config or not device:
        return JSONResponse({"status": "No config or device provided."}, status_code=400)
    try:
        output_lines = []
        # SSH/CLI simulation (default)
        if device == "cisco_asr9000_ssh" or device == "ericsson_router6000_cli":
            HOST, PORT = "localhost", 2222
            with socket.create_connection((HOST, PORT), timeout=5) as s:
                s.recv(1024)  # Read initial prompt
                for line in config.splitlines():
                    s.sendall(line.encode() + b"\n")
                    resp = s.recv(1024)
                    output_lines.append(resp.decode().strip())
                s.sendall(b"exit\n")
                resp = s.recv(1024)
                output_lines.append(resp.decode().strip())
            return JSONResponse({"status": f"Config pushed to simulated device ({device}).", "output": '\n'.join(output_lines)})
        # NETCONF simulation
        elif device in ["cisco_asr9000_netconf", "nokia_7750sr_netconf"]:
            # Simulate NETCONF session (in real usage, use ncclient or similar)
            output_lines.append("[NETCONF] Simulated push: " + config.replace('\n', ' | '))
            return JSONResponse({"status": f"Config pushed via NETCONF to {device} (simulated)", "output": '\n'.join(output_lines)})
        else:
            return JSONResponse({"status": f"Unknown device/protocol: {device}"}, status_code=400)
    except Exception as e:
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
        return {"vendor": request.vendor, "rolled_back_config": config}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/vendor-products")
def get_vendor_products():
    """
    Returns the vendor-product mapping from vendor_products.json as JSON.
    """
    try:
        import os
        vendor_file = os.path.join(os.getcwd(), "vendor_products.json")
        with open(vendor_file, "r") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

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
