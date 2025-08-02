# AI-Powered Multi-Vendor Network Configuration Manager

## Overview

This project is a production-ready, extensible, multi-vendor network configuration manager and simulator. It enables network engineers and operators to dynamically generate, version, test, and push device configurations for a wide range of vendors (Cisco, Nokia, Ericsson, Huawei, Openet, and more) through a modern web dashboard.

- **Backend:** FastAPI (Python)
- **Frontend:** Jinja2 templates, HTML/CSS/JS
- **Simulators:** Local Python socket servers for each vendor/product
- **Config Storage:** GitOps (versioned, rollback, commit history)

---

## Agentic AI Device Connectors

The Agentic AI Device Connectors module provides a robust, extensible E2E workflow for multi-vendor network configuration management, bridging the gap between northbound intent (NBI) and southbound device configuration (SBI) via agent microservices for each vendor.

### What It Does
- Lets you register and manage agent endpoints for each supported vendor (Cisco, Nokia, Ericsson, Huawei, Openet, etc.).
- Provides a built-in NBI Payload Generator to create NB API payloads and generate vendor-specific configs.
- Enables direct push of generated configs to physical or simulated hardware via agents, supporting SSH, NETCONF, or other protocols.
- Supports E2E testing, demo, and production workflows from the dashboard.

### Agentic AI Workflow Diagram

```mermaid
graph TD
    subgraph Dashboard
        A[NBI Payload Generator]
        B[Agent Registration]
        C[Push Config Form]
    end
    subgraph Backend
        D[Config Generator]
        E[Agent Registry]
        F[Push-to-Agent Endpoint]
    end
    subgraph Agents
        G[Cisco Agent]
        H[Nokia Agent]
        I[Ericsson Agent]
        J[Openet Agent]
    end
    subgraph Devices
        K[Cisco Device]
        L[Nokia Device]
        M[Ericsson Device]
        N[Openet Device]
    end

    A-->|Generate Config|D
    B-->|Register Agent|E
    C-->|Push Config|F
    D-->|Return Config|A
    F-->|Send Config|G
    F-->|Send Config|H
    F-->|Send Config|I
    F-->|Send Config|J
    G-->|Apply Config|K
    H-->|Apply Config|L
    I-->|Apply Config|M
    J-->|Apply Config|N
    G-->|Status/Output|F
    H-->|Status/Output|F
    I-->|Status/Output|F
    J-->|Status/Output|F
    F-->|Show Output|C
```

### Features & E2E Flow

- **NBI Payload Generator:**
  - Compose NB API payloads (JSON) for any vendor/product.
  - Generate vendor-specific CLI/JSON/XML/YANG configs instantly.
  - Copy generated config directly to the push form.

- **Agent Registration:**
  - Register agent endpoints (IP/port, token) for each vendor.
  - View agent status, last sync, and manage endpoints.

- **Config Push:**
  - Select vendor, paste/generated config, and push directly to the device via the registered agent.
  - Supports real hardware or simulators for safe E2E testing.

- **Agent Microservices:**
  - Each vendor agent runs as a microservice (FastAPI/Uvicorn, Docker-ready).
  - Agents connect to devices via SSH, NETCONF, or other protocols.
  - Agents return status/output to the dashboard for full visibility.

- **E2E Orchestration:**
  - From NBI intent to device config, the workflow is fully automated, observable, and extensible.
  - Supports demo, development, and production deployments.

---

## Example Screenshots

> _Replace the image URLs below with actual screenshots from your deployment._

**Dashboard - NBI Payload Generator and Agentic Push**

![Dashboard Screenshot](![alt text](image.png))

**Agent Registration and Status Table**

![Agents Screenshot](![alt text](image-1.png))

---

## More Deployment Instructions

### 1. Docker Compose (Recommended)

- Build and start all services (orchestrator and agents):
  ```bash
  docker-compose up --build
  ```
- Visit [http://localhost:8000](http://localhost:8000) for the dashboard.
- Agents will be available on ports 5001 (Nokia), 5003 (Cisco), 5004 (Ericsson), 5005 (Openet).

### 2. Standalone (Dev/Test)

- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Start the orchestrator:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
- Start agents (in separate terminals):
  ```bash
  python agents/agent_cisco_ssh.py
  python agents/agent_nokia_ssh.py
  # ...etc.
  ```

### 3. Production Best Practices
- Use HTTPS and secure credentials.
- Protect dashboard and API with authentication.
- Use Docker or Kubernetes for orchestration.
- Monitor logs and agent health.

---

## API Endpoint Documentation

### Orchestrator API

- `GET /api/vendor-products` — List available vendor/product pairs
- `POST /generate-config` — Generate vendor-specific config from NB API payload
- `POST /api/agents/register` — Register a new agent endpoint
- `GET /api/agents/list` — List all registered agents
- `POST /api/agents/push` — Push config to a registered agent

### Agent API (per vendor)

- `POST /push-config` — Receive and apply config to device (SSH, NETCONF, etc.)
  - Example payload:
    ```json
    {
      "config": "<CLI or XML config>",
      "token": "<optional>"
    }
    ```

---

## Docker Compose Quickstart

```bash
git clone https://github.com/aamir-kode-1c/network-config-ai.git
cd network-config-ai
docker-compose up --build
```
- Visit [http://localhost:8000](http://localhost:8000) to use the dashboard.
- Agents are available on their respective ports.

---

## Developers

<img src="docs/logo-dev-ai.png" alt="Dev AI Logo" width="48" height="48" style="vertical-align:middle; margin-right:8px;"/> Syed Aamir

---

## Key Features

- **Dynamic Vendor/Product Selection:** Supports multiple vendors and products with automatic dropdown population.
- **Config Generation:** Accepts NB API payload (JSON) and generates vendor/product-specific CLI, JSON, XML, or YANG configs.
- **Simulation & E2E Testing:** Pushes generated configs to local simulators for each vendor/product via SSH/CLI or NETCONF.
- **Version Control:** GitOps integration for config history, rollback, and audit.
- **User Feedback:** Modern dashboard with clear status, loading, and error messages.

---

## System Architecture & Workflow

```mermaid
graph TD
    A[User Dashboard UI] -->|1. Select Vendor_Product, Enter Payload| B
    B[Frontend JS] -->|2. Fetch api_vendor_products| C
    B -->|3. Submit generate_config| D
    D[FastAPI Backend] -->|4. Generate Config| E
    E[Vendor Generators] -->|5. Return Config| D
    D -->|6. Return Config to UI| B
    B -->|7. Push to Device| F
    F[FastAPI Backend] -->|8. Connect to Simulator| G
    G[Vendor Simulator] -->|9. Receive CLI Commands| G
    F -->|10. Return Push Status Output| B
    B -->|11. Show Output to User| A
    D -->|12. Commit Config GitOps| H[Git Repo]
```