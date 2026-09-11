"""Low-dependency metrics, tracing, and production-change alerting."""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.request
import uuid
from collections import Counter
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger("network_config_ai")
_metrics: Counter[str] = Counter()
_lock = threading.Lock()
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def start_trace(incoming: str | None = None) -> str:
    value = incoming or f"tr-{uuid.uuid4().hex}"
    _trace_id.set(value)
    return value


def current_trace_id() -> str:
    return _trace_id.get()


def increment(name: str, labels: dict[str, str] | None = None, value: int = 1) -> None:
    label_text = ""
    if labels:
        label_text = "{" + ",".join(f'{key}="{str(val).replace(chr(34), chr(39))}"' for key, val in sorted(labels.items())) + "}"
    with _lock:
        _metrics[f"{name}{label_text}"] += value


def set_gauge(name: str, value: int | float, labels: dict[str, str] | None = None) -> None:
    label_text = ""
    if labels:
        label_text = "{" + ",".join(f'{key}="{str(val).replace(chr(34), chr(39))}"' for key, val in sorted(labels.items())) + "}"
    with _lock:
        _metrics[f"{name}{label_text}"] = value


def snapshot() -> dict[str, int | float]:
    with _lock:
        return dict(_metrics)


def metric_value(name: str, labels: dict[str, str] | None = None) -> int | float:
    label_text = ""
    if labels:
        label_text = "{" + ",".join(f'{key}="{str(val).replace(chr(34), chr(39))}"' for key, val in sorted(labels.items())) + "}"
    with _lock:
        return _metrics.get(f"{name}{label_text}", 0)


def alert_failed_change(change_id: str, actor: str, error: str) -> None:
    payload = {"alert": "production_change_failed", "change_id": change_id, "actor": actor, "error": error, "trace_id": current_trace_id()}
    logger.error("Production change failed: %s", json.dumps(payload, sort_keys=True))
    webhook = os.getenv("CONFIG_MANAGER_ALERT_WEBHOOK")
    if not webhook:
        return
    request = urllib.request.Request(webhook, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(request, timeout=5).close()
    except OSError:
        logger.exception("Unable to deliver production change alert")


set_gauge("change_queue_depth", 0)
set_gauge("configuration_rollback_rate", 0)
