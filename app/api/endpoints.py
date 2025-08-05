from fastapi import APIRouter, HTTPException, Request, Body
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

VENDOR_PRODUCTS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../vendor_products.json'))
SIMULATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../simulators'))
AGENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../agents'))

# Helper: Mock authorized source fetch
def fetch_product_details(vendor, product):
    # In real-world, pull from API/db
    return {
        "vendor": vendor,
        "product": product,
        "description": f"Auto-generated details for {vendor} {product}",
        "features": ["feature1", "feature2"]
    }

# Helper: Create simulator stub
def create_simulator(vendor, product):
    os.makedirs(SIMULATOR_DIR, exist_ok=True)
    sim_file = os.path.join(SIMULATOR_DIR, f"sim_{vendor.lower()}_{product.lower().replace(' ', '_')}.py")
    if not os.path.exists(sim_file):
        with open(sim_file, 'w') as f:
            f.write(f"""# Simulator for {vendor} {product}\nclass {vendor.title()}{product.title().replace(' ', '')}Simulator:\n    def run(self):\n        return 'Simulating {vendor} {product}'\n""")
    return sim_file

# Helper: Create agent stub
def create_agent(vendor, product):
    os.makedirs(AGENT_DIR, exist_ok=True)
    agent_file = os.path.join(AGENT_DIR, f"agent_{vendor.lower()}_{product.lower().replace(' ', '_')}.py")
    if not os.path.exists(agent_file):
        with open(agent_file, 'w') as f:
            f.write(f"""# Agent for {vendor} {product}\nclass {vendor.title()}{product.title().replace(' ', '')}Agent:\n    def connect(self):\n        return 'Connecting to {vendor} {product} physical server'\n""")
    return agent_file

# Helper: Update vendor_products.json
def update_vendor_products(vendor, product):
    try:
        with open(VENDOR_PRODUCTS_PATH, 'r') as f:
            data = json.load(f)
    except Exception:
        data = {}
    if vendor.lower() in data:
        if product not in data[vendor.lower()]:
            data[vendor.lower()].append(product)
    else:
        data[vendor.lower()] = [product]
    with open(VENDOR_PRODUCTS_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    return data

@router.post("/add-vendor-product")
async def add_vendor_product(request: Request):
    try:
        body = await request.json()
        vendor = body.get('vendor')
        product = body.get('product')
        if not vendor or not product:
            return JSONResponse({"error": "Vendor and product required."}, status_code=400)
        # Step 1: Fetch product details (mocked)
        details = fetch_product_details(vendor, product)
        # Step 2: Create simulator
        sim_path = create_simulator(vendor, product)
        # Step 3: Create agent
        agent_path = create_agent(vendor, product)
        # Step 4: Update vendor_products.json
        updated_list = update_vendor_products(vendor, product)
        return JSONResponse({
            "status": f"Successfully added {vendor} {product}. Simulator and agent created.",
            "details": details,
            "simulator": sim_path,
            "agent": agent_path,
            "vendor_products": updated_list
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

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
            HOST, PORT = "localhost", 2222
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

@router.get("/vendor-products")
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
