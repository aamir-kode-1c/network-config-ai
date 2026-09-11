"""Approval-gated NETCONF deployment worker."""

from __future__ import annotations

import os
import json
from xml.etree import ElementTree
from typing import Any

from ncclient import manager
from app.core.observability import increment


class NetconfDeploymentError(RuntimeError):
    """Raised when a NETCONF deployment cannot be completed safely."""


def _inventory() -> dict[str, dict[str, Any]]:
    raw = os.getenv("DEVICE_INVENTORY_JSON")
    if not raw:
        raise NetconfDeploymentError("DEVICE_INVENTORY_JSON is not configured")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NetconfDeploymentError("DEVICE_INVENTORY_JSON is invalid JSON") from exc
    if not isinstance(data, dict):
        raise NetconfDeploymentError("DEVICE_INVENTORY_JSON must map device IDs to connection objects")
    return data


def _device(device_id: str, inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    device = inventory or _inventory().get(device_id)
    if not isinstance(device, dict):
        raise NetconfDeploymentError(f"No NETCONF inventory entry for device {device_id}")
    required = ("host", "username")
    missing = [field for field in required if not device.get(field)]
    if missing:
        raise NetconfDeploymentError(f"NETCONF inventory is missing: {', '.join(missing)}")
    if not device.get("password") and not device.get("password_env"):
        raise NetconfDeploymentError("NETCONF inventory requires password or password_env")
    return device


def deploy_netconf(
    device_id: str,
    config: str,
    *,
    config_format: str,
    commit_timeout: int = 120,
    inventory: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Validate and apply a candidate via NETCONF commit-confirmed.

    Device credentials are resolved from DEVICE_INVENTORY_JSON at deployment time
    and are never persisted in the change database.
    """
    if config_format != "xml":
        raise NetconfDeploymentError("NETCONF deployment requires XML output")
    try:
        root = ElementTree.fromstring(config)
    except ElementTree.ParseError as exc:
        raise NetconfDeploymentError("NETCONF candidate is not well-formed XML") from exc
    if root.tag.rsplit("}", 1)[-1] != "config":
        raise NetconfDeploymentError("NETCONF candidate root element must be <config>")
    if not 1 <= int(commit_timeout) <= 600:
        raise NetconfDeploymentError("commit_timeout must be between 1 and 600 seconds")
    device = _device(device_id, inventory)
    password = device.get("password") or os.getenv(device["password_env"])
    if not password:
        raise NetconfDeploymentError(f"Credential environment variable {device['password_env']} is not set")
    try:
        port = int(device.get("port", 830))
        timeout = int(device.get("timeout", 30))
    except (TypeError, ValueError) as exc:
        raise NetconfDeploymentError("NETCONF port and timeout must be integers") from exc
    hostkey_verify = device.get("hostkey_verify", True)
    if not isinstance(hostkey_verify, bool):
        raise NetconfDeploymentError("hostkey_verify must be a boolean")
    hostkey = device.get("hostkey")
    if hostkey_verify and not hostkey:
        raise NetconfDeploymentError("hostkey is required when hostkey_verify is enabled")
    if hostkey_verify and not os.path.isfile(str(hostkey)):
        raise NetconfDeploymentError("configured NETCONF hostkey file does not exist")

    connect_args: dict[str, Any] = {
        "host": device["host"],
        "port": port,
        "username": device["username"],
        "password": password,
        "hostkey_verify": hostkey_verify,
        "timeout": timeout,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if hostkey:
        connect_args["known_hosts"] = hostkey

    try:
        with manager.connect(**connect_args) as session:
            if not session.server_capabilities:
                raise NetconfDeploymentError("NETCONF server did not advertise capabilities")
            if not any("confirmed-commit" in capability for capability in session.server_capabilities):
                raise NetconfDeploymentError("NETCONF server does not support confirmed commit")
            session.discard_changes()
            locked = False
            try:
                session.lock("candidate")
                locked = True
                session.edit_config(target="candidate", config=config)
                session.validate(source="candidate")
                commit = session.commit(confirmed=True, confirm_timeout=commit_timeout)
                # Confirm only after the device accepts the candidate. A failure
                # before this call intentionally leaves the rollback timer active.
                session.commit()
            finally:
                if locked:
                    try:
                        session.unlock("candidate")
                    except Exception:
                        # Unlock failure must not turn a committed candidate into
                        # a false success.
                        raise NetconfDeploymentError("Unable to unlock NETCONF candidate")
            increment("device_reachability_total", {"device_id": device_id, "status": "success"})
            return {
                "status": "committed",
                "device_id": device_id,
                "message": str(commit),
            }
    except NetconfDeploymentError:
        increment("device_reachability_total", {"device_id": device_id, "status": "failure"})
        raise
    except Exception as exc:
        increment("device_reachability_total", {"device_id": device_id, "status": "failure"})
        raise NetconfDeploymentError(f"NETCONF deployment failed for {device_id}: {exc}") from exc
