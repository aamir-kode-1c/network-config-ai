"""Seed an idempotent lab inventory with ten devices per supported vendor."""

from __future__ import annotations

import argparse
from collections import Counter

from app.core.production import DeviceCreate, list_devices, register_device


VENDOR_PRODUCTS = {
    "cisco": ["ASR 9000", "Catalyst 9000", "Nexus 7000"],
    "nokia": ["7750 SR", "7250 IXR", "SROS", "Nuage VNS"],
    "ericsson": ["Router 6000", "MINI-LINK", "SSR 8000"],
    "huawei": ["NE40E", "AR G3", "CloudEngine S Series"],
    "openet": ["Policy Manager", "Charging Gateway"],
}


def seed_devices(per_vendor: int = 10) -> list[str]:
    created: list[str] = []
    existing = {device.device_id for device in list_devices()}
    vendor_index = {vendor: index for index, vendor in enumerate(VENDOR_PRODUCTS)}
    for vendor, products in VENDOR_PRODUCTS.items():
        for number in range(1, per_vendor + 1):
            device_id = f"lab-{vendor}-device-{number:02d}"
            if device_id in existing:
                continue
            device = DeviceCreate(
                device_id=device_id,
                vendor=vendor,
                product=products[(number - 1) % len(products)],
                management_address=f"192.0.2.{10 + vendor_index[vendor] * 10 + number}",
                username="netops",
                password_env=f"LAB_{vendor.upper()}_{number:02d}_PASSWORD",
                port=830,
                timeout=30,
                hostkey_verify=False,
                hostkey=None,
                enabled=True,
            )
            register_device(device)
            created.append(device_id)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-vendor", type=int, default=10)
    args = parser.parse_args()
    if args.per_vendor < 10:
        parser.error("--per-vendor must be at least 10")
    created = seed_devices(args.per_vendor)
    inventory = list_devices()
    counts = Counter(device.vendor for device in inventory)
    print(f"Created {len(created)} devices; inventory total: {len(inventory)}")
    for vendor in VENDOR_PRODUCTS:
        print(f"{vendor}: {counts[vendor]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
