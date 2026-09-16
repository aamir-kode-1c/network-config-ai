"""Explicit device transport workers used by approved changes."""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
from typing import Any


def _credentials(env_name: str) -> dict[str, Any]:
    raw = os.getenv(env_name)
    if not raw:
        raise ValueError(f"Credential environment variable {env_name} is not configured")
    try:
        credentials = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Credential environment variable {env_name} must contain JSON") from exc
    if not isinstance(credentials, dict):
        raise ValueError("Credential JSON must be an object")
    return credentials


def deploy_candidate(intent: Any, config: str) -> dict[str, Any]:
    transport = intent.transport
    if transport == "simulated":
        return {"transport": transport, "status": "simulated", "output": config}
    if not intent.management_address:
        raise ValueError("management_address is required for device deployment")
    credentials = _credentials(intent.credentials_env)
    if transport == "netconf":
        return _deploy_netconf(intent, credentials, config)
    if transport == "restconf":
        return _deploy_restconf(intent, credentials, config)
    if transport == "ssh":
        return _deploy_ssh(intent, credentials, config)
    raise ValueError(f"Unsupported deployment transport: {transport}")


def _deploy_netconf(intent: Any, credentials: dict[str, Any], config: str) -> dict[str, Any]:
    if intent.output_format != "xml":
        raise ValueError("NETCONF deployment requires output_format=xml")
    from ncclient import manager

    with manager.connect(
        host=intent.management_address,
        port=intent.port,
        username=credentials["username"],
        password=credentials.get("password"),
        hostkey_verify=True,
        allow_agent=False,
        look_for_keys=False,
        timeout=intent.timeout_seconds,
    ) as session:
        session.edit_config(target="candidate", config=config)
        session.validate()
        session.commit()
    return {"transport": "netconf", "status": "committed"}


def _deploy_restconf(intent: Any, credentials: dict[str, Any], config: str) -> dict[str, Any]:
    if intent.output_format not in {"xml", "json"}:
        raise ValueError("RESTCONF deployment requires output_format=xml or json")
    path = intent.restconf_path
    if not path.startswith("/"):
        raise ValueError("restconf_path must be an absolute API path")
    scheme = "https" if intent.tls_verify else "http"
    url = f"{scheme}://{intent.management_address}:{intent.port}{path}"
    body = config.encode("utf-8")
    content_type = "application/yang-data+json" if intent.output_format == "json" else "application/yang-data+xml"
    request = urllib.request.Request(url, data=body, method="PATCH", headers={"Content-Type": content_type, "Accept": content_type})
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, url, credentials["username"], credentials["password"])
    context = ssl.create_default_context() if intent.tls_verify else ssl._create_unverified_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPBasicAuthHandler(password_mgr),
        urllib.request.HTTPSHandler(context=context),
    )
    with opener.open(request, timeout=intent.timeout_seconds) as response:
        return {"transport": "restconf", "status": "committed", "http_status": response.status}


def _deploy_ssh(intent: Any, credentials: dict[str, Any], config: str) -> dict[str, Any]:
    import paramiko

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            intent.management_address,
            port=intent.port,
            username=credentials["username"],
            password=credentials.get("password"),
            key_filename=credentials.get("key_filename"),
            timeout=intent.timeout_seconds,
            allow_agent=False,
            look_for_keys=False,
        )
        command = "configure terminal\n" + config.rstrip() + "\nend\nwrite memory\n"
        stdin, stdout, stderr = client.exec_command(command, timeout=intent.timeout_seconds)
        return {"transport": "ssh", "status": "committed", "output": stdout.read().decode(), "error": stderr.read().decode()}
    finally:
        client.close()
