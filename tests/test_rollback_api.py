import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test scenarios for different vendors/products with rollback
TEST_CASES = [
    {
        "vendor": "nokia",
        "product": "7750 SR",
        "format": "cli",
        "payloads": [
            {
                "interface": "to-core",
                "ip": "10.1.1.1",
                "subnet": "24",
                "description": "Uplink to Core A",
                "admin_state": "up"
            },
            {
                "interface": "to-core",
                "ip": "10.1.1.1",
                "subnet": "24",
                "description": "Uplink to Core B",
                "admin_state": "up"
            }
        ]
    },
    {
        "vendor": "cisco",
        "product": "ASR 9000",
        "format": "yang",
        "payloads": [
            {
                "interface": "GigabitEthernet0/1",
                "ip": "172.16.0.1",
                "subnet": "255.255.255.0",
                "description": "WAN Edge OLD",
                "admin_state": "down"
            },
            {
                "interface": "GigabitEthernet0/1",
                "ip": "172.16.0.1",
                "subnet": "255.255.255.0",
                "description": "WAN Edge NEW",
                "admin_state": "up"
            }
        ]
    },
    {
        "vendor": "ericsson",
        "product": "Router 6000",
        "format": "xml",
        "payloads": [
            {
                "interface": "ge-0/0/2",
                "ip": "192.168.10.2",
                "subnet": "24",
                "description": "Branch WAN 1"
            },
            {
                "interface": "ge-0/0/3",
                "ip": "192.168.10.3",
                "subnet": "24",
                "description": "Branch WAN 2"
            }
        ]
    },
    {
        "vendor": "huawei",
        "product": "NE40E",
        "format": "json",
        "payloads": [
            {
                "interface": "GigabitEthernet0/0/1",
                "ip": "10.10.10.2",
                "subnet": "255.255.255.0",
                "description": "DC Link 1",
                "admin_state": "up"
            },
            {
                "interface": "GigabitEthernet0/0/1",
                "ip": "10.10.10.3",
                "subnet": "255.255.255.0",
                "description": "DC Link 2",
                "admin_state": "down"
            }
        ]
    },
    {
        "vendor": "openet",
        "product": "Policy Manager",
        "format": "cli",
        "payloads": [
            {
                "interface": "eth1",
                "ip": "10.20.30.40",
                "subnet": "24",
                "description": "Policy link 1",
                "admin_state": "up"
            },
            {
                "interface": "eth1",
                "ip": "10.20.30.40",
                "subnet": "24",
                "description": "Policy link 2",
                "admin_state": "down"
            }
        ]
    }
]

def test_rollback_for_all_vendors():
    for case in TEST_CASES:
        vendor = case["vendor"]
        product = case["product"]
        format_ = case["format"]
        payloads = case["payloads"]

        # Generate config #1
        resp1 = client.post("/generate-config", json={
            "vendor": vendor,
            "product": product,
            "nb_payload": payloads[0],
            "description": "Initial config",
            "format": format_
        })
        assert resp1.status_code == 200
        config1 = resp1.json()["config"]

        # Generate config #2
        resp2 = client.post("/generate-config", json={
            "vendor": vendor,
            "product": product,
            "nb_payload": payloads[1],
            "description": "Modified config",
            "format": format_
        })
        assert resp2.status_code == 200
        config2 = resp2.json()["config"]
        assert config1 != config2

        # Rollback
        rollback_resp = client.post("/rollback", json={
            "vendor": vendor,
            "product": product,
            "nb_payload": {},
            "description": "",
            "format": format_
        })
        assert rollback_resp.status_code == 200
        rolled_back = rollback_resp.json()["rolled_back_config"]
        assert rolled_back == config1, f"Rollback failed for {vendor} {product}"
