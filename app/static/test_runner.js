const runButton = document.getElementById("run-tests");
const status = document.getElementById("test-status");
const detail = document.getElementById("test-detail");
const spinner = document.getElementById("test-spinner");
const results = document.getElementById("test-results");
const caseList = document.getElementById("test-case-list");
const caseCount = document.getElementById("case-count");

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[character]));
}

function renderResults(data) {
    results.innerHTML = data.results.map((result) => `
        <article class="panel test-result ${result.passed ? "test-passed" : "test-failed"}">
            <div class="panel-heading"><div><h2>${result.passed ? "PASS" : "FAIL"}</h2><p class="muted">${escapeHtml(result.command)}</p></div><span class="status-pill ${result.passed ? "healthy" : "warning"}">Exit ${result.exit_code}</span></div>
            <pre>${escapeHtml(result.output || "No output")}</pre>
        </article>
    `).join("");
}

function renderCases(data) {
    caseCount.textContent = `${data.cases.length} available`;
    caseList.innerHTML = data.cases.map((testCase, index) => `
        <div class="test-case-row">
            <div><strong>${index + 1}. ${escapeHtml(testCase.name)}${testCase.label ? ` <span class="status-pill neutral">${escapeHtml(testCase.label)}</span>` : ""}</strong><small>${escapeHtml(testCase.description)}</small><small>${escapeHtml(testCase.id)}</small></div>
            <button class="secondary run-case" data-case="${encodeURIComponent(testCase.id)}">Execute</button>
        </div>
    `).join("");
    caseList.querySelectorAll(".run-case").forEach((button) => {
        button.addEventListener("click", () => runCase(decodeURIComponent(button.dataset.case), button));
    });
}

async function runCase(testCase, button) {
    button.disabled = true;
    status.textContent = "Running selected test";
    detail.textContent = testCase;
    results.innerHTML = "";
    try {
        const response = await fetch("/api/tests/run-case", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({case: testCase})
        });
        const data = await response.json();
        renderResults(data);
        status.textContent = data.status === "passed" ? "Selected test passed" : "Selected test failed";
    } catch (error) {
        status.textContent = "Test runner unavailable";
        detail.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

runButton.addEventListener("click", async () => {
    runButton.disabled = true;
    spinner.hidden = false;
    status.textContent = "Running tests";
    detail.textContent = "The full suite and Cisco simulator workflow are in progress.";
    results.innerHTML = "";
    try {
        const response = await fetch("/api/tests/run", {method: "POST"});
        const data = await response.json();
        renderResults(data);
        status.textContent = data.status === "passed" ? "All tests passed" : "Test failures detected";
        detail.textContent = `${data.results.filter((item) => item.passed).length}/${data.results.length} test groups passed.`;
    } catch (error) {
        status.textContent = "Test runner unavailable";
        detail.textContent = error.message;
    } finally {
        runButton.disabled = false;
        spinner.hidden = true;
    }
});

fetch("/api/tests/cases")
    .then((response) => response.json())
    .then(renderCases)
    .catch((error) => {
        caseCount.textContent = "Unavailable";
        caseList.innerHTML = `<div class="connector-error">${escapeHtml(error.message)}</div>`;
    });
