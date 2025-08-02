from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.core.gitops_utils import get_config_history, get_config_content

router = APIRouter()

@router.get("/history/{vendor}/{product}", response_class=HTMLResponse)
def history(request: Request, vendor: str, product: str):
    history = get_config_history(vendor, product)
    return JSONResponse(history)

@router.get("/history/config/{vendor}/{product}/{commit_hash}", response_class=HTMLResponse)
def get_config(request: Request, vendor: str, product: str, commit_hash: str):
    history = get_config_history(vendor, product)
    for entry in history:
        if entry['commit'].startswith(commit_hash):
            content = get_config_content(entry['filepath'], entry['commit'])
            return JSONResponse({"content": content, "file": entry['file'], "commit": entry['commit']})
    return JSONResponse({"error": "Not found"}, status_code=404)
