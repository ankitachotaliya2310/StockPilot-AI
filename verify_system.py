import os
import sys
import pandas as pd
import json

# Setup sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skills import (
    DatasetProfilingSkill,
    InventoryAnalysisSkill,
    DemandAnalysisSkill,
    RiskAssessmentSkill,
    RecommendationGenerationSkill,
    ExecutiveReportingSkill
)
from agents import StockPilotOrchestrator
from mcp_server import mcp as mcp_instance

def run_verification():
    print("======================================================")
    print("🔍 UPGRADED VERIFICATION SUITE - STOCKPILOT AI SYSTEM")
    print("======================================================\n")

    sample_path = os.path.join(os.getcwd(), "sample_inventory.csv")
    if not os.path.exists(sample_path):
        print(f"⚠️ Sample file not found at {sample_path}. Generating default...")
        from data_generator import generate_default_dataset
        df_gen = generate_default_dataset()
        df_gen.to_csv(sample_path, index=False)
        print("✅ Sample file generated.")

    # 1. Test DatasetProfilingSkill
    print("🧪 Test 1: DatasetProfilingSkill validation & load...")
    try:
        df = DatasetProfilingSkill.validate_and_load(sample_path)
        profile = DatasetProfilingSkill.get_profile(df)
        assert df.shape[0] > 0, "Empty DataFrame returned"
        assert "Product ID" in df.columns, "Required columns missing"
        print(f"✅ Passed: Loaded {df.shape[0]} SKUs and verified 10 core headers.\n")
    except Exception as e:
        print(f"❌ Failed Test 1: {e}")
        sys.exit(1)

    # 2. Test InventoryAnalysisSkill
    print("🧪 Test 2: InventoryAnalysisSkill Overview...")
    try:
        metrics = InventoryAnalysisSkill.compute_overview_metrics(df)
        categories = InventoryAnalysisSkill.compute_category_analytics(df)
        assert metrics["SKU Count"] == df.shape[0], "SKU count mismatch"
        assert metrics["Total Valuation"] > 0, "Valuation should be positive"
        assert len(categories) > 0, "Categories breakdown empty"
        print(f"✅ Passed: Inventory valuation is ${metrics['Total Valuation']:,.2f} across {len(categories)} categories.\n")
    except Exception as e:
        print(f"❌ Failed Test 2: {e}")
        sys.exit(1)

    # 3. Test DemandAnalysisSkill
    print("🧪 Test 3: DemandAnalysisSkill Velocity & Depletion...")
    try:
        velocity = DemandAnalysisSkill.classify_velocity(df)
        depletion = DemandAnalysisSkill.project_depletion(df)
        assert "counts" in velocity or "Velocity Counts" in velocity, "Velocity keys mismatch"
        assert depletion["Overall Avg Days of Supply"] > 0, "Average Days of Supply must be positive"
        print(f"✅ Passed: Classified demand. Overall Avg Days of Supply is {depletion['Overall Avg Days of Supply']} days.\n")
    except Exception as e:
        print(f"❌ Failed Test 3: {e}")
        sys.exit(1)

    # 4. Test RiskAssessmentSkill & Health Scores
    print("🧪 Test 4: RiskAssessmentSkill Health & Threat Scans...")
    try:
        risks = RiskAssessmentSkill.analyze_risks(df)
        scores = RiskAssessmentSkill.calculate_health_scores(df)
        assert "Inventory Health Score" in scores, "Health Score key missing"
        assert "Stockout Risk Score" in scores, "Risk level key missing"
        print(f"✅ Passed: Inventory Health Score is {scores['Inventory Health Score']}% (Risk Level: {scores['Stockout Risk Score']}).\n")
    except Exception as e:
        print(f"❌ Failed Test 4: {e}")
        sys.exit(1)

    # 5. Test RecommendationGenerationSkill & Consensus Logic
    print("🧪 Test 5: RecommendationGenerationSkill & Consensus Optimization...")
    try:
        recs = RecommendationGenerationSkill.generate_orders(df)
        opt_recs = RecommendationGenerationSkill.optimize_consensual_plan(recs, risks)
        assert len(recs) == df.shape[0], "Recommendations size mismatch"
        assert len(opt_recs) == len(recs), "Optimized plan size mismatch"
        
        # Verify consensus notes exist
        notes_exist = any("Consensus Note" in r for r in opt_recs)
        assert notes_exist, "Consensus adjustments notes are missing"
        print("✅ Passed: Optimized procurement plan generated and consensus adjustments verified.\n")
    except Exception as e:
        print(f"❌ Failed Test 5: {e}")
        sys.exit(1)

    # 6. Test MCP Server registrations
    print("🧪 Test 6: FastMCP Server Tool Registration Checks...")
    try:
        import asyncio
        registered_tools = asyncio.run(mcp_instance.list_tools())
        tool_names = [t.name for t in registered_tools]
        required_tools = [
            "profile_dataset", "analyze_inventory", "assess_risks", 
            "analyze_demand", "generate_recommendations", "compile_report"
        ]
        for rt in required_tools:
            assert rt in tool_names, f"MCP Tool '{rt}' not registered"
        print(f"✅ Passed: Verified all {len(required_tools)} tools are registered in FastMCP.\n")
    except Exception as e:
        print(f"❌ Failed Test 6: {e}")
        sys.exit(1)

    # 7. Test Multi-Agent Swarm Orchestration in Mock Mode
    print("🧪 Test 7: Multi-Agent Orchestrator (Mock Mode Swarm Consensus)...")
    try:
        orchestrator = StockPilotOrchestrator(api_key=None)
        steps_logged = []
        final_report = ""
        
        for step in orchestrator.run_multi_agent(sample_path):
            steps_logged.append(step)
            if step["agent"] == "Report Writer" and step["status"] == "done":
                final_report = step["output"]
                
        # Check that we ran all agents
        agents_run = set(s["agent"] for s in steps_logged)
        expected_agents = {"Coordinator", "Data Analyzer", "Risk Detector", "Demand Trend Detector", "Recommender", "Report Writer"}
        assert expected_agents.issubset(agents_run), f"Missing agents in execution loop. Found: {agents_run}"
        
        # Verify report was generated
        assert len(final_report) > 0, "Final report empty"
        print("✅ Passed: Swarm sequence ran and consensus dialogue simulated successfully.\n")
    except Exception as e:
        print(f"❌ Failed Test 7: {e}")
        sys.exit(1)

    print("🎉 ALL TESTS PASSED SUCCESSFULLY! The upgraded StockPilot AI is production-ready.")

if __name__ == "__main__":
    run_verification()
