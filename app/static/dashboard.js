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

    document.getElementById("vendor").addEventListener("change", function() {
        populateProducts(this.value);
        populateSbiDevices(this.value);
        document.getElementById("history-vendor").textContent = this.options[this.selectedIndex].text;
    });

    document.getElementById("configForm").addEventListener("submit", function(e) {
        e.preventDefault();
        clearFeedback();
        showLoading("#form-loading", true);

        // Validate JSON
        let nbPayload = document.getElementById("nb_payload").value;
        try {
            JSON.parse(nbPayload);
        } catch (err) {
            showFeedback("#form-feedback", "NB API Payload must be valid JSON.", true);
            showLoading("#form-loading", false);
            return;
        }

        // Submit form via fetch
        const formData = new FormData(this);
        fetch("/dashboard", {
            method: "POST",
            body: formData
        })
        .then(r => r.text())
        .then(html => {
            // Parse returned HTML for config and errors
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const config = doc.querySelector("#generated-config");
            const error = doc.querySelector(".feedback.error");
            if (config) {
                document.getElementById("generated-config").textContent = config.textContent;
                document.getElementById("generated-config-block").style.display = "block";
            } else {
                document.getElementById("generated-config-block").style.display = "none";
            }
            if (error) {
                showFeedback("#output-error", error.textContent, true);
            } else {
                showFeedback("#output-error", "");
            }
            showLoading("#form-loading", false);
        })
        .then(() => {
            const config = document.getElementById('generated-config').innerText;
            const vendor = document.getElementById('vendor').value;
            const product = document.getElementById('product').value;
            document.getElementById('test-simulator-btn').addEventListener('click', () => {
                fetch('/api/test-simulator', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ config, vendor, product })
                })
                .then(r => r.json())
                .then(data => {
                    showFeedback("#simulator-output", data.output);
                })
                .catch(e => {
                    showFeedback("#simulator-output", 'Error', true);
                });
            });
        })
        .catch(() => {
            showFeedback("#form-feedback", "Failed to generate config.", true);
            showLoading("#form-loading", false);
        });
    });

    document.getElementById("history-vendor").textContent = document.getElementById("vendor").options[0]?.text || "";
    document.getElementById('sim-push-btn').addEventListener('click', pushToSimDevice);
    // Optionally, fetch and render config history here
});

function triggerAgenticUpdate() {
    document.getElementById('agentic-update-status').innerText = 'Running...';
    fetch('/run-agentic-update', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            document.getElementById('agentic-update-status').innerText = data.status || 'Done';
        })
        .catch(e => {
            document.getElementById('agentic-update-status').innerText = 'Error';
        });
}

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
