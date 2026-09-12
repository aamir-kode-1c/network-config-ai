from collections import Counter

from fastapi import APIRouter

from app.core.production import list_devices

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


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
