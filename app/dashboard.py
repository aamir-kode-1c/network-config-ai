from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # Show a form for NB API input and a section for output/config
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.post("/dashboard", response_class=HTMLResponse)
def dashboard_post(request: Request):
    # This will be implemented in main.py as a POST handler
    pass
