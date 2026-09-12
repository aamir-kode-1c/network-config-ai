const form = document.getElementById("discovery-form");
const results = document.getElementById("discovery-results");
const feedback = document.getElementById("discovery-feedback");
const addSelected = document.getElementById("add-selected");

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[character]));
}

function selectedRows() {
    return [...results.querySelectorAll("input[data-address]:checked")];
}

function renderDevices(devices) {
    if (!devices.length) {
        results.innerHTML = '<div class="empty-state">No reachable devices found in this range.</div>';
        addSelected.disabled = true;
        return;
    }
    results.innerHTML = devices.map((device, index) => `
        <div class="test-case-row">
            <input type="checkbox" data-address="${escapeHtml(device.address)}" data-port="${device.suggested_port || 22}">
            <div><strong>${index + 1}. ${escapeHtml(device.address)}</strong><small>Open ports: ${escapeHtml(device.open_ports.join(", "))}</small></div>
            <input class="discovery-field" data-vendor="${escapeHtml(device.address)}" value="unknown" aria-label="Vendor">
            <input class="discovery-field" data-product="${escapeHtml(device.address)}" value="Unknown network device" aria-label="Product">
        </div>
    `).join("");
    results.querySelectorAll("input[type=checkbox]").forEach((checkbox) => checkbox.addEventListener("change", () => {
        addSelected.disabled = selectedRows().length === 0;
    }));
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "Scanning approved range...";
    try {
        const ports = document.getElementById("ports").value.split(",").map((value) => Number(value.trim())).filter(Boolean);
        const response = await fetch("/api/inventory/discover", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({cidr: document.getElementById("cidr").value.trim(), ports})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Discovery failed");
        renderDevices(data.devices);
        feedback.textContent = `Scanned ${data.scanned} addresses; found ${data.devices.length} reachable device(s).`;
    } catch (error) {
        feedback.textContent = error.message;
        results.innerHTML = '<div class="connector-error">Discovery failed.</div>';
    }
});

addSelected.addEventListener("click", async () => {
    feedback.textContent = "Adding selected devices...";
    const added = [];
    for (const checkbox of selectedRows()) {
        const address = checkbox.dataset.address;
        const vendor = results.querySelector(`[data-vendor="${CSS.escape(address)}"]`).value;
        const product = results.querySelector(`[data-product="${CSS.escape(address)}"]`).value;
        const response = await fetch("/api/inventory/add", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({device_id: `discovered-${address.replaceAll(".", "-")}`, vendor, product, management_address: address, port: Number(checkbox.dataset.port)})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Unable to add ${address}`);
        added.push(data.device_id);
    }
    feedback.textContent = `Added ${added.length} device(s) to inventory: ${added.join(", ")}`;
    addSelected.disabled = true;
});
