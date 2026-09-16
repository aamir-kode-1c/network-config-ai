"""Small, dependency-free API key and role based access control helpers."""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass
from typing import Mapping

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthContext:
    actor: str
    role: str


ROLE_PERMISSIONS: Mapping[str, frozenset[str]] = {
    "operator": frozenset({"changes:read", "changes:create", "devices:read", "knowledge:read"}),
    "approver": frozenset({"changes:read", "changes:approve", "devices:read", "knowledge:read"}),
    "deployer": frozenset({"changes:read", "changes:deploy", "devices:read", "knowledge:read"}),
    "admin": frozenset(
        {
            "changes:read",
            "changes:create",
            "changes:approve",
            "changes:deploy",
            "devices:read",
            "devices:write", "knowledge:read", "knowledge:write",
        }
    ),
}


def _configured_credentials() -> list[tuple[str, str, str]]:
    """Return (key, actor, role) entries without logging any secrets."""
    raw = os.getenv("CONFIG_MANAGER_API_KEYS")
    if raw:
        try:
            values = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=503, detail="API key configuration is invalid") from exc
        if not isinstance(values, dict):
            raise HTTPException(status_code=503, detail="API key configuration is invalid")
        entries = []
        for key, value in values.items():
            if isinstance(value, str):
                actor, role = value, "operator"
            elif isinstance(value, dict):
                actor = str(value.get("actor", "api-client"))
                role = str(value.get("role", "operator")).lower()
            else:
                continue
            entries.append((str(key), actor, role))
        return entries
    key = os.getenv("CONFIG_MANAGER_API_KEY")
    if not key:
        return []
    return [
        (
            key,
            os.getenv("CONFIG_MANAGER_API_ACTOR", "api-client"),
            os.getenv("CONFIG_MANAGER_API_ROLE", "operator").lower(),
        )
    ]


def require_auth(
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
    permission: str = "changes:read",
) -> AuthContext:
    """Authenticate an API request and enforce a configured role permission.

    Authentication is fail-closed: production endpoints cannot be used until an
    API key is explicitly configured.  Actor and role are never accepted from
    an untrusted role header.
    """
    credentials = _configured_credentials()
    if not credentials:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    match = next(
        (
            (actor, role)
            for key, actor, role in credentials
            if x_api_key and hmac.compare_digest(key, x_api_key)
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=401, detail="A valid X-API-Key is required")
    actor, role = match
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=503, detail="API role configuration is invalid")
    if permission not in ROLE_PERMISSIONS[role]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if x_actor and x_actor != actor:
        raise HTTPException(status_code=403, detail="X-Actor does not match the API key")
    return AuthContext(actor=actor, role=role)
