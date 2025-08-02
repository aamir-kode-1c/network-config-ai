// agents.js: Handles agent registration, listing, and pushing configs to physical hardware

document.addEventListener("DOMContentLoaded", function() {
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
