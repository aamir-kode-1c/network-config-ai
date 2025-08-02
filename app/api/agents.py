from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from typing import Dict, List
import time

router = APIRouter()

# In-memory agent registry (replace with DB for production)
agents_registry: Dict[str, Dict] = {}

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
        "status": "Online",
        "last_sync": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"status": "registered", "vendor": vendor}

@router.get("/api/agents/list")
def list_agents():
    # Return all registered agents
    return [{"vendor": v, **info} for v, info in agents_registry.items()]

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
        agent["last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if resp.ok:
            return resp.json()
        else:
            return JSONResponse({"status": f"Agent error: {resp.status_code}", "output": resp.text}, status_code=502)
    except Exception as e:
        return JSONResponse({"status": f"Push failed: {str(e)}"}, status_code=500)
