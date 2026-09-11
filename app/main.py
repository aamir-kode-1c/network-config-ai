from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api import endpoints
from app.api.history import router as history_router
from app.api.agents import router as agents_router
from app.api.production import router as production_router
from app.api.rag import router as rag_router
from app.core.config_generator import generate_config
from app.core.gitops import commit_config
from app.core.gitops_utils import get_config_history, get_config_content
from app.core.production import _connection
import os
from collections import Counter
from time import monotonic
from app.core.observability import current_trace_id, increment, set_gauge, snapshot, start_trace

app = FastAPI(
    title="AI-Based Config Manager",
    description="AI-powered tool for multi-vendor network configuration management with GitOps integration.",
    version="0.1.0"
)
_metrics = Counter()
_started_at = monotonic()


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    started = monotonic()
    trace_id = start_trace(request.headers.get("X-Trace-ID"))
    metric_path = request.url.path.replace("\\", "\\\\").replace('"', '\\"')
    try:
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        _metrics[f"http_requests_total{{path=\"{metric_path}\",status=\"{response.status_code}\"}}"] += 1
        return response
    except Exception:
        _metrics[f"http_requests_total{{path=\"{metric_path}\",status=\"500\"}}"] += 1
        raise
    finally:
        _metrics["http_request_duration_seconds_sum"] += monotonic() - started

# Mount static and templates
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(endpoints.router)
app.include_router(history_router)
app.include_router(agents_router)
app.include_router(production_router)
app.include_router(rag_router)


@app.get("/health/live", tags=["health"])
def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness():
    connection = None
    try:
        connection = _connection()
        connection.execute("SELECT 1").fetchone()
    except Exception as exc:
        return JSONResponse({"status": "not_ready", "detail": str(exc)}, status_code=503)
    finally:
        if connection is not None:
            connection.close()
    return {"status": "ready"}


@app.get("/metrics", response_class=PlainTextResponse, tags=["health"])
def metrics():
    lines = [
        "# HELP config_manager_uptime_seconds Process uptime in seconds",
        "# TYPE config_manager_uptime_seconds gauge",
        f"config_manager_uptime_seconds {monotonic() - _started_at:.3f}",
        "# HELP config_manager_http_request_duration_seconds_sum Total request duration",
        "# TYPE config_manager_http_request_duration_seconds_sum counter",
        f"config_manager_http_request_duration_seconds_sum {_metrics['http_request_duration_seconds_sum']:.6f}",
    ]
    lines.append("# TYPE http_requests_total counter")
    for key, value in {**snapshot(), **_metrics}.items():
        if key != "http_request_duration_seconds_sum":
            lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request},
    )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, vendor: str = "nokia"):
    history = get_config_history(vendor)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "history": history, "selected_vendor": vendor},
    )

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
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "config": config,
            "error": error,
            "history": history,
            "selected_vendor": vendor,
        },
    )

@app.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={"request": request},
    )

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
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "config": config,
            "error": error,
            "history": history,
            "selected_vendor": vendor,
        },
    )
