"""Vendor and product catalog loading with optional remote discovery."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


CATALOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../vendor_products.json")
)
SUPPORTED_FORMATS = ("cli", "json", "xml", "yang")


def _read_json_url(url: str) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "network-config-ai/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load vendor catalog from {url}: {exc}") from exc


def _normalize_catalog(data: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(data, dict):
        raise ValueError("Vendor catalog must be a JSON object")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for vendor, products in data.items():
        if not isinstance(vendor, str) or not isinstance(products, list):
            raise ValueError("Vendor catalog entries must map vendor names to product arrays")
        entries = []
        for product in products:
            if isinstance(product, str):
                entries.append({"name": product, "formats": list(SUPPORTED_FORMATS), "payloads": {}})
                continue
            if not isinstance(product, dict) or not isinstance(product.get("name"), str):
                raise ValueError(f"Invalid product entry for vendor {vendor}")
            entry = {
                "name": product["name"],
                "formats": product.get("formats", list(SUPPORTED_FORMATS)),
                "payloads": product.get("payloads", {}),
                "documentation_url": product.get("documentation_url"),
                "api_url": product.get("api_url"),
            }
            entry["formats"] = [fmt for fmt in entry["formats"] if fmt in SUPPORTED_FORMATS]
            entries.append(entry)
        normalized[vendor.lower()] = entries
    return normalized


def load_catalog(source: str | None = None) -> dict[str, list[dict[str, Any]]]:
    source = source or os.getenv("VENDOR_CATALOG_URL")
    if source:
        return _normalize_catalog(_read_json_url(source))
    with open(CATALOG_PATH, encoding="utf-8") as catalog_file:
        return _normalize_catalog(json.load(catalog_file))


def catalog_as_product_mapping(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    return {vendor: [product["name"] for product in products] for vendor, products in catalog.items()}


def get_product_details(vendor: str, product: str) -> dict[str, Any]:
    catalog = load_catalog()
    for entry in catalog.get(vendor.lower(), []):
        if entry["name"].lower() == product.lower():
            return deepcopy(entry)
    raise KeyError(f"Unknown vendor/product: {vendor}/{product}")


def get_payload_templates(vendor: str, product: str) -> dict[str, Any]:
    details = get_product_details(vendor, product)
    templates = deepcopy(details.get("payloads", {}))
    default_payload = {
        "interface": "eth0",
        "ip": "192.0.2.1",
        "subnet": "24",
        "description": f"{details['name']} interface",
        "admin_state": "up",
    }
    for output_format in details["formats"]:
        templates.setdefault(output_format, deepcopy(default_payload))
        if not templates[output_format]:
            templates[output_format] = deepcopy(default_payload)
    return {"vendor": vendor.lower(), "product": details["name"], "formats": details["formats"], "payloads": templates}


def discover_catalog(source_url: str) -> dict[str, list[dict[str, Any]]]:
    return _normalize_catalog(_read_json_url(source_url))
