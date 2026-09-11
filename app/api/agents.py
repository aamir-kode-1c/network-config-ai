from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from typing import Dict, List
import time
from urllib.request import urlopen

router = APIRouter()

# In-memory agent registry (replace with DB for production)
agents_registry: Dict[str, Dict] = {
    "cisco": {"endpoint": "agent-cisco:5003", "device": "Cisco simulator", "token": None},
    "nokia": {"endpoint": "agent-nokia:5001", "device": "Nokia test connector", "token": None},
    "ericsson": {"endpoint": "agent-ericsson:5004", "device": "Ericsson test connector", "token": None},
    "openet": {"endpoint": "agent-openet:5005", "device": "Openet test connector", "token": None},
}


def _probe_agent(vendor: str, info: Dict) -> Dict:
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with urlopen(f"http://{info['endpoint']}/openapi.json", timeout=3) as response:
            status = "Connected" if 200 <= response.status < 300 else "Disconnected"
            error = None
    except OSError as exc:
        status, error = "Disconnected", str(exc)
    info.update({"status": status, "last_check": checked_at, "error": error})
    return {"vendor": vendor, **info}

@router.post("/api/agents/register")
def register_agent(agent: dict = Body(...)):
    vendor = agent.get("vendor")
    endpoint = agent.get("endpoint")
    token = agent.get("token", None)
    if not vendor or not endpoint:
        return JSONResponse({"status": "Missing vendor or endpoint"}, status_code=400)
    agents_registry[vendor] = {
        "endpoint": endpoint,
        "token": token,
        "device": agent.get("device", "Unassigned device"),
        "status": "Unknown",
        "last_check": None,
        "error": None,
    }
    return {"status": "registered", "vendor": vendor}

@router.get("/api/agents/list")
def list_agents():
    return [_probe_agent(vendor, info) for vendor, info in agents_registry.items()]


@router.get("/api/agents/status")
def agent_status():
    return list_agents()

@router.post("/api/agents/push")
def push_to_agent(vendor: str = Body(...), config: str = Body(...)):
    import requests
    agent = agents_registry.get(vendor)
    if not agent:
        return JSONResponse({"status": "No agent registered for vendor"}, status_code=404)
    endpoint = agent["endpoint"]
    token = agent.get("token")
    url = f"http://{endpoint}/push-config"
    try:
        payload = {"config": config}
        if token:
            payload["token"] = token
        resp = requests.post(url, json=payload, timeout=10)
        agent["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if resp.ok:
            return resp.json()
        else:
            return JSONResponse({"status": f"Agent error: {resp.status_code}", "output": resp.text}, status_code=502)
    except Exception as e:
        return JSONResponse({"status": f"Push failed: {str(e)}"}, status_code=500)
