# AI-Powered Multi-Vendor Network Configuration Manager

## Overview

This project is a production-ready, extensible, multi-vendor network configuration manager and simulator. It enables network engineers and operators to dynamically generate, version, test, and push device configurations for a wide range of vendors (Cisco, Nokia, Ericsson, Huawei, Openet, and more) through a modern web dashboard.

- **Backend:** FastAPI (Python)
- **Frontend:** Jinja2 templates, HTML/CSS/JS
- **Simulators:** Local Python socket servers for each vendor/product
- **Config Storage:** GitOps (versioned, rollback, commit history)

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
    A[User: Dashboard UI] -->|1. Select Vendor/Product, Enter Payload| B
    B[Frontend JS] -->|2. Fetch api_vendor_products| C
    B -->|3. Submit generate_config| D
    D[FastAPI Backend] -->|4. Generate Config| E
    E[Vendor Generators] -->|5. Return Config| D
    D -->|6. Return Config to UI| B
    B -->|7. Push to Device| F
    F[FastAPI Backend] -->|8. Connect to Simulator| G
    G[Vendor Simulator] -->|9. Receive CLI Commands| G
    F -->|10. Return Push Status/Output| B
    B -->|11. Show Output to User| A
    D -->|12. Commit Config (GitOps)| H[Git Repo]
