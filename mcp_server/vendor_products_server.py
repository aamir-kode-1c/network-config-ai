"""Local MCP server exposing vendor products and payload templates.

Run from the repository root:
    python -m mcp_server.vendor_products_server

The server uses stdio transport so MCP clients can launch it as a local process.
Set VENDOR_CATALOG_URL to load a normalized JSON catalog from an API instead of
the repository's vendor_products.json file.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.vendor_catalog import (
    catalog_as_product_mapping,
    get_payload_templates,
    get_product_details,
    load_catalog,
)
from app.core.rag import search_documents
from app.core.observability import increment


mcp = FastMCP("network-config-ai-vendor-products")


@mcp.tool()
def list_vendors_and_products() -> dict[str, list[str]]:
    """List every vendor and product currently available to the agents."""
    return catalog_as_product_mapping(load_catalog())


@mcp.tool()
def get_product(vendor: str, product: str) -> dict[str, Any]:
    """Return metadata and documentation links for one vendor product."""
    try:
        return get_product_details(vendor, product)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool()
def get_product_payloads(vendor: str, product: str) -> dict[str, Any]:
    """Return CLI, JSON, XML, and YANG payload templates for a product."""
    try:
        return get_payload_templates(vendor, product)
    except KeyError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool()
def search_vendor_documentation(query: str, vendor: str | None = None, product: str | None = None) -> list[dict[str, Any]]:
    """Retrieve vendor documentation passages with versioned citations."""
    increment("ai_tool_invocations_total", {"tool": "mcp_search_vendor_documentation"})
    return search_documents(query, vendor, product)


@mcp.resource("vendor-products://catalog")
def vendor_products_catalog() -> str:
    """Expose the complete vendor/product catalog as an MCP resource."""
    return json.dumps(load_catalog(), indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
