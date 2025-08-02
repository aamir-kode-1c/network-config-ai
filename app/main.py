from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api import endpoints
from app.api.history import router as history_router
from app.api.agents import router as agents_router
from app.core.config_generator import generate_config
from app.core.gitops import commit_config
from app.core.gitops_utils import get_config_history, get_config_content
import os

app = FastAPI(
    title="AI-Based Config Manager",
    description="AI-powered tool for multi-vendor network configuration management with GitOps integration.",
    version="0.1.0"
)

# Mount static and templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(endpoints.router)
app.include_router(history_router)
app.include_router(agents_router)

from fastapi.responses import JSONResponse


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, vendor: str = "nokia"):
    history = get_config_history(vendor)
    return templates.TemplateResponse("dashboard.html", {"request": request, "history": history, "selected_vendor": vendor})

@app.post("/dashboard", response_class=HTMLResponse)
def dashboard_post(
    request: Request,
    vendor: str = Form(...),
    nb_payload: str = Form(...),
    description: str = Form("")
):
    config = None
    error = None
    try:
        import json
        payload = json.loads(nb_payload)
        config = generate_config(vendor, payload)
        commit_config(vendor, config, description)
    except Exception as e:
        error = str(e)
    history = get_config_history(vendor)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "config": config, "error": error, "history": history, "selected_vendor": vendor}
    )

@app.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request):
    return templates.TemplateResponse("agents.html", {"request": request})

@app.post("/dashboard/rollback/{commit_hash}", response_class=HTMLResponse)
def dashboard_rollback(request: Request, commit_hash: str, vendor: str = Form(...)):
    from app.core.gitops_utils import get_config_history, get_config_content
    history = get_config_history(vendor)
    config = None
    error = None
    for entry in history:
        if entry['commit'].startswith(commit_hash):
            config = get_config_content(entry['filepath'], entry['commit'])
            if config is not None:
                # Save rollback as a new commit
                from app.core.gitops import commit_config
                commit_config(vendor, config, f"Rollback to commit {commit_hash[:7]}")
            else:
                error = f"Config file not found for commit {commit_hash[:7]}"
            break
    else:
        error = f"Commit {commit_hash[:7]} not found in history."
    history = get_config_history(vendor)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "config": config, "error": error, "history": history, "selected_vendor": vendor}
    )
