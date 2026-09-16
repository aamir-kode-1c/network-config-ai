from fastapi.testclient import TestClient

from app.main import app
from app.core.netconf_worker import NetconfDeploymentError, deploy_netconf


def test_production_api_fails_closed_without_api_key(monkeypatch):
    monkeypatch.delenv("CONFIG_MANAGER_API_KEY", raising=False)
    monkeypatch.delenv("CONFIG_MANAGER_API_KEYS", raising=False)
    response = TestClient(app).get("/api/v1/devices")
    assert response.status_code == 503


def test_device_inventory_is_persistent_and_does_not_store_password(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DB_PATH", str(tmp_path / "inventory.db"))
    monkeypatch.setenv(
        "CONFIG_MANAGER_API_KEYS",
        '{"test-key":{"actor":"admin@example.com","role":"admin"}}',
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/devices",
        headers={"X-API-Key": "test-key", "X-Actor": "admin@example.com"},
        json={
            "device_id": "router-001",
            "vendor": "cisco",
            "product": "ASR 9000",
            "management_address": "192.0.2.10",
            "username": "netconf",
            "password_env": "DEVICE_PASSWORD",
            "hostkey": "ssh-ed25519 255 SHA256:example",
        },
    )
    assert response.status_code == 201
    assert "password" not in response.json()
    assert "secret" not in response.text.lower()
    assert client.get("/api/v1/devices", headers={"X-API-Key": "test-key"}).json()[0]["device_id"] == "router-001"


def test_netconf_rejects_non_xml_and_unpinned_host(monkeypatch):
    monkeypatch.setenv(
        "DEVICE_INVENTORY_JSON",
        '{"router-001":{"host":"192.0.2.10","username":"netconf","password":"secret"}}',
    )
    try:
        deploy_netconf("router-001", "interface eth0", config_format="yang")
    except NetconfDeploymentError as exc:
        assert "XML" in str(exc)
    else:
        raise AssertionError("non-XML candidate was accepted")

    monkeypatch.setenv(
        "DEVICE_INVENTORY_JSON",
        '{"router-001":{"host":"192.0.2.10","username":"netconf","password":"secret","hostkey_verify":true}}',
    )
    try:
        deploy_netconf("router-001", "<config/>", config_format="xml")
    except NetconfDeploymentError as exc:
        assert "hostkey" in str(exc)
    else:
        raise AssertionError("unpinned host was accepted")


def test_health_endpoints():
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    assert "config_manager_uptime_seconds" in client.get("/metrics").text
