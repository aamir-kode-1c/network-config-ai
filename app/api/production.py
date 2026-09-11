from fastapi import APIRouter, Header, HTTPException

from app.core.production import (
    ChangeCreate,
    ChangeRecord, DeviceCreate, DeviceRecord,
    audit_events,
    approve_change,
    create_change,
    deploy_change,
    get_change,
    get_device,
    list_devices,
    register_device,
    reject_change,
    update_device,
)
from app.core.security import AuthContext, require_auth

router = APIRouter(prefix="/api/v1", tags=["production workflow"])


def _auth(x_actor: str | None, x_api_key: str | None, permission: str) -> AuthContext:
    return require_auth(x_api_key=x_api_key, x_actor=x_actor, permission=permission)


@router.post("/changes", response_model=ChangeRecord, status_code=201)
def create_production_change(
    request: ChangeCreate,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    auth = _auth(x_actor, x_api_key, "changes:create")
    if request.requested_by != auth.actor:
        raise HTTPException(status_code=403, detail="requested_by must match the authenticated actor")
    try:
        return create_change(request)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/changes/{change_id}", response_model=ChangeRecord)
def read_production_change(
    change_id: str,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    # Authentication is intentionally required even for candidate config reads.
    # The function call is kept separate to preserve the existing route shape.
    _auth(x_actor, x_api_key, "changes:read")
    try:
        return get_change(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/changes/{change_id}/approve", response_model=ChangeRecord)
def approve_production_change(
    change_id: str,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    actor = _auth(x_actor, x_api_key, "changes:approve").actor
    try:
        return approve_change(change_id, actor)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 409, detail=str(exc)) from exc


@router.post("/changes/{change_id}/deploy", response_model=ChangeRecord)
def deploy_production_change(
    change_id: str,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    actor = _auth(x_actor, x_api_key, "changes:deploy").actor
    try:
        return deploy_change(change_id, actor)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 409, detail=str(exc)) from exc


@router.post("/changes/{change_id}/reject", response_model=ChangeRecord)
def reject_production_change(
    change_id: str,
    reason: str = "",
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    actor = _auth(x_actor, x_api_key, "changes:approve").actor
    try:
        return reject_change(change_id, actor, reason)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 409, detail=str(exc)) from exc


@router.get("/changes/{change_id}/audit")
def read_change_audit(
    change_id: str,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _auth(x_actor, x_api_key, "changes:read")
    try:
        get_change(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return audit_events(change_id)


@router.post("/devices", response_model=DeviceRecord, status_code=201)
def create_device(
    request: DeviceCreate,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _auth(x_actor, x_api_key, "devices:write")
    try:
        return register_device(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/devices", response_model=list[DeviceRecord])
def read_devices(
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _auth(x_actor, x_api_key, "devices:read")
    return list_devices()


@router.get("/devices/{device_id}", response_model=DeviceRecord)
def read_device(
    device_id: str,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _auth(x_actor, x_api_key, "devices:read")
    try:
        return get_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/devices/{device_id}", response_model=DeviceRecord)
def replace_device(
    device_id: str,
    request: DeviceCreate,
    x_actor: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    _auth(x_actor, x_api_key, "devices:write")
    try:
        return update_device(device_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
