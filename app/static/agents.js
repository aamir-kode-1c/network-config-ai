// agents.js: Handles agent registration, listing, and pushing configs to physical hardware

const vendorProducts = {
    cisco: ["ASR 9000", "ISR 4000"],
    nokia: ["7750 SR", "7250 IXR"],
    ericsson: ["Router 6000"],
    huawei: ["NE40E"],
    openet: ["Policy Manager"]
};

const vendorSamples = {
    cisco: JSON.stringify({
        interface: "GigabitEthernet0/2/0/1",
        ip: "192.168.50.1",
        subnet: "255.255.255.252",
        description: "Uplink to Data Center",
        admin_state: "up",
        mtu: 9100,
        vrf: "core-vrf",
        custom_param: "test_value"
    }, null, 2),
    nokia: JSON.stringify({
        interface: "1/1/1",
        ip: "10.10.100.1",
        subnet: "30",
        description: "Nokia uplink",
        admin_state: "up",
        mtu: 9000,
        vrf: "customer-vpn"
    }, null, 2),
    ericsson: JSON.stringify({
        interface: "ge-0/0/1",
        ip: "172.16.1.1",
        subnet: "30",
        description: "Ericsson uplink",
        admin_state: "up",
        mtu: 9000,
        vrf: "customer-vpn"
    }, null, 2),
    huawei: JSON.stringify({
        interface: "GigabitEthernet0/0/1",
        ip: "192.16.1.1",
        subnet: "255.255.255.0",
        description: "Huawei uplink",
        admin_state: "up",
        mtu: 1500,
        vrf: "default"
    }, null, 2),
    openet: JSON.stringify({
        interface: "pm0",
        ip: "10.0.0.10",
        subnet: "24",
        description: "Openet Policy",
        admin_state: "up"
    }, null, 2)
};

document.addEventListener("DOMContentLoaded", function() {
    // NBI Payload Generator enhancements
    const nbiVendor = document.getElementById("nbi-vendor");
    const nbiProduct = document.getElementById("nbi-product");
    const pushVendor = document.getElementById("push-vendor");
    const nbiPayload = document.getElementById("nbi-payload");

    // Auto-fill product and sync vendor dropdowns
    nbiVendor.addEventListener("change", function() {
        const vendor = this.value;
        nbiProduct.value = vendorProducts[vendor] ? vendorProducts[vendor][0] : "";
        pushVendor.value = vendor;
    });
    pushVendor.addEventListener("change", function() {
        nbiVendor.value = this.value;
        nbiProduct.value = vendorProducts[this.value] ? vendorProducts[this.value][0] : "";
    });

    // Insert sample payload
    const insertSampleBtn = document.createElement("button");
    insertSampleBtn.type = "button";
    insertSampleBtn.id = "insert-sample-nbi";
    insertSampleBtn.textContent = "Insert Sample Payload";
    nbiPayload.parentNode.insertBefore(insertSampleBtn, nbiPayload.nextSibling);
    insertSampleBtn.addEventListener("click", function() {
        const vendor = nbiVendor.value;
        nbiPayload.value = vendorSamples[vendor] || "";
    });

    // NBI Payload Generator
    document.getElementById("nbi-generator-form").addEventListener("submit", async function(e) {
        e.preventDefault();
        const vendor = nbiVendor.value;
        const product = nbiProduct.value;
        const format = document.getElementById("nbi-format").value;
        const payloadText = nbiPayload.value;
        let payload;
        try {
            payload = JSON.parse(payloadText);
        } catch (err) {
            showNbiGeneratorFeedback("Invalid JSON payload", true);
            return;
        }
        try {
            const resp = await fetch("/generate-config", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({vendor, product, format, nb_payload: payload})
            });
            const data = await resp.json();
            if (resp.ok && data.config) {
                document.getElementById("nbi-generated-config").value = data.config;
                document.getElementById("nbi-config-block").style.display = "block";
                showNbiGeneratorFeedback("Config generated.");
                // Direct push: auto-copy to push form
                document.getElementById("push-config").value = data.config;
            } else {
                showNbiGeneratorFeedback(data.error || "Generation failed", true);
            }
        } catch (err) {
            showNbiGeneratorFeedback("Error: " + err, true);
        }
    });

    document.getElementById("copy-nbi-config").addEventListener("click", function() {
        const config = document.getElementById("nbi-generated-config").value;
        document.getElementById("push-config").value = config;
    });

    // NBI Payload Generator
    document.getElementById("nbi-generator-form").addEventListener("submit", async function(e) {
        e.preventDefault();
        const vendor = document.getElementById("nbi-vendor").value;
        const product = document.getElementById("nbi-product").value;
        const format = document.getElementById("nbi-format").value;
        const payloadText = document.getElementById("nbi-payload").value;
        let payload;
        try {
            payload = JSON.parse(payloadText);
        } catch (err) {
            showNbiGeneratorFeedback("Invalid JSON payload", true);
            return;
        }
        try {
            const resp = await fetch("/generate-config", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({vendor, product, format, nb_payload: payload})
            });
            const data = await resp.json();
            if (resp.ok && data.config) {
                document.getElementById("nbi-generated-config").value = data.config;
                document.getElementById("nbi-config-block").style.display = "block";
                showNbiGeneratorFeedback("Config generated.");
            } else {
                showNbiGeneratorFeedback(data.error || "Generation failed", true);
            }
        } catch (err) {
            showNbiGeneratorFeedback("Error: " + err, true);
        }
    });

    document.getElementById("copy-nbi-config").addEventListener("click", function() {
        const config = document.getElementById("nbi-generated-config").value;
        document.getElementById("push-config").value = config;
    });

    // Register Agent form
    document.getElementById("agent-form").addEventListener("submit", async function(e) {
        e.preventDefault();
        const vendor = document.getElementById("vendor").value;
        const endpoint = document.getElementById("agent-address").value;
        const token = document.getElementById("auth-token").value;
        try {
            const resp = await fetch("/api/agents/register", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({vendor, endpoint, token})
            });
            const data = await resp.json();
            if (resp.ok) {
                showAgentFeedback("Agent registered for " + vendor);
                loadAgents();
            } else {
                showAgentFeedback(data.status || "Registration failed", true);
            }
        } catch (err) {
            showAgentFeedback("Error: " + err, true);
        }
    });

    document.getElementById("push-agent-form").addEventListener("submit", async function(e) {
        e.preventDefault();
        const vendor = document.getElementById("push-vendor").value;
        const config = document.getElementById("push-config").value;
        try {
            const resp = await fetch("/api/agents/push", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({vendor, config})
            });
            const data = await resp.json();
            if (resp.ok) {
                showPushAgentFeedback(data.status || "Push success");
            } else {
                showPushAgentFeedback(data.status || "Push failed", true);
            }
        } catch (err) {
            showPushAgentFeedback("Error: " + err, true);
        }
    });

    // Load registered agents from backend
    loadAgents();
});

async function loadAgents() {
    try {
        const resp = await fetch("/api/agents/list");
        const agents = await resp.json();
        renderAgentsTable(agents);
    } catch (err) {
        renderAgentsTable([]);
        showAgentFeedback("Could not load agents", true);
    }
}


function showAgentFeedback(msg, isError) {
    const el = document.getElementById("agent-form-feedback");
    el.textContent = msg;
    el.className = "feedback" + (isError ? " error" : "");
    el.style.display = msg ? "block" : "none";
}

function showPushAgentFeedback(msg, isError) {
    const el = document.getElementById("push-agent-feedback");
    el.textContent = msg;
    el.className = "feedback" + (isError ? " error" : "");
    el.style.display = msg ? "block" : "none";
}

function renderAgentsTable(agents) {
    const tbody = document.getElementById("agents-table").querySelector("tbody");
    tbody.innerHTML = "";
    agents.forEach(agent => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${agent.vendor}</td><td>${agent.endpoint}</td><td>${agent.status}</td><td>${agent.lastSync}</td><td>${agent.actions}</td>`;
        tbody.appendChild(tr);
    });
}
