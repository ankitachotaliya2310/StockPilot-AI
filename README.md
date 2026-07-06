# StockPilot AI ✈️

StockPilot AI is an enterprise-grade Multi-Agent inventory decision assistant that helps retailers optimize stock levels, prevent stockouts, reduce overstocking, and release locked-up working capital.

This application is built using the **Google Agent Development Kit (ADK)** for Python and **Streamlit**, and utilizes a localized **Model Context Protocol (MCP)** server architecture to separate reasoning and task execution.

---

## 🏗️ System Architecture

StockPilot AI uses a clean, separated microservice-like structure:

```
                  [Uploaded Dataset]
                          │
                          ▼
            [Root_Coordinator_Agent (ADK)]
                          │
             ┌────────────┼────────────┬─────────────┐
             ▼            ▼            ▼             ▼
       [DataAnalyzer] [RiskDetector] [DemandTrend] [Recommender]
             │            │            │             │
             └────────────┼────────────┴─────────────┘
                          ▼  (Queries tools via MCP)
                    [Stdio Transport]
                          │
                          ▼
             [StockPilot-MCP-Server (FastMCP)]
                          │
                          ▼
                  [Reusable Skills]
             ├─ DatasetProfilingSkill
             ├─ InventoryAnalysisSkill
             ├─ DemandAnalysisSkill
             ├─ RiskAssessmentSkill
             └─ RecommendationGenerationSkill
```

### 1. Reusable OOP Agent Skills (`skills.py`)
Core inventory calculations and data science pipelines are encapsulated as clean, reusable Python classes. This keeps business logic completely decoupled from agent configurations:
* **`DatasetProfilingSkill`:** Handles file loading, type coercion, size checks, and column validation.
* **`InventoryAnalysisSkill`:** Computes base inventory counts, valuations, and categories.
* **`DemandAnalysisSkill`:** Segments SKUs by sales velocity and projects depletion days.
* **`RiskAssessmentSkill`:** Scans for stockouts, safety stock warnings, cash bottlenecks, and calculates health scores.
* **`RecommendationGenerationSkill`:** Generates optimized restock purchase orders and applies swarm consensus buffers.
* **`ExecutiveReportingSkill`:** Compiles final markdown executive briefs.

### 2. Local FastMCP stdio Server (`mcp_server.py`)
Exposes the reusable OOP Skills to the agents as official MCP tools over a stdio transport layer:
* `profile_dataset(file_path)`
* `analyze_inventory(file_path)`
* `assess_risks(file_path)`
* `analyze_demand(file_path)`
* `generate_recommendations(file_path)`
* `compile_report(file_path)`

### 3. Google ADK Swarm Orchestration (`agents.py`)
* Implements a parent-child delegation model: `Root_Coordinator_Agent` manages `Data_Analyzer`, `Risk_Detector`, `Demand_Trend_Detector`, `Recommender`, and `Report_Writer` sub-agents.
* Instantiates `McpToolset` with `StdioConnectionParams` to spawn the local `mcp_server.py` subprocess, allowing agents to execute tasks by calling MCP tools.
* Executes a **Swarm Consensus Review Phase** where the Coordinator has the Risk Detector and Recommender challenge each other's outputs to establish a safe, risk-hedged purchase order plan.

---

## 🔒 Enterprise Security Features

* **Strict Input Validation:** The system parses files in-memory, validates column names, enforces numeric boundaries (no negative inventory), and restricts uploads to 10MB to prevent denial-of-service.
* **API Key Safety:** Keys are securely contained in Streamlit's `st.session_state` or loaded from `.env` files. They are never written to disk, logged, or exposed in error messages.
* **Safe Subprocesses:** Stdio MCP connections are sandboxed to the local workspace folder. Standard logs are routed to `sys.stderr` to prevent JSON-RPC transport corruption.

---

## ⚡ Setup & Launch

### 1. Installation
Install the upgraded requirements:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file based on `.env.example`:
```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run Automated Tests
Execute the verification suite to check the skills classes, MCP tool conversions, and agent loops:
```bash
python -X utf8 verify_system.py
```

### 4. Start Dashboard
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** to access the Mission Control Room.
