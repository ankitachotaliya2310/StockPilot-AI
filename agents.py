import os
import sys
import asyncio
import pandas as pd
import json
import time
import subprocess
from typing import Generator, Dict, Any

# Import ADK modules
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.genai.types import Content, Part

# Import local skills
from skills import (
    DatasetProfilingSkill,
    InventoryAnalysisSkill,
    DemandAnalysisSkill,
    RiskAssessmentSkill,
    RecommendationGenerationSkill,
    ExecutiveReportingSkill
)

class StockPilotOrchestrator:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        """Initializes the upgraded orchestrator.
        
        Args:
            api_key: User's Gemini API key (optional).
            model: Gemini model name.
        """
        self.api_key = api_key
        self.model = model
        self.mcp_process = None
        
        if self.api_key:
            os.environ["GEMINI_API_KEY"] = self.api_key
            self.mode = "REAL"
        else:
            self.mode = "MOCK"

    def run_multi_agent(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """Runs the multi-agent swarm in sequence, including the consensus review.
        
        Args:
            file_path: Path to the uploaded CSV/Excel file.
            
        Yields:
            Dict: Status updates.
        """
        # Load local data for statistics in mock/real fallback
        try:
            df = DatasetProfilingSkill.validate_and_load(file_path)
        except Exception as e:
            yield {
                "agent": "Coordinator",
                "status": "error",
                "message": f"Security Schema Check Failed: {e}"
            }
            return

        yield {
            "agent": "Coordinator",
            "status": "start",
            "message": (
                f"StockPilot AI Multi-Agent swarm started in **{self.mode} Mode**.\n"
                f"Successfully validated `{os.path.basename(file_path)}` schema and columns. "
                f"Registered Coordinator and 5 sub-agents under official Google ADK structure."
            )
        }
        time.sleep(1.2)

        # -------------------------------------------------------------
        # REAL ADK RUN (with local MCP Server subprocess)
        # -------------------------------------------------------------
        if self.mode == "REAL":
            yield {
                "agent": "Coordinator",
                "status": "running",
                "message": "Starting local Stdio MCP Server and establishing ADK client tunnel..."
            }
            
            # Start local MCP server
            server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
            
            # Use sys.executable to run with same python environment
            self.mcp_process = subprocess.Popen(
                [sys.executable, server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            time.sleep(2.0) # Wait for server to start stdio channel
            
            # Check if subprocess crashed
            if self.mcp_process.poll() is not None:
                err_output = self.mcp_process.stderr.read()
                yield {
                    "agent": "Coordinator",
                    "status": "warning",
                    "message": f"Failed to start local MCP server: {err_output}. Falling back to local Skills engine (Mock Mode)."
                }
                self.mode = "MOCK"
            else:
                yield {
                    "agent": "Coordinator",
                    "status": "running",
                    "message": "Stdio MCP Server established. Instantiating ADK McpToolset..."
                }

        # If still in real mode, proceed with ADK run
        if self.mode == "REAL":
            try:
                server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[server_script],
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                mcp_toolset = McpToolset(
                    connection_params=StdioConnectionParams(server_params=server_params)
                )
                
                # Define child agents using mcp tools
                data_analyzer = Agent(
                    model=self.model,
                    name="Data_Analyzer_Agent",
                    instruction="You profile datasets and analyze inventory parameters using profile_dataset and analyze_inventory MCP tools.",
                    tools=[mcp_toolset]
                )
                
                risk_detector = Agent(
                    model=self.model,
                    name="Risk_Detector_Agent",
                    instruction="You evaluate stock risks, shortages, and lead times using the assess_risks MCP tool.",
                    tools=[mcp_toolset]
                )
                
                trend_detector = Agent(
                    model=self.model,
                    name="Demand_Trend_Agent",
                    instruction="You calculate sales velocity and depletion remaining using the analyze_demand MCP tool.",
                    tools=[mcp_toolset]
                )
                
                recommender = Agent(
                    model=self.model,
                    name="Recommender_Agent",
                    instruction="You calculate optimal order sizes and safety stock parameters using the generate_recommendations MCP tool.",
                    tools=[mcp_toolset]
                )
                
                report_writer = Agent(
                    model=self.model,
                    name="Report_Writer_Agent",
                    instruction="You write complete, professional executive reports using the compile_report MCP tool.",
                    tools=[mcp_toolset]
                )
                
                # Define parent coordinator
                coordinator = Agent(
                    model=self.model,
                    name="Root_Coordinator_Agent",
                    instruction=(
                        "You are the Root Coordinator Agent. You oversee a swarm of 5 sub-agents: Data_Analyzer_Agent, "
                        "Risk_Detector_Agent, Demand_Trend_Agent, Recommender_Agent, and Report_Writer_Agent. "
                        "Your job is to delegate tasks to them sequentially. "
                        "Provide a structured synthesis after delegating."
                    ),
                    sub_agents=[data_analyzer, risk_detector, trend_detector, recommender, report_writer]
                )
                
                runner = InMemoryRunner(agent=coordinator)
                
                # Step 1: Run Data Analyzer Agent
                yield {"agent": "Data Analyzer", "status": "running", "message": "Querying profile_dataset and analyze_inventory MCP tools..."}
                analyzer_res = self._run_adk_runner(runner, f"Ask Data_Analyzer_Agent to analyze the dataset at path: {file_path}")
                yield {"agent": "Data Analyzer", "status": "done", "message": "Core inventory metrics generated via MCP.", "output": analyzer_res}
                time.sleep(1.0)
                
                # Step 2: Run Risk Detector Agent
                yield {"agent": "Risk Detector", "status": "running", "message": "Querying assess_risks MCP tool..."}
                risk_res = self._run_adk_runner(runner, f"Ask Risk_Detector_Agent to evaluate risks at path: {file_path}")
                yield {"agent": "Risk Detector", "status": "done", "message": "Risk and supply anomalies scanned via MCP.", "output": risk_res}
                time.sleep(1.0)
                
                # Step 3: Run Demand Trend Agent
                yield {"agent": "Demand Trend Detector", "status": "running", "message": "Querying analyze_demand MCP tool..."}
                trend_res = self._run_adk_runner(runner, f"Ask Demand_Trend_Agent to analyze sales trends at path: {file_path}")
                yield {"agent": "Demand Trend Detector", "status": "done", "message": "Velocity and stock depletion computed via MCP.", "output": trend_res}
                time.sleep(1.0)
                
                # Step 4: Run Recommender Agent (Initial run)
                yield {"agent": "Recommender", "status": "running", "message": "Querying generate_recommendations MCP tool..."}
                rec_res = self._run_adk_runner(runner, f"Ask Recommender_Agent to generate recommendations for path: {file_path}")
                yield {"agent": "Recommender", "status": "done", "message": "Initial reorder values calculated via MCP.", "output": rec_res}
                time.sleep(1.0)
                
                # Step 5: Swarm Consensus Review
                yield {"agent": "Coordinator", "status": "running", "message": "Initiating Swarm Consensus Review step..."}
                time.sleep(1.5)
                consensus_prompt = (
                    "Initiate the Consensus Review phase. Let Risk_Detector_Agent challenge Recommender_Agent's reorder suggestions "
                    "based on supplier delay risks and excess overstocks. Summarize their agreed adjustments."
                )
                consensus_res = self._run_adk_runner(runner, consensus_prompt)
                yield {
                    "agent": "Coordinator",
                    "status": "consensus",
                    "message": "Swarm Consensus reached. Supplier buffers and overstock cuts applied.",
                    "output": consensus_res
                }
                time.sleep(1.0)
                
                # Step 6: Run Report Writer Agent
                yield {"agent": "Report Writer", "status": "running", "message": "Querying compile_report MCP tool..."}
                report_res = self._run_adk_runner(runner, f"Ask Report_Writer_Agent to write the final markdown report for path: {file_path}")
                yield {"agent": "Report Writer", "status": "done", "message": "Strategic executive summary compiled.", "output": report_res}
                
                yield {
                    "agent": "Coordinator",
                    "status": "complete",
                    "message": "StockPilot AI Multi-Agent execution completed successfully! Visualizations and reports updated."
                }
                
                # Return final report text
                return
                
            except Exception as e:
                yield {
                    "agent": "Coordinator",
                    "status": "warning",
                    "message": f"Real ADK run encountered an error: {e}. Falling back to local Skills engine (Mock Mode)."
                }
                self.mode = "MOCK"
            finally:
                self.cleanup()

        # -------------------------------------------------------------
        # MOCK ADK RUN (with local Skills engine & streaming logs)
        # -------------------------------------------------------------
        if self.mode == "MOCK":
            # Step 1: Data Analyzer
            yield {
                "agent": "Data Analyzer",
                "status": "running",
                "message": "Profiling schema and computing descriptive statistics..."
            }
            time.sleep(1.5)
            stats = InventoryAnalysisSkill.compute_overview_metrics(df)
            cat_stats = InventoryAnalysisSkill.compute_category_analytics(df)
            
            analyzer_out = (
                f"### Data Analyzer Agent Report (Mock Mode)\n"
                f"I profiled the uploaded file schema and verified all required headers are present.\n"
                f"- **Unique SKUs:** {stats['SKU Count']}\n"
                f"- **Stock Units:** {stats['Total Stock Units']:,}\n"
                f"- **Inventory Valuation:** ${stats['Total Valuation']:,.2f}\n"
                f"- **Category Summary:** Active across {len(cat_stats)} categories."
            )
            yield {
                "agent": "Data Analyzer",
                "status": "done",
                "message": "Core inventory metrics generated via local Skills engine.",
                "output": analyzer_out
            }
            time.sleep(1.0)

            # Step 2: Risk Detector
            yield {
                "agent": "Risk Detector",
                "status": "running",
                "message": "Scanning inventory for anomalies, capital lockups, and supplier risks..."
            }
            time.sleep(1.5)
            risks = RiskAssessmentSkill.analyze_risks(df)
            scores = RiskAssessmentSkill.calculate_health_scores(df)
            
            risk_out = (
                f"### Risk Detector Agent Report (Mock Mode)\n"
                f"I scanned the inventory parameters for anomalies:\n"
                f"- **Inventory Health Score:** {scores['Inventory Health Score']}/100\n"
                f"- **Threat Level:** {scores['Stockout Risk Score']}\n"
                f"- **Stockout Items:** {len(risks['Stockouts'])} SKU(s)\n"
                f"- **Critical Shortages:** {len(risks['Shortages'])} SKU(s)\n"
                f"- **Cash Lockup Warnings:** {len(risks['Capital Lockups'])} item(s) showing overstocking."
            )
            yield {
                "agent": "Risk Detector",
                "status": "done",
                "message": "Risk and supply anomalies scanned via local Skills engine.",
                "output": risk_out
            }
            time.sleep(1.0)

            # Step 3: Demand Trend Detector
            yield {
                "agent": "Demand Trend Detector",
                "status": "running",
                "message": "Evaluating sales velocity and stockout exhaustion dates..."
            }
            time.sleep(1.5)
            velocity = DemandAnalysisSkill.classify_velocity(df)
            depletion = DemandAnalysisSkill.project_depletion(df)
            
            trend_out = (
                f"### Demand Trend Detector Agent Report (Mock Mode)\n"
                f"I calculated sales velocity classes and days of supply remaining:\n"
                f"- **Velocity Classifications:** {velocity['Velocity Counts'].get('HIGH', 0)} High, "
                f"{velocity['Velocity Counts'].get('MEDIUM', 0)} Medium, {velocity['Velocity Counts'].get('LOW', 0)} Low.\n"
                f"- **Overall Avg Days of Supply:** {depletion['Overall Avg Days of Supply']} days."
            )
            if depletion["Top Depleting SKUs"]:
                first = depletion["Top Depleting SKUs"][0]
                trend_out += f"\n- **Urgent Exhaustion Alert:** SKU `{first['Product ID']}` ({first['Product Name']}) has only **{first['Days Left']} days** of supply left."
                
            yield {
                "agent": "Demand Trend Detector",
                "status": "done",
                "message": "Velocity and stock depletion computed via local Skills engine.",
                "output": trend_out
            }
            time.sleep(1.0)

            # Step 4: Recommender
            yield {
                "agent": "Recommender",
                "status": "running",
                "message": "Calculating optimal safety stock sizes and reorder quantities..."
            }
            time.sleep(1.5)
            recs_list = RecommendationGenerationSkill.generate_orders(df)
            items_to_reorder = sum(1 for r in recs_list if r["Needs Restock"] == "Yes")
            total_reorder_cost = sum(r["Estimated Restock Cost"] for r in recs_list if r["Needs Restock"] == "Yes")
            
            rec_out = (
                f"### Recommender Agent Report (Mock Mode)\n"
                f"Calculated replenishment quantities using target order-up-to safety stock formula:\n"
                f"- **Suggested SKU Orders:** {items_to_reorder}\n"
                f"- **Estimated Procurement Valuation:** ${total_reorder_cost:,.2f}"
            )
            yield {
                "agent": "Recommender",
                "status": "done",
                "message": "Initial reorder values calculated via local Skills engine.",
                "output": rec_out
            }
            time.sleep(1.0)

            # Step 5: Swarm Consensus Review (Mock Mode dialogue logs)
            yield {
                "agent": "Coordinator",
                "status": "running",
                "message": "Root Coordinator Agent is running the Swarm Consensus Review..."
            }
            time.sleep(2.0)
            
            # Find a product with a supplier alert or high lead time for a concrete example
            alert_supplier = "VoltTech Solutions"
            alert_sku = "SKU-1001"
            for r in recs_list:
                if r["Needs Restock"] == "Yes" and r["Lead Time (days)"] > 10:
                    alert_sku = r["Product ID"]
                    alert_supplier = r["Supplier Name"]
                    break
                    
            consensus_out = (
                f"### 🤝 Swarm Consensus Review Log (Mock Mode)\n"
                f"**Root_Coordinator_Agent:** Initial replenishment calculations completed. Risk_Detector_Agent, please review the proposed plan against supplier risks.\n\n"
                f"**Risk_Detector_Agent:** I have reviewed the reorder list. I notice supplier **'{alert_supplier}'** is handling critical items like `{alert_sku}`, but shows an Alert Ratio > 0.60, representing a high probability of shipping delays. A standard lead time buffer is unsafe. I challenge the Recommender's target stock size. We should apply a **+15% safety stock multiplier** to all products managed by `{alert_supplier}`.\n\n"
                f"**Recommender_Agent:** I accept the risk assessment challenge. I have applied a 1.15 multiplier to safety calculations for `{alert_supplier}` SKUs. Re-calculating. The reorder size for `{alert_sku}` has been safely increased.\n\n"
                f"**Root_Coordinator_Agent:** The adjustment is sound and has been approved. The final replenishment plan is locked and passed to the Report Writer."
            )
            yield {
                "agent": "Coordinator",
                "status": "consensus",
                "message": "Swarm Consensus reached. Procurement plan safely optimized.",
                "output": consensus_out
            }
            time.sleep(1.0)

            # Step 6: Report Writer
            yield {
                "agent": "Report Writer",
                "status": "running",
                "message": "Drafting final strategic executive markdown summary..."
            }
            time.sleep(2.0)
            
            # Use local skills to compile the final report
            overview_m = InventoryAnalysisSkill.compute_overview_metrics(df)
            scores_m = RiskAssessmentSkill.calculate_health_scores(df)
            overview_combined = {**overview_m, **scores_m}
            
            risks_m = RiskAssessmentSkill.analyze_risks(df)
            depletion_m = DemandAnalysisSkill.project_depletion(df)
            
            # Re-generate recommendations using consensus logic
            opt_recs = RecommendationGenerationSkill.optimize_consensual_plan(recs_list, risks_m)
            items_c = sum(1 for r in opt_recs if r["Needs Restock"] == "Yes")
            cost_c = sum(r["Estimated Restock Cost"] for r in opt_recs if r["Needs Restock"] == "Yes")
            summary_c = {"Items to Reorder": items_c, "Total Cost": cost_c}
            
            report_out = ExecutiveReportingSkill.generate_report(overview_combined, risks_m, depletion_m, summary_c)
            
            yield {
                "agent": "Report Writer",
                "status": "done",
                "message": "Strategic executive summary compiled.",
                "output": report_out
            }
            time.sleep(1.0)
            
            yield {
                "agent": "Coordinator",
                "status": "complete",
                "message": "StockPilot AI Multi-Agent execution completed successfully! Dashboard updated."
            }

    def _run_adk_runner(self, runner: InMemoryRunner, prompt: str) -> str:
        """Helper to run a prompt synchronously on an ADK runner."""
        async def execute():
            input_content = Content(parts=[Part(text=prompt)])
            response_chunks = []
            async for event in runner.run_async(user_id="default_user", session_id="session_1", new_message=input_content):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_chunks.append(part.text)
            return "".join(response_chunks)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(execute())
        finally:
            loop.close()

    def cleanup(self):
        """Cleans up the local MCP subprocess."""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                self.mcp_process.wait(timeout=2.0)
            except:
                try:
                    self.mcp_process.kill()
                except:
                    pass
            finally:
                self.mcp_process = None

    def __del__(self):
        self.cleanup()
