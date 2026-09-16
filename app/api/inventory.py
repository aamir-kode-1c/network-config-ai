from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import socket

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.production import DeviceCreate, list_devices, register_device

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class DiscoveryRequest(BaseModel):
    cidr: str = Field(min_length=1, max_length=43)
    ports: list[int] = Field(default=[22, 80, 443, 830], min_length=1, max_length=8)
    timeout: float = Field(default=0.35, ge=0.1, le=2.0)


class InventoryAddRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    vendor: str = Field(default="unknown", min_length=1, max_length=50)
    product: str = Field(default="Unknown network device", min_length=1, max_length=100)
    management_address: str
    port: int = Field(default=22, ge=1, le=65535)


def _probe_host(address: str, ports: list[int], timeout: float) -> dict:
    open_ports = []
    for port in ports:
        try:
            with socket.create_connection((address, port), timeout=timeout):
                open_ports.append(port)
        except OSError:
            continue
    return {
        "address": address,
        "reachable": bool(open_ports),
        "open_ports": open_ports,
        "suggested_port": open_ports[0] if open_ports else None,
        "vendor": "unknown",
        "product": "Unknown network device",
    }


@router.post("/discover")
def discover_devices(request: DiscoveryRequest):
    try:
        network = ipaddress.ip_network(request.cidr, strict=False)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid CIDR: {exc}") from exc
    if not (network.is_private or network.is_loopback or network.is_link_local):
        raise HTTPException(status_code=422, detail="Discovery is limited to private, loopback, or link-local networks")
    hosts = list(network.hosts())
    if len(hosts) > 256:
        raise HTTPException(status_code=422, detail="Discovery is limited to 256 host addresses per scan")
    if any(port in {0} for port in request.ports):
        raise HTTPException(status_code=422, detail="Ports must be between 1 and 65535")
    with ThreadPoolExecutor(max_workers=min(32, max(1, len(hosts)))) as executor:
        futures = [executor.submit(_probe_host, str(host), request.ports, request.timeout) for host in hosts]
        results = [future.result() for future in as_completed(futures)]
    results.sort(key=lambda item: ipaddress.ip_address(item["address"]))
    return {"cidr": str(network), "scanned": len(hosts), "devices": [item for item in results if item["reachable"]]}


@router.post("/add")
def add_discovered_device(request: InventoryAddRequest):
    try:
        address = ipaddress.ip_address(request.management_address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid management address: {exc}") from exc
    if not (address.is_private or address.is_loopback or address.is_link_local):
        raise HTTPException(status_code=422, detail="Only private, loopback, or link-local addresses can be added")
    try:
        device = register_device(
            DeviceCreate(
                device_id=request.device_id,
                vendor=request.vendor.lower(),
                product=request.product,
                management_address=str(address),
                username="discovered-device",
                password_env="DISCOVERED_DEVICE_PASSWORD",
                port=request.port,
                timeout=5,
                hostkey_verify=False,
                enabled=True,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "device_id": device.device_id,
        "management_address": device.management_address,
        "status": "added",
    }


@router.get("/summary")
def inventory_summary():
    devices = list_devices()
    counts = Counter(device.vendor for device in devices)
    return {
        "total": len(devices),
        "vendors": [
            {
                "vendor": vendor,
                "count": counts[vendor],
                "devices": [
                    {
                        "device_id": device.device_id,
                        "product": device.product,
                        "management_address": device.management_address,
                        "enabled": device.enabled,
                    }
                    for device in devices
                    if device.vendor == vendor
                ],
            }
            for vendor in sorted(counts)
        ],
    }
