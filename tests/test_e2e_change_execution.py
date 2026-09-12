import pytest

from app.core.production import ChangeCreate, approve_change, create_change, deploy_change, get_change


E2E_CASES = [
    ("cisco", "ASR 9000", "GigabitEthernet0/1"),
    ("nokia", "7750 SR", "1/1/1"),
    ("ericsson", "Router 6000", "ge-0/0/1"),
    ("huawei", "NE40E", "GigabitEthernet0/0/1"),
    ("openet", "Policy Manager", "pm0"),
]


@pytest.mark.parametrize("vendor,product,interface", E2E_CASES)
def test_change_creation_approval_and_simulated_execution(tmp_path, monkeypatch, vendor, product, interface):
    """Creates a candidate, requires a separate approval, then executes it."""
    monkeypatch.setenv("CONFIG_DB_PATH", str(tmp_path / f"{vendor}.db"))
    monkeypatch.setenv("CONFIG_MANAGER_DEPLOYMENT_MODE", "simulated")
    request = ChangeCreate(
        device_id=f"e2e-{vendor}-001",
        vendor=vendor,
        product=product,
        change_type="interface_update",
        payload={
            "interface": interface,
            "ip": "192.0.2.10",
            "subnet": "24",
            "description": f"{vendor} end-to-end execution",
            "admin_state": "up",
        },
        reason=f"Validate {vendor} end-to-end change execution",
        requested_by="operator@example.com",
        transport="simulated",
    )

    created = create_change(request)
    print(f"[E2E] {vendor}: change created: {created.id} (status={created.status})")
    assert created.status == "pending_approval"
    assert created.candidate_config
    assert get_change(created.id).status == "pending_approval"

    approved = approve_change(created.id, "approver@example.com")
    print(f"[E2E] {vendor}: change approved by approver@example.com (status={approved.status})")
    assert approved.status == "approved"

    deployed = deploy_change(created.id, "deployer@example.com")
    print(f"[E2E] {vendor}: simulated deployment completed by deployer@example.com (status={deployed.status})")
    assert deployed.status == "completed"
    assert get_change(created.id).status == "completed"
