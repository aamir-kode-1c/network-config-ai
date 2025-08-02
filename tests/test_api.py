import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

PRODUCT_CASES = [
    # vendor, product, expected, interface
    ("nokia", "7750 SR", "configure router interface", "eth0"),
    ("nokia", "7250 IXR", "set interface", "eth0"),
    ("nokia", "SROS", "/configure port", "eth0"),
    ("nokia", "Nuage VNS", "vns interface", "eth0"),
    # Ericsson
    ("ericsson", "Router 6000", "interface ge-0/0/1", "ge-0/0/1"),
    ("ericsson", "MINI-LINK", "minilink-if", "ml-if1"),
    ("ericsson", "SSR 8000", "set interface", "eth0"),
    # Cisco
    ("cisco", "ASR 9000", "interface GigabitEthernet0/1", "GigabitEthernet0/1"),
    ("cisco", "Catalyst 9000", "switchport mode access", "GigabitEthernet1/0/1"),
    ("cisco", "Nexus 7000", "interface Ethernet1/1", "Ethernet1/1"),
    # Openet
    ("openet", "Policy Manager", "pm-if", "pm0"),
    ("openet", "Charging Gateway", "cg-if", "cg0"),
    # Huawei (placeholders)
    ("huawei", "NE40E", "# TODO: Implement CLI for NE40E", "GigabitEthernet0/0/1"),
    ("huawei", "AR G3", "# TODO: Implement CLI for AR G3", "GigabitEthernet0/0/1"),
    ("huawei", "CloudEngine S Series", "# TODO: Implement CLI for CloudEngine S Series", "GigabitEthernet0/0/1"),
]

@pytest.mark.parametrize("vendor,product,expected,iface", PRODUCT_CASES)
def test_generate_config_product(vendor, product, expected, iface):
    response = client.post("/generate-config", json={
        "vendor": vendor,
        "product": product,
        "nb_payload": {"interface": iface, "ip": "1.1.1.1", "subnet": "24", "description": "test", "admin_state": "up"},
        "description": f"Test config for {vendor} {product}",
        "format": "cli"
    })
    assert response.status_code == 200
    assert expected in response.json()["config"]

def test_generate_config_invalid_vendor():
    response = client.post("/generate-config", json={
        "vendor": "fakevendor",
        "product": "Fake Product",
        "nb_payload": {"interface": "eth2", "ip": "10.0.0.3"},
        "description": "Invalid vendor",
        "format": "cli"
    })
    assert response.status_code == 400
    assert "Unsupported vendor" in response.json()["detail"]
