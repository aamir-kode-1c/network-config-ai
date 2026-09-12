from app.core.production import (
    ChangeCreate,
    approve_change,
    create_change,
    deploy_change,
    get_change,
)


def test_change_requires_approval_before_deployment(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_DB_PATH", str(tmp_path / "changes.db"))
    request = ChangeCreate(
        device_id="router-001",
        vendor="cisco",
        product="ASR 9000",
        change_type="interface_update",
        payload={"interface": "GigabitEthernet0/1", "ip": "192.0.2.1", "subnet": "24"},
        reason="Provision transit link",
        requested_by="engineer@example.com",
        transport="simulated",
    )

    change = create_change(request)
    assert change.status == "pending_approval"
    assert change.candidate_config
    assert get_change(change.id).status == "pending_approval"

    approved = approve_change(change.id, "approver@example.com")
    assert approved.status == "approved"

    monkeypatch.setenv("CONFIG_MANAGER_DEPLOYMENT_MODE", "simulated")
    deployed = deploy_change(change.id, "release@example.com")
    assert deployed.status == "completed"
