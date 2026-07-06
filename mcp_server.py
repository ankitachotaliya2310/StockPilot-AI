import sys
import os
import json
from fastmcp import FastMCP

# Add local path to sys.path to ensure local imports work inside the subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import (
    DatasetProfilingSkill,
    InventoryAnalysisSkill,
    DemandAnalysisSkill,
    RiskAssessmentSkill,
    RecommendationGenerationSkill,
    ExecutiveReportingSkill
)

# 1. Initialize FastMCP server
mcp = FastMCP("StockPilot-MCP-Server")

# Log helper
def log_info(msg: str):
    print(f"[StockPilot-MCP] {msg}", file=sys.stderr, flush=True)

# 2. Define MCP Tools

@mcp.tool()
def profile_dataset(file_path: str) -> str:
    """Validates the CSV/Excel file schema and profiles its completeness.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Profiling dataset at {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        profile = DatasetProfilingSkill.get_profile(df)
        return json.dumps({
            "status": "success",
            "rows": df.shape[0],
            "columns": list(df.columns),
            "profile": profile
        }, indent=2)
    except Exception as e:
        log_info(f"Error in profile_dataset: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def analyze_inventory(file_path: str) -> str:
    """Calculates core inventory metrics, valuations, and category-level analysis.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Analyzing inventory at {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        overview = InventoryAnalysisSkill.compute_overview_metrics(df)
        categories = InventoryAnalysisSkill.compute_category_analytics(df)
        return json.dumps({
            "status": "success",
            "overview": overview,
            "category_breakdown": categories
        }, indent=2)
    except Exception as e:
        log_info(f"Error in analyze_inventory: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def assess_risks(file_path: str) -> str:
    """Identifies inventory risks, stockouts, shortages, lead times, and capital lockups.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Assessing risks at {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        risks = RiskAssessmentSkill.analyze_risks(df)
        scores = RiskAssessmentSkill.calculate_health_scores(df)
        return json.dumps({
            "status": "success",
            "risks_summary": risks,
            "scores": scores
        }, indent=2)
    except Exception as e:
        log_info(f"Error in assess_risks: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def analyze_demand(file_path: str) -> str:
    """Analyzes daily sales velocity and projects stock depletion dates.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Analyzing demand at {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        velocity = DemandAnalysisSkill.classify_velocity(df)
        depletion = DemandAnalysisSkill.project_depletion(df)
        return json.dumps({
            "status": "success",
            "velocity": {
                "counts": velocity["Velocity Counts"]
            },
            "depletion": depletion
        }, indent=2)
    except Exception as e:
        log_info(f"Error in analyze_demand: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def generate_recommendations(file_path: str) -> str:
    """Calculates safety stocks, reorder points, and recommended order quantities.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Generating recommendations for {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        base_recs = RecommendationGenerationSkill.generate_orders(df)
        risks = RiskAssessmentSkill.analyze_risks(df)
        
        # Apply Consensus Logic
        optimized_recs = RecommendationGenerationSkill.optimize_consensual_plan(base_recs, risks)
        
        # Summarize costs
        items_count = sum(1 for r in optimized_recs if r["Needs Restock"] == "Yes")
        total_cost = sum(r["Estimated Restock Cost"] for r in optimized_recs if r["Needs Restock"] == "Yes")
        
        return json.dumps({
            "status": "success",
            "summary": {
                "Items to Reorder": items_count,
                "Total Cost": round(total_cost, 2)
            },
            "recommendations": optimized_recs
        }, indent=2)
    except Exception as e:
        log_info(f"Error in generate_recommendations: {e}")
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def compile_report(file_path: str) -> str:
    """Compiles a complete strategic executive summary report in Markdown format.
    
    Args:
        file_path: The file path to the CSV or Excel file.
    """
    log_info(f"Compiling report for {file_path}")
    try:
        df = DatasetProfilingSkill.validate_and_load(file_path)
        
        overview_metrics = InventoryAnalysisSkill.compute_overview_metrics(df)
        scores = RiskAssessmentSkill.calculate_health_scores(df)
        overview = {**overview_metrics, **scores}
        
        risks = RiskAssessmentSkill.analyze_risks(df)
        depletion = DemandAnalysisSkill.project_depletion(df)
        
        # Get optimized recommendations
        base_recs = RecommendationGenerationSkill.generate_orders(df)
        optimized_recs = RecommendationGenerationSkill.optimize_consensual_plan(base_recs, risks)
        
        items_count = sum(1 for r in optimized_recs if r["Needs Restock"] == "Yes")
        total_cost = sum(r["Estimated Restock Cost"] for r in optimized_recs if r["Needs Restock"] == "Yes")
        recs_summary = {"Items to Reorder": items_count, "Total Cost": total_cost}
        
        report = ExecutiveReportingSkill.generate_report(overview, risks, depletion, recs_summary)
        return report
    except Exception as e:
        log_info(f"Error in compile_report: {e}")
        return f"Error compiling report: {e}"

# 3. Main runner
if __name__ == "__main__":
    log_info("Starting StockPilot MCP Server stdio channel")
    mcp.run()
