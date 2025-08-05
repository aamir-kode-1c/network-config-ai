from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse
from typing import Dict, List
import time

router = APIRouter()

import os
import json
AGENTS_REGISTRY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../agents_registry.json'))

def load_agents_registry():
    if os.path.exists(AGENTS_REGISTRY_PATH):
        try:
            with open(AGENTS_REGISTRY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_agents_registry(registry):
    with open(AGENTS_REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)

# Persistent agent registry
agents_registry: Dict[str, Dict] = load_agents_registry()

@router.post("/api/agents/register")
def register_agent(agent: dict = Body(...)):
    vendor = agent.get("vendor")
    endpoint = agent.get("endpoint")
    token = agent.get("token", None)
    if not vendor or not endpoint:
        return JSONResponse({"status": "Missing vendor or endpoint"}, status_code=400)
    agent_entry = {
        "endpoint": endpoint,
        "token": token,
        "status": "Online",
        "last_sync": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if vendor in agents_registry:
        # Prevent duplicates for same endpoint
        if not any(a['endpoint'] == endpoint for a in agents_registry[vendor]):
            agents_registry[vendor].append(agent_entry)
    else:
        agents_registry[vendor] = [agent_entry]
    save_agents_registry(agents_registry)
    return {"status": "registered", "vendor": vendor}

@router.get("/api/agents/list")
def list_agents():
    agents_registry.update(load_agents_registry())  # reload in case of external changes
    agent_list = []
    for vendor, agents in agents_registry.items():
        for agent in agents:
            entry = {"vendor": vendor}
            entry.update(agent)
            agent_list.append(entry)
    return agent_list

from fastapi import Query

@router.delete("/api/agents/delete")
def delete_agent(vendor: str = Query(...), endpoint: str = Query(...)):
    agents_registry.update(load_agents_registry())
    if vendor in agents_registry:
        original_count = len(agents_registry[vendor])
        agents_registry[vendor] = [a for a in agents_registry[vendor] if a['endpoint'] != endpoint]
        if not agents_registry[vendor]:
            del agents_registry[vendor]
        save_agents_registry(agents_registry)
        if len(agents_registry.get(vendor, [])) < original_count:
            return {"status": "deleted", "vendor": vendor, "endpoint": endpoint}
    return JSONResponse({"status": "not found", "vendor": vendor, "endpoint": endpoint}, status_code=404)

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
