# StockPilot AI – Upgraded Technical Architecture & Design Document

This document provides an in-depth explanation of the upgraded architecture, local MCP server interfaces, reusable OOP Skills, and security boundaries implemented in **StockPilot AI**.

---

## 🏗️ Upgraded Swarm Architecture (Google ADK)

StockPilot AI utilizes the **Google Agent Development Kit (ADK)** to establish a hierarchical, parent-child multi-agent system. Instead of flat script execution, the system employs model-driven delegation and transport isolation.

### 1. Hierarchical Delegation Flow
* **Root Coordinator:** Instantiated as the parent agent. It is given a list of `sub_agents` and coordinates the task flow.
* **Child Agents:** Sub-agents are configured with `mode="single_turn"` or `mode="task"`. The parent agent delegates tasks to them using automatically-generated transfer tools.
* **Consensus Review Phase:** The Coordinator agent orchestrates a discussion loop. The Risk Detector agent evaluates the Recommender's replenishment quantities against supplier delay risks and overstock valuation alerts. Once a consensus is reached, the adjusted procurement plan is passed to the Report Writer agent.

### 2. Local MCP Server stdio Integration
The sub-agents are decoupled from direct Python execution. They are instead linked to a local Stdio process runner:
* **Connection Type:** Stdio connection parameters (`StdioConnectionParams` wrapping `StdioServerParameters`).
* **Process Lifecycle:** The orchestrator launches a Python subprocess running `mcp_server.py`. The ADK `McpToolset` initiates a client tunnel that queries and runs tools dynamically.
* **Safety:** By routing tool calls through standard JSON-RPC JSON structures, we prevent agents from executing arbitrary python code on the host, achieving high transport security.

---

## 🧮 Reusable OOP Skills (`skills.py`)

All computations are separated into modular, testable, and reusable Python classes:

### 1. `DatasetProfilingSkill`
* Enforces schema constraints on columns.
* Parses CSV and Excel files into typed pandas DataFrames.
* Gracefully filters out negative stock, cost, or lead time inputs.

### 2. `InventoryAnalysisSkill`
* Calculates descriptive statistics (Sku Counts, Valuations, Categories, Healthy Units).

### 3. `DemandAnalysisSkill`
* Computes daily sales velocity and Days of Supply remaining.
* Tier classifications: HIGH (sales > 5/day), MEDIUM (1.5 - 5), and LOW (< 1.5).

### 4. `RiskAssessmentSkill`
* Computes the **Inventory Health Score**:
  $$\text{Health Score} = 100 \times \left(1 - \frac{\text{Stockouts} + \text{Shortages} + \text{Overstocks}}{\text{Total SKUs}}\right)$$
* Determines **Stockout Risk Scores** (CRITICAL, HIGH, NORMAL).
* Identifies overstock valuation cash lockups and supplier dependencies.

### 5. `RecommendationGenerationSkill`
* Computes replenishment orders using the mathematical target stock formula.
* Implements the **Consensus Safety Adjustments**:
  * If a supplier has an Alert Ratio > 0.6, increase safety stock and suggested order size by **15%**.
  * If lead time > 15 days, add a **10%** safety buffer.

---

## 🔒 Enterprise Security & Safety Checkpoints

1. **Upload Size Restrictions:** File bytes are limited to 10MB in `app.py` to prevent heap exhaustion.
2. **Schema & Header Verification:** Files are inspected immediately upon upload. Any missing column terminates execution with a structured validation error before agents are spawned.
3. **No-Stdout Pollution Policy:** In stdio-based MCP servers, stdout is reserved for JSON-RPC packets. The `mcp_server.py` redirects all logging to `sys.stderr` to prevent protocol corruption.
4. **Secret Variable Masking:** Gemini API keys are entered via Streamlit password inputs or loaded from `.env` files. They are stored in session state memory and never logged, printed, or saved.

---

## 📈 Visualizations & SaaS UI Components

* **Health Gauge:** A dynamic semi-circle gauge indicating the Inventory Health Score, colored by risk zone.
* **Capital Lockup Bar Chart:** Visualizes excess inventory valuation tied up in overstocked SKUs.
* **Treemap:** Hierarchical representation of total stock valuation divided by Category and Product Name.
* **SaaS Timeline UI:** Live collaboration log rendered as an enterprise timeline using premium backdrop-blur styling.
