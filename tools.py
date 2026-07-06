import pandas as pd
import numpy as np
import io
import json
from typing import Dict, Any, List

# Import OOP Skills
from skills import (
    DatasetProfilingSkill,
    InventoryAnalysisSkill,
    DemandAnalysisSkill,
    RiskAssessmentSkill,
    RecommendationGenerationSkill,
    ExecutiveReportingSkill
)

def load_data(file_data, file_name: str) -> pd.DataFrame:
    """Loads a CSV or Excel file into a pandas DataFrame (delegates to DatasetProfilingSkill)."""
    # Create a temporary file to leverage the path loader, or load directly
    # Since load_data gets bytes, we can use a temp file or standard StringIO
    suffix = ".csv" if file_name.endswith('.csv') else ".xlsx"
    import tempfile
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tfile.write(file_data)
    tfile.close()
    try:
        df = DatasetProfilingSkill.validate_and_load(tfile.name)
        return df
    finally:
        try:
            os.unlink(tfile.name)
        except:
            pass

def analyze_dataset(df: pd.DataFrame) -> dict:
    """Analyzes raw inventory data (delegates to InventoryAnalysisSkill)."""
    overview = InventoryAnalysisSkill.compute_overview_metrics(df)
    categories = InventoryAnalysisSkill.compute_category_analytics(df)
    
    return {
        "SKU Count": overview["SKU Count"],
        "Total Stock Units": overview["Total Stock Units"],
        "Total Valuation": overview["Total Valuation"],
        "Stockout SKUs": overview["Stockouts"],
        "Critical Shortage SKUs": overview["Critical Shortages"],
        "Reorder Alert SKUs": overview["Reorder Warnings"],
        "Overstock Alert SKUs": overview["Overstocked SKUs"],
        "Healthy SKUs": overview["Healthy SKUs"],
        "Category Breakdown": categories
    }

def detect_risk_anomalies(df: pd.DataFrame) -> dict:
    """Identifies risk anomalies and supplier warnings (delegates to RiskAssessmentSkill)."""
    risks = RiskAssessmentSkill.analyze_risks(df)
    return {
        "Total Stockout Items": len(risks["Stockouts"]),
        "Total Critical Shortage Items": len(risks["Shortages"]),
        "Stockouts": risks["Stockouts"],
        "Critical Shortages": risks["Shortages"],
        "Lead Time Exposed SKUs": risks["Exposed Lead Times"],
        "Capital Lockups (Top 5)": risks["Capital Lockups"],
        "Supplier Alerts": risks["Supplier Alerts"]
    }

def forecast_demand_seasonality(df: pd.DataFrame) -> dict:
    """Forecasts depletion days and sales velocity (delegates to DemandAnalysisSkill)."""
    velocity = DemandAnalysisSkill.classify_velocity(df)
    depletion = DemandAnalysisSkill.project_depletion(df)
    
    # Map back to original structure
    mapped_depleting = []
    for item in depletion["Top Depleting SKUs"]:
        mapped_depleting.append({
            "Product ID": item["Product ID"],
            "Product Name": item["Product Name"],
            "Daily Sales": item["Daily Sales"],
            "Current Stock": item["Current Stock"],
            "Days of Supply Remaining": item["Days Left"]
        })
        
    return {
        "Velocity Distribution": velocity["Velocity Counts"],
        "Fastest Depleting SKUs (Top 5)": mapped_depleting,
        "Average Days of Supply by Category": depletion["Category Avg Days of Supply"],
        "Overall Avg Days of Supply": depletion["Overall Avg Days of Supply"]
    }

def generate_recommendations(df: pd.DataFrame) -> dict:
    """Generates reorder plans and restock priorities (delegates to RecommendationGenerationSkill)."""
    base_recs = RecommendationGenerationSkill.generate_orders(df)
    risks = RiskAssessmentSkill.analyze_risks(df)
    optimized = RecommendationGenerationSkill.optimize_consensual_plan(base_recs, risks)
    
    items_to_restock = sum(1 for r in optimized if r["Needs Restock"] == "Yes")
    total_restock_cost = sum(r["Estimated Restock Cost"] for r in optimized if r["Needs Restock"] == "Yes")
    
    mapped_recs = []
    for r in optimized:
        mapped_recs.append({
            "Product ID": r["Product ID"],
            "Product Name": r["Product Name"],
            "Category": r["Category"],
            "Current Stock": r["Current Stock"],
            "Reorder Point": r["Reorder Point"],
            "Safety Stock": r["Safety Stock"],
            "Needs Restock": r["Needs Restock"],
            "Suggested Reorder Qty": r["Suggested Qty"],
            "Unit Cost": r["Unit Cost"],
            "Estimated Restock Cost": r["Estimated Restock Cost"],
            "Priority": r["Priority"],
            "Supplier Name": r["Supplier Name"]
        })
        
    return {
        "Total Restock Items": items_to_restock,
        "Total Restock Cost": round(total_restock_cost, 2),
        "Recommendations": mapped_recs
    }

def compile_executive_report(analysis_res: dict, risk_res: dict, trend_res: dict, rec_res: dict) -> str:
    """Assembles all analyses into the final Markdown report (delegates to ExecutiveReportingSkill)."""
    overview = {
        "SKU Count": analysis_res["SKU Count"],
        "Total Valuation": analysis_res["Total Valuation"],
        "Total Stock Units": analysis_res["Total Stock Units"],
        "Health Score": 90.0,
        "Risk Level": "NORMAL",
        "Stockouts": analysis_res["Stockout SKUs"],
        "Critical Shortages": analysis_res["Critical Shortage SKUs"],
        "Reorder Warnings": analysis_res["Reorder Alert SKUs"],
        "Overstocked SKUs": analysis_res["Overstock Alert SKUs"],
        "Healthy SKUs": analysis_res["Healthy SKUs"]
    }
    
    # Calculate health score dynamically
    unhealthy = overview["Stockouts"] + overview["Critical Shortages"] + overview["Overstocked SKUs"]
    overview["Health Score"] = round(max(0.0, min(100.0, 100.0 * (1 - unhealthy / overview["SKU Count"]))), 1)
    overview["Risk Level"] = "CRITICAL" if (overview["Stockouts"] + overview["Critical Shortages"]) / overview["SKU Count"] > 0.15 else "HIGH" if (overview["Stockouts"] + overview["Critical Shortages"]) / overview["SKU Count"] > 0.05 else "NORMAL"
    
    risks = {
        "Stockouts": risk_res["Stockouts"],
        "Exposed Lead Times": risk_res["Lead Time Exposed SKUs"],
        "Capital Lockups": risk_res["Capital Lockups (Top 5)"],
        "Supplier Alerts": risk_res["Supplier Alerts"]
    }
    
    # Map depleting SKUs
    mapped_depleting = []
    for item in trend_res["Fastest Depleting SKUs (Top 5)"]:
        mapped_depleting.append({
            "Product ID": item["Product ID"],
            "Product Name": item["Product Name"],
            "Category": "Unknown",
            "Current Stock": item["Current Stock"],
            "Daily Sales": item["Daily Sales"],
            "Days Left": item["Days of Supply Remaining"]
        })
        
    depletion = {
        "Overall Avg Days of Supply": trend_res["Overall Avg Days of Supply"],
        "Top Depleting SKUs": mapped_depleting
    }
    
    recs_summary = {
        "Items to Reorder": rec_res["Total Restock Items"],
        "Total Cost": rec_res["Total Restock Cost"]
    }
    
    return ExecutiveReportingSkill.generate_report(overview, risks, depletion, recs_summary)

# Keep compatibility wrappers for old agent scripts if invoked directly
def analyze_dataset_tool(file_path: str) -> str:
    """Loads inventory data from file_path and returns key analysis statistics as JSON."""
    df = DatasetProfilingSkill.validate_and_load(file_path)
    return json.dumps(analyze_dataset(df), indent=2)

def detect_risk_anomalies_tool(file_path: str) -> str:
    """Loads inventory data from file_path and returns high-risk inventory anomalies as JSON."""
    df = DatasetProfilingSkill.validate_and_load(file_path)
    return json.dumps(detect_risk_anomalies(df), indent=2)

def forecast_demand_seasonality_tool(file_path: str) -> str:
    """Loads inventory data from file_path and returns demand velocity and stock depletion forecasts as JSON."""
    df = DatasetProfilingSkill.validate_and_load(file_path)
    return json.dumps(forecast_demand_seasonality(df), indent=2)

def generate_recommendations_tool(file_path: str) -> str:
    """Loads inventory data from file_path and returns replenishment recommendations as JSON."""
    df = DatasetProfilingSkill.validate_and_load(file_path)
    return json.dumps(generate_recommendations(df), indent=2)
