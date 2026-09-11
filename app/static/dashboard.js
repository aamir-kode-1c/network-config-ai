// Optionally enhance UX with AJAX in the future
// For now, form posts to /dashboard and reloads

console.log("dashboard.js loaded");
let vendorProducts = {};
let sbiDevices = {
    nokia: [
        { value: "nokia_7750sr_ssh", label: "Nokia 7750 SR (SSH/CLI)" },
        { value: "nokia_7750sr_netconf", label: "Nokia 7750 SR (NETCONF)" }
    ],
    ericsson: [
        { value: "ericsson_router6000_ssh", label: "Ericsson Router 6000 (SSH/CLI)" },
        { value: "ericsson_router6000_cli", label: "Ericsson Router 6000 (CLI)" }
    ],
    openet: [
        { value: "openet_pm_ssh", label: "Openet Policy Manager (SSH/CLI)" }
    ],
    huawei: [
        { value: "huawei_ne40e_ssh", label: "Huawei NE40E (SSH/CLI)" },
        { value: "huawei_ne40e_cli", label: "Huawei NE40E (CLI)" },
        { value: "huawei_ar_g3_cli", label: "Huawei AR G3 (CLI)" },
        { value: "huawei_cloudengine_cli", label: "Huawei CloudEngine S Series (CLI)" }
    ],
    cisco: [
        { value: "cisco_asr9000_ssh", label: "Cisco ASR 9000 (SSH/CLI)" },
        { value: "cisco_asr9000_netconf", label: "Cisco ASR 9000 (NETCONF)" }
    ]
};

function showLoading(selector, show) {
    document.querySelector(selector).style.display = show ? "block" : "none";
}

function refreshAgentConnections() {
    const list = document.getElementById("connector-list");
    list.innerHTML = '<div class="connector-loading">Checking agent connections...</div>';
    fetch("/api/agents/status")
        .then(response => response.json())
        .then(agents => {
            list.innerHTML = "";
            agents.forEach(agent => {
                const connected = agent.status === "Connected";
                const card = document.createElement("div");
                card.className = "connector-card";
                card.innerHTML = `<strong>${agent.vendor}</strong><div class="connector-meta">${agent.device || "Device not assigned"}</div><div class="connector-status ${connected ? "connected" : "disconnected"}"><i class="connector-dot"></i>${agent.status}</div><div class="connector-meta">${agent.endpoint}</div>${agent.error ? `<div class="connector-error" title="${agent.error}">${agent.error}</div>` : `<div class="connector-meta">Checked ${agent.last_check || "now"}</div>`}`;
                list.appendChild(card);
            });
        })
        .catch(() => {
            list.innerHTML = '<div class="connector-error">Unable to query agent status.</div>';
        });
}

function showFeedback(selector, msg, isError = false) {
    const el = document.querySelector(selector);
    el.textContent = msg;
    el.className = "feedback" + (isError ? " error" : "");
    el.style.display = msg ? "block" : "none";
}

function clearFeedback() {
    showFeedback("#form-feedback", "");
    showFeedback("#output-error", "");
    showFeedback("#sim-push-result", "");
}

function populateVendors() {
    const vendorSel = document.getElementById("vendor");
    vendorSel.innerHTML = "";
    Object.keys(vendorProducts).forEach(vendor => {
        const opt = document.createElement("option");
        opt.value = vendor;
        opt.textContent = vendor.charAt(0).toUpperCase() + vendor.slice(1);
        vendorSel.appendChild(opt);
    });

}

function populateProducts(vendor) {
    const productSel = document.getElementById("product");
    productSel.innerHTML = "";
    (vendorProducts[vendor] || []).forEach(product => {
        const opt = document.createElement("option");
        opt.value = product;
        opt.textContent = product;
        productSel.appendChild(opt);
    });
}

function populateSbiDevices(vendor) {
    const sbiSel = document.getElementById("sbi-device");
    sbiSel.innerHTML = "";
    (sbiDevices[vendor] || []).forEach(dev => {
        const opt = document.createElement("option");
        opt.value = dev.value;
        opt.textContent = dev.label;
        sbiSel.appendChild(opt);
    });
}

function fetchVendorProducts() {
    showLoading("#form-loading", true);
    console.log("Fetching /api/vendor-products...");
    fetch("/api/vendor-products")
        .then(r => {
            console.log("Response status:", r.status);
            return r.json();
        })
        .then(data => {
            console.log("Fetched vendorProducts:", data);
            vendorProducts = data;
            populateVendors();
            const vendorVal = document.getElementById("vendor").value;
            console.log("Selected vendor after populateVendors:", vendorVal);
            populateProducts(vendorVal);
            populateSbiDevices(vendorVal);
            showLoading("#form-loading", false);
        })
        .catch((err) => {
            console.error("Failed to load vendors/products:", err);
            showFeedback("#form-feedback", "Failed to load vendors/products.", true);
            showLoading("#form-loading", false);
        });
}

function populateVendors() {
    const vendorSel = document.getElementById("vendor");
    vendorSel.innerHTML = "";
    const keys = Object.keys(vendorProducts);
    console.log("Populating vendors with:", keys);
    keys.forEach(vendor => {
        const opt = document.createElement("option");
        opt.value = vendor;
        opt.textContent = vendor.charAt(0).toUpperCase() + vendor.slice(1);
        vendorSel.appendChild(opt);
    });
    console.log("Vendor select populated. Current value:", vendorSel.value);
}

function populateProducts(vendor) {
    const productSel = document.getElementById("product");
    productSel.innerHTML = "";
    const products = vendorProducts[vendor] || [];
    console.log(`Populating products for vendor ${vendor}:`, products);
    products.forEach(product => {
        const opt = document.createElement("option");
        opt.value = product;
        opt.textContent = product;
        productSel.appendChild(opt);
    });
    console.log("Product select populated. Current value:", productSel.value);
    loadPayloadTemplate(vendor, productSel.value);
}

function loadPayloadTemplate(vendor, product) {
    if (!vendor || !product) return;
    fetch(`/api/vendor-products/${encodeURIComponent(vendor)}/${encodeURIComponent(product)}/payloads`)
        .then(response => {
            if (!response.ok) throw new Error("Payload templates unavailable");
            return response.json();
        })
        .then(data => {
            const format = document.getElementById("format").value;
            const payload = data.payloads && data.payloads[format];
            if (payload) {
                document.getElementById("nb_payload").value = JSON.stringify(payload, null, 2);
            }
        })
        .catch(error => console.warn("Unable to load payload template:", error));
}

function refreshOperationalSummary() {
    Promise.all([
        fetch("/health/ready").then(response => response.json()),
        fetch("/metrics").then(response => response.text())
    ]).then(([health, metrics]) => {
        const values = {};
        const metricTotal = (metricName, status) => {
            const pattern = new RegExp("^" + metricName + "\\{[^}]*status=\"" + status + "\"[^}]*\\}\\s+([0-9.]+)", "gm");
            return [...metrics.matchAll(pattern)].reduce((total, match) => total + Number(match[1]), 0);
        };
        metrics.split("\n").forEach(line => {
            const match = line.match(/^([a-zA-Z0-9_]+)(?:\{[^}]*\})?\s+([0-9.]+)/);
            if (match) values[match[1]] = Number(match[2]);
        });
        document.getElementById("control-plane").textContent = health.status === "ready" ? "Ready" : "Degraded";
        document.getElementById("system-status").textContent = health.status === "ready" ? "Healthy" : "Degraded";
        document.getElementById("system-status").className = "status-pill " + (health.status === "ready" ? "healthy" : "warning");
        document.getElementById("queue-depth").textContent = values.change_queue_depth ?? 0;
        document.getElementById("validation-failures").textContent = values.config_validation_failures_total ?? 0;
        document.getElementById("tool-invocations").textContent = values.ai_tool_invocations_total ?? 0;
        const successfulDeployments = metricTotal("production_change_deployments_total", "success") + metricTotal("simulated_deployments_total", "success");
        const failedDeployments = metricTotal("production_change_deployments_total", "failure") + metricTotal("simulated_deployments_total", "failure");
        const deployments = successfulDeployments + failedDeployments;
        document.getElementById("deployment-success").textContent = deployments ? String(successfulDeployments) : "—";
        const commits = values.configuration_commits_total ?? 0;
        document.getElementById("deployment-detail").textContent = deployments ? `${successfulDeployments} successful / ${failedDeployments} failed` : (commits ? `${commits} candidate commit(s); not deployed` : "No deployments recorded");
        document.getElementById("fleet-health").textContent = health.status === "ready" ? "100%" : "At risk";
        document.getElementById("fleet-detail").textContent = "Control plane availability";
        document.getElementById("last-updated").textContent = new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
    }).catch(() => {
        document.getElementById("system-status").textContent = "Unavailable";
        document.getElementById("system-status").className = "status-pill warning";
    });
}


document.addEventListener("DOMContentLoaded", function() {
    document.getElementById('configForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const vendor = document.getElementById('vendor').value;
        const product = document.getElementById('product').value;
        const format = document.getElementById('format').value;
        const nb_payload = document.getElementById('nb_payload').value;
        const description = document.getElementById('description').value;

        let nb_payload_json;
        try {
            nb_payload_json = JSON.parse(nb_payload);
        } catch (err) {
            showFeedback("#form-feedback", "NB API Payload must be valid JSON.", true);
            return;
        }

        fetch('/generate-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                vendor,
                product,
                format,
                nb_payload: nb_payload_json,
                description
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.config) {
                document.getElementById('generated-config-block').style.display = 'block';
                document.getElementById('generated-config').innerText = data.config;
                // Always attach handler after block is shown
                document.getElementById('sim-push-btn').onclick = pushToSimDevice;
                showFeedback("#form-feedback", "Config generated successfully.", false);
            } else {
                showFeedback("#form-feedback", data.detail || "Failed to generate config.", true);
            }
        })
        .catch(e => {
            showFeedback("#form-feedback", "Failed to generate config.", true);
        });
    });
    fetchVendorProducts();
    refreshOperationalSummary();
    document.getElementById("refresh-dashboard").addEventListener("click", refreshOperationalSummary);
    refreshAgentConnections();
    document.getElementById("refresh-agents").addEventListener("click", refreshAgentConnections);

    document.getElementById("vendor").addEventListener("change", function() {
        populateProducts(this.value);
        populateSbiDevices(this.value);
        const historyVendor = document.getElementById("history-vendor");
        if (historyVendor) historyVendor.textContent = this.options[this.selectedIndex].text;
    });
    document.getElementById("product").addEventListener("change", function() {
        loadPayloadTemplate(document.getElementById("vendor").value, this.value);
    });
    document.getElementById("format").addEventListener("change", function() {
        loadPayloadTemplate(document.getElementById("vendor").value, document.getElementById("product").value);
    });

    const historyVendor = document.getElementById("history-vendor");
    if (historyVendor) {
        historyVendor.textContent = document.getElementById("vendor").options[0]?.text || "";
    }
    const simPushButton = document.getElementById('sim-push-btn');
    if (simPushButton) {
        simPushButton.addEventListener('click', pushToSimDevice);
    }
    // Optionally, fetch and render config history here
});



function pushToSimDevice() {
    console.log("Push to Device button clicked");
    clearFeedback();
    const config = document.getElementById('generated-config').innerText;
    const device = document.getElementById('sbi-device').value;
    document.getElementById('sim-push-status').innerText = 'Pushing...';
    document.getElementById('sim-push-result').style.display = 'none';
    document.getElementById('sim-push-result').innerText = '';
    fetch('/push-to-sim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: config, device: device })
    })
    .then(async r => {
        let data;
        try {
            data = await r.json();
        } catch (err) {
            data = { status: 'Invalid response', output: '' };
        }
        document.getElementById('sim-push-status').innerText = data.status || data.error || 'Done';
        document.getElementById('sim-push-result').style.display = 'block';
        document.getElementById('sim-push-result').innerText = data.output || data.error || JSON.stringify(data);
    })
    .catch(e => {
        document.getElementById('sim-push-status').innerText = 'Error';
        document.getElementById('sim-push-result').style.display = 'block';
        document.getElementById('sim-push-result').innerText = 'Push failed.';
    });
}
