"""Production-oriented intent, adapter, workflow, and audit primitives."""

from __future__ import annotations

import difflib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
import ipaddress
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config_generator import generate_config
from app.core.vendor_catalog import get_product_details
from app.core.netconf_worker import NetconfDeploymentError, deploy_netconf
from app.core.observability import alert_failed_change, increment, set_gauge


ChangeStatus = Literal[
    "draft", "validated", "pending_approval", "approved", "deploying",
    "completed", "deployment_failed", "rejected", "rolled_back",
]
DEFAULT_DB_PATH = os.path.join("configs", "network_config_manager.db")


class DeviceIntent(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    vendor: str = Field(min_length=1, max_length=64)
    product: str = Field(min_length=1, max_length=128)
    change_type: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any] = Field(min_length=1)
    output_format: Literal["cli", "json", "xml", "yang"] = "cli"
    reason: str = Field(min_length=1, max_length=500)
    ticket_id: str | None = Field(default=None, max_length=128)
    environment: Literal["lab", "staging", "production"] = "lab"
    transport: Literal["simulated", "netconf", "restconf", "ssh"] = "simulated"
    management_address: str | None = None
    port: int = Field(default=830, ge=1, le=65535)
    credentials_env: str = Field(default="CONFIG_MANAGER_DEVICE_CREDENTIALS", min_length=1)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    restconf_path: str = "/restconf/data"
    tls_verify: bool = True

    @field_validator("vendor")
    @classmethod
    def normalize_vendor(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("device_id", "change_type", "reason", "credentials_env", "restconf_path")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("text fields may not contain control characters")
        return value.strip()

    @field_validator("management_address")
    @classmethod
    def validate_management_address(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value or len(value) > 253 or any(char.isspace() for char in value):
            raise ValueError("management_address must be a host or IP address")
        try:
            ipaddress.ip_address(value)
        except ValueError:
            labels = value.rstrip(".").split(".")
            if (
                not labels
                or any(
                    not re.fullmatch(r"[A-Za-z0-9-]{1,63}", label)
                    or label.startswith("-")
                    or label.endswith("-")
                    for label in labels
                )
            ):
                raise ValueError("management_address must be a valid host or IP address")
        return value

    @field_validator("credentials_env")
    @classmethod
    def validate_credentials_env(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", value):
            raise ValueError("credentials_env must be an environment variable name")
        return value

    @field_validator("restconf_path")
    @classmethod
    def validate_restconf_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//") or "\x00" in value:
            raise ValueError("restconf_path must be an absolute path")
        return value

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, default=str)) > 64 * 1024:
            raise ValueError("payload exceeds the 64 KiB limit")
        return value


class ChangeCreate(DeviceIntent):
    requested_by: str = Field(min_length=1, max_length=256)


class DeviceCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    vendor: str = Field(min_length=1, max_length=64)
    product: str = Field(min_length=1, max_length=128)
    management_address: str
    username: str = Field(min_length=1, max_length=128)
    password_env: str = Field(min_length=1, max_length=128, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    port: int = Field(default=830, ge=1, le=65535)
    timeout: int = Field(default=30, ge=1, le=300)
    hostkey_verify: bool = True
    hostkey: str | None = Field(default=None, max_length=4096)
    enabled: bool = True

    @field_validator("vendor")
    @classmethod
    def normalize_device_vendor(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("management_address")
    @classmethod
    def validate_device_address(cls, value: str) -> str:
        return DeviceIntent.validate_management_address(value)  # type: ignore[return-value]

    @field_validator("hostkey")
    @classmethod
    def require_hostkey(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("hostkey_verify") and not value:
            raise ValueError("hostkey is required when hostkey_verify is enabled")
        return value


class DeviceRecord(DeviceCreate):
    created_at: str
    updated_at: str


class ChangeRecord(BaseModel):
    id: str
    status: ChangeStatus
    intent: ChangeCreate
    candidate_config: str | None = None
    diff: str | None = None
    approved_by: str | None = None
    created_at: str
    updated_at: str


class Adapter:
    def __init__(self, vendor: str, product: str):
        details = get_product_details(vendor, product)
        self.vendor = vendor
        self.product = details["name"]
        self.formats = details["formats"]

    def render(self, intent: DeviceIntent) -> str:
        if intent.output_format not in self.formats:
            raise ValueError(f"{intent.output_format} is not supported for {self.vendor}/{self.product}")
        return generate_config(self.vendor, intent.payload, intent.output_format, self.product)

    def validate(self, intent: DeviceIntent, config: str) -> None:
        if intent.environment == "production" and not intent.ticket_id:
            raise ValueError("A ticket_id is required for production changes")
        if not config.strip():
            raise ValueError("Generated candidate configuration is empty")


def get_adapter(vendor: str, product: str) -> Adapter:
    return Adapter(vendor, product)


def _connection() -> sqlite3.Connection:
    db_path = os.getenv("CONFIG_DB_PATH", DEFAULT_DB_PATH)
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS changes (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, intent_json TEXT NOT NULL,
            candidate_config TEXT, diff TEXT, approved_by TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY, vendor TEXT NOT NULL, product TEXT NOT NULL,
            management_address TEXT NOT NULL, username TEXT NOT NULL,
            password_env TEXT NOT NULL, port INTEGER NOT NULL, timeout INTEGER NOT NULL,
            hostkey_verify INTEGER NOT NULL, hostkey TEXT, enabled INTEGER NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, change_id TEXT NOT NULL,
            actor TEXT NOT NULL, action TEXT NOT NULL, details_json TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    connection.commit()
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(connection: sqlite3.Connection, change_id: str, actor: str, action: str, details: dict[str, Any] | None = None) -> None:
    connection.execute(
        "INSERT INTO audit_events(change_id, actor, action, details_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (change_id, actor, action, json.dumps(details or {}), _now()),
    )


def _device_record(row: sqlite3.Row) -> DeviceRecord:
    return DeviceRecord(
        device_id=row["device_id"], vendor=row["vendor"], product=row["product"],
        management_address=row["management_address"], username=row["username"],
        password_env=row["password_env"], port=row["port"], timeout=row["timeout"],
        hostkey_verify=bool(row["hostkey_verify"]), hostkey=row["hostkey"],
        enabled=bool(row["enabled"]), created_at=row["created_at"], updated_at=row["updated_at"],
    )


def register_device(request: DeviceCreate) -> DeviceRecord:
    timestamp = _now()
    connection = _connection()
    try:
        connection.execute(
            """INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.device_id, request.vendor, request.product,
                request.management_address, request.username, request.password_env,
                request.port, request.timeout, int(request.hostkey_verify),
                request.hostkey, int(request.enabled), timestamp, timestamp,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise ValueError(f"Device already exists: {request.device_id}") from exc
    finally:
        connection.close()
    return get_device(request.device_id)


def get_device(device_id: str) -> DeviceRecord:
    connection = _connection()
    row = connection.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    connection.close()
    if row is None:
        raise KeyError(f"Unknown device: {device_id}")
    return _device_record(row)


def update_device(device_id: str, request: DeviceCreate) -> DeviceRecord:
    if request.device_id != device_id:
        raise ValueError("device_id in path and body must match")
    timestamp = _now()
    connection = _connection()
    cursor = connection.execute(
        """UPDATE devices SET vendor=?, product=?, management_address=?, username=?,
           password_env=?, port=?, timeout=?, hostkey_verify=?, hostkey=?, enabled=?, updated_at=?
           WHERE device_id=?""",
        (
            request.vendor, request.product, request.management_address, request.username,
            request.password_env, request.port, request.timeout, int(request.hostkey_verify),
            request.hostkey, int(request.enabled), timestamp, device_id,
        ),
    )
    if cursor.rowcount != 1:
        connection.rollback()
        connection.close()
        raise KeyError(f"Unknown device: {device_id}")
    connection.commit()
    connection.close()
    return get_device(device_id)


def list_devices() -> list[DeviceRecord]:
    connection = _connection()
    rows = connection.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
    connection.close()
    return [_device_record(row) for row in rows]


def create_change(request: ChangeCreate) -> ChangeRecord:
    try:
        adapter = get_adapter(request.vendor, request.product)
        candidate = adapter.render(request)
        adapter.validate(request, candidate)
    except (KeyError, ValueError):
        increment("config_validation_failures_total", {"vendor": request.vendor, "product": request.product})
        raise
    change_id = f"chg-{uuid.uuid4().hex[:12]}"
    timestamp = _now()
    diff = "\n".join(
        difflib.unified_diff(
            [],
            candidate.splitlines(),
            fromfile="running-config",
            tofile="candidate-config",
            lineterm="",
        )
    )
    connection = _connection()
    _audit(connection, change_id, request.requested_by, "created", {"change_type": request.change_type})
    connection.execute(
        "INSERT INTO changes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (change_id, "pending_approval", request.model_dump_json(), candidate, diff, None, timestamp, timestamp),
    )
    connection.commit()
    connection.close()
    set_gauge("change_queue_depth", _pending_change_count())
    return ChangeRecord(
        id=change_id,
        status="pending_approval",
        intent=request,
        candidate_config=candidate,
        diff=diff,
        created_at=timestamp,
        updated_at=timestamp,
    )


def get_change(change_id: str) -> ChangeRecord:
    connection = _connection()
    row = connection.execute("SELECT * FROM changes WHERE id = ?", (change_id,)).fetchone()
    connection.close()
    if row is None:
        raise KeyError(f"Unknown change: {change_id}")
    return ChangeRecord(
        id=row["id"], status=row["status"], intent=ChangeCreate.model_validate_json(row["intent_json"]),
        candidate_config=row["candidate_config"], diff=row["diff"], approved_by=row["approved_by"],
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


def approve_change(change_id: str, actor: str) -> ChangeRecord:
    change = get_change(change_id)
    if change.status != "pending_approval":
        raise ValueError(f"Change {change_id} is not awaiting approval")
    if actor == change.intent.requested_by:
        raise ValueError("A change requester may not approve their own change")
    connection = _connection()
    updated = _now()
    cursor = connection.execute(
        "UPDATE changes SET status = ?, approved_by = ?, updated_at = ? WHERE id = ? AND status = ?",
        ("approved", actor, updated, change_id, "pending_approval"),
    )
    if cursor.rowcount != 1:
        connection.rollback()
        connection.close()
        raise ValueError(f"Change {change_id} is no longer awaiting approval")
    _audit(connection, change_id, actor, "approved")
    connection.commit()
    connection.close()
    return get_change(change_id)


def reject_change(change_id: str, actor: str, reason: str = "") -> ChangeRecord:
    change = get_change(change_id)
    if change.status != "pending_approval":
        raise ValueError(f"Change {change_id} is not awaiting approval")
    if actor == change.intent.requested_by:
        raise ValueError("A change requester may not reject their own change")
    connection = _connection()
    updated = _now()
    cursor = connection.execute(
        "UPDATE changes SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
        ("rejected", updated, change_id, "pending_approval"),
    )
    if cursor.rowcount != 1:
        connection.rollback()
        connection.close()
        raise ValueError(f"Change {change_id} is no longer awaiting approval")
    _audit(connection, change_id, actor, "rejected", {"reason": reason[:500]})
    connection.commit()
    connection.close()
    return get_change(change_id)


def deploy_change(change_id: str, actor: str) -> ChangeRecord:
    change = get_change(change_id)
    if change.status != "approved":
        raise ValueError("Only approved changes can be deployed")
    deployment_mode = os.getenv("CONFIG_MANAGER_DEPLOYMENT_MODE", "disabled")
    if deployment_mode not in {"simulated", "netconf"}:
        raise ValueError("Deployment backend is disabled; configure CONFIG_MANAGER_DEPLOYMENT_MODE")
    increment("production_change_deployments_total", {"mode": deployment_mode, "status": "started"})
    if deployment_mode == "netconf" and change.intent.transport != "netconf":
        raise ValueError("NETCONF deployment requires a NETCONF change intent")
    connection = _connection()
    updated = _now()
    # Reserve the change before performing I/O, preventing two workers from
    # deploying the same approved candidate concurrently.
    cursor = connection.execute(
        "UPDATE changes SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
        ("deploying", updated, change_id, "approved"),
    )
    if cursor.rowcount != 1:
        connection.close()
        raise ValueError("Change is already being deployed")
    _audit(connection, change_id, actor, "deployment_started", {"mode": deployment_mode})
    connection.commit()
    connection.close()
    if deployment_mode == "netconf":
        try:
            device = get_device(change.intent.device_id)
            if not device.enabled:
                raise NetconfDeploymentError("Device is disabled")
            deployment_result = deploy_netconf(
                change.intent.device_id,
                change.candidate_config or "",
                config_format=change.intent.output_format,
                inventory={
                    **device.model_dump(),
                    "host": device.management_address,
                },
            )
        except (NetconfDeploymentError, KeyError, ValueError) as exc:
            connection = _connection()
            updated = _now()
            connection.execute("UPDATE changes SET status = ?, updated_at = ? WHERE id = ?", ("deployment_failed", updated, change_id))
            _audit(connection, change_id, actor, "deployment_failed", {"error": str(exc)})
            connection.commit()
            connection.close()
            increment("production_change_deployments_total", {"mode": deployment_mode, "status": "failure"})
            alert_failed_change(change_id, actor, str(exc))
            raise ValueError(str(exc)) from exc
    else:
        deployment_result = {"status": "simulated"}
    connection = _connection()
    updated = _now()
    connection.execute("UPDATE changes SET status = ?, updated_at = ? WHERE id = ?", ("completed", updated, change_id))
    _audit(connection, change_id, actor, "deployed", {"mode": deployment_mode, "result": deployment_result})
    connection.commit()
    connection.close()
    increment("production_change_deployments_total", {"mode": deployment_mode, "status": "success"})
    set_gauge("change_queue_depth", _pending_change_count())
    return get_change(change_id)


def _pending_change_count() -> int:
    connection = _connection()
    row = connection.execute("SELECT COUNT(*) AS count FROM changes WHERE status IN ('pending_approval', 'approved', 'deploying')").fetchone()
    connection.close()
    return int(row["count"])


def audit_events(change_id: str) -> list[dict[str, Any]]:
    connection = _connection()
    rows = connection.execute("SELECT * FROM audit_events WHERE change_id = ? ORDER BY id", (change_id,)).fetchall()
    connection.close()
    return [dict(row) for row in rows]
