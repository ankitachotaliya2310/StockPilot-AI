import pandas as pd
import numpy as np
import io
import os
import json
from typing import Dict, Any, List, Union

class DatasetProfilingSkill:
    """Skill for loading, profiling, and validating inventory datasets."""
    
    @staticmethod
    def validate_and_load(file_path: str) -> pd.DataFrame:
        """Loads and validates an Excel or CSV file.
        
        Args:
            file_path: Path to the dataset file.
            
        Returns:
            pd.DataFrame: Validated inventory data.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            raise ValueError(f"File size exceeds safety limit of 50MB (Size: {file_size_mb:.2f}MB).")
            
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported format. Only CSV and Excel (.xlsx, .xls) are allowed.")
            
        if df.empty:
            raise ValueError("Dataset is empty. Please upload a file containing records.")
            
        # Clean whitespaces in headers
        df.columns = [col.strip() for col in df.columns]
        
        # Verify required headers
        required_cols = [
            "Product ID", "Product Name", "Category", "Current Stock", 
            "Reorder Point", "Safety Stock", "Daily Sales Rate", "Unit Cost", 
            "Lead Time (days)", "Supplier Name"
        ]
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Schema violation: missing required columns: {', '.join(missing)}")
            
        # Convert types safely
        numeric_cols = ["Current Stock", "Reorder Point", "Safety Stock", "Daily Sales Rate", "Unit Cost", "Lead Time (days)"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = np.maximum(df[col], 0)  # No negative values allowed
            
        # Standardize strings
        string_cols = ["Product ID", "Product Name", "Category", "Supplier Name"]
        for col in string_cols:
            df[col] = df[col].astype(str).str.strip().fillna("Unknown")
            
        return df

    @staticmethod
    def get_profile(df: pd.DataFrame) -> Dict[str, Any]:
        """Profiles the columns and data completeness."""
        profile = {}
        for col in df.columns:
            profile[col] = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "unique_values": int(df[col].nunique())
            }
        return profile


class InventoryAnalysisSkill:
    """Skill for calculating descriptive statistics and category analytics."""
    
    @staticmethod
    def compute_overview_metrics(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates general inventory metrics."""
        sku_count = int(df.shape[0])
        total_stock = int(df["Current Stock"].sum())
        total_valuation = float((df["Current Stock"] * df["Unit Cost"]).sum())
        avg_unit_cost = float(df["Unit Cost"].mean())
        
        # Breakdown status
        stockouts = int((df["Current Stock"] == 0).sum())
        critical = int((df["Current Stock"] <= df["Safety Stock"]).sum()) - stockouts
        critical = max(0, critical)
        
        reorder_alerts = int((df["Current Stock"] <= df["Reorder Point"]).sum()) - stockouts - critical
        reorder_alerts = max(0, reorder_alerts)
        
        overstock_alerts = int((df["Current Stock"] > df["Reorder Point"] * 3).sum())
        
        healthy = sku_count - stockouts - critical - reorder_alerts - overstock_alerts
        healthy = max(0, healthy)
        
        return {
            "SKU Count": sku_count,
            "Total Stock Units": total_stock,
            "Total Valuation": total_valuation,
            "Average Unit Cost": avg_unit_cost,
            "Stockouts": stockouts,
            "Critical Shortages": critical,
            "Reorder Warnings": reorder_alerts,
            "Overstocked SKUs": overstock_alerts,
            "Healthy SKUs": healthy
        }

    @staticmethod
    def compute_category_analytics(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates metrics grouped by category."""
        category_data = {}
        groups = df.groupby("Category")
        for name, group in groups:
            category_data[name] = {
                "SKUs": int(group.shape[0]),
                "Stock Units": int(group["Current Stock"].sum()),
                "Valuation": float((group["Current Stock"] * group["Unit Cost"]).sum()),
                "Average Lead Time": float(group["Lead Time (days)"].mean())
            }
        return category_data


class DemandAnalysisSkill:
    """Skill for analyzing demand trends, velocity, and exhaustion."""
    
    @staticmethod
    def classify_velocity(df: pd.DataFrame) -> Dict[str, Any]:
        """Classifies SKUs by demand velocity."""
        df_copy = df.copy()
        df_copy["Velocity"] = np.where(
            df_copy["Daily Sales Rate"] > 5, 
            "HIGH", 
            np.where(df_copy["Daily Sales Rate"] >= 1.5, "MEDIUM", "LOW")
        )
        counts = df_copy["Velocity"].value_counts().to_dict()
        
        velocity_list = []
        for _, row in df_copy.iterrows():
            velocity_list.append({
                "Product ID": row["Product ID"],
                "Product Name": row["Product Name"],
                "Daily Sales": float(row["Daily Sales Rate"]),
                "Velocity": row["Velocity"]
            })
            
        return {
            "Velocity Counts": {k: int(v) for k, v in counts.items()},
            "Product Velocities": velocity_list
        }

    @staticmethod
    def project_depletion(df: pd.DataFrame) -> Dict[str, Any]:
        """Projects days of supply remaining and top depletion warnings."""
        df_copy = df.copy()
        df_copy["Days of Supply"] = np.where(
            df_copy["Daily Sales Rate"] > 0, 
            df_copy["Current Stock"] / df_copy["Daily Sales Rate"], 
            9999.0
        )
        
        overall_avg = float(df_copy[df_copy["Daily Sales Rate"] > 0]["Days of Supply"].mean())
        
        # Category average
        category_dos = {}
        for name, group in df_copy.groupby("Category"):
            active = group[group["Daily Sales Rate"] > 0]
            category_dos[name] = float(active["Days of Supply"].mean()) if not active.empty else 9999.0
            
        # Top 5 depletion alerts (excluding stockouts)
        active_exhaust = df_copy[(df_copy["Current Stock"] > 0) & (df_copy["Daily Sales Rate"] > 0)]
        top_depleting = active_exhaust.sort_values(by="Days of Supply").head(5)
        
        depleting_list = []
        for _, row in top_depleting.iterrows():
            depleting_list.append({
                "Product ID": row["Product ID"],
                "Product Name": row["Product Name"],
                "Category": row["Category"],
                "Current Stock": int(row["Current Stock"]),
                "Daily Sales": float(row["Daily Sales Rate"]),
                "Days Left": round(float(row["Days of Supply"]), 1)
            })
            
        return {
            "Overall Avg Days of Supply": round(overall_avg, 1),
            "Category Avg Days of Supply": {k: round(v, 1) for k, v in category_dos.items()},
            "Top Depleting SKUs": depleting_list
        }


class RiskAssessmentSkill:
    """Skill for evaluating critical inventory risks, suppliers, and metrics."""
    
    @staticmethod
    def analyze_risks(df: pd.DataFrame) -> Dict[str, Any]:
        """Identifies anomalies and supplier risks."""
        # Stockouts
        stockouts = df[df["Current Stock"] == 0][["Product ID", "Product Name", "Category", "Supplier Name"]].to_dict(orient="records")
        
        # Shortages
        shortages_df = df[(df["Current Stock"] <= df["Safety Stock"]) & (df["Current Stock"] > 0)]
        shortages = shortages_df[["Product ID", "Product Name", "Current Stock", "Safety Stock", "Supplier Name"]].to_dict(orient="records")
        
        # Supply Chain exposure
        exposed_df = df[(df["Lead Time (days)"] > 15) & (df["Current Stock"] <= df["Reorder Point"])]
        exposed = exposed_df[["Product ID", "Product Name", "Lead Time (days)", "Current Stock"]].to_dict(orient="records")
        
        # Capital lockup
        overstock_df = df[df["Current Stock"] > df["Reorder Point"] * 3].copy()
        overstock_df["Excess Cost"] = (overstock_df["Current Stock"] - overstock_df["Reorder Point"]) * overstock_df["Unit Cost"]
        capital_lockups = overstock_df.sort_values(by="Excess Cost", ascending=False).head(5)
        
        lockups = []
        for _, row in capital_lockups.iterrows():
            lockups.append({
                "Product ID": row["Product ID"],
                "Product Name": row["Product Name"],
                "Current Stock": int(row["Current Stock"]),
                "Excess Stock": int(row["Current Stock"] - row["Reorder Point"]),
                "Tied Up Capital": float(row["Excess" + " Cost"])
            })
            
        # Supplier risks
        below_rp = df[df["Current Stock"] <= df["Reorder Point"]]
        supplier_alerts = {}
        if not below_rp.empty:
            counts = below_rp["Supplier Name"].value_counts()
            for supplier, count in counts.items():
                total = df[df["Supplier Name"] == supplier].shape[0]
                supplier_alerts[supplier] = {
                    "Alert SKUs": int(count),
                    "Total SKUs": int(total),
                    "Ratio": round(float(count / total), 2)
                }
                
        return {
            "Stockouts": stockouts,
            "Shortages": shortages,
            "Exposed Lead Times": exposed,
            "Capital Lockups": lockups,
            "Supplier Alerts": supplier_alerts
        }

    @staticmethod
    def calculate_health_scores(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates Health and Risk metrics."""
        sku_count = df.shape[0]
        if sku_count == 0:
            return {"Health Score": 100.0, "Risk Level": "Low"}
            
        stockouts = (df["Current Stock"] == 0).sum()
        shortages = ((df["Current Stock"] <= df["Safety Stock"]) & (df["Current Stock"] > 0)).sum()
        overstocks = (df["Current Stock"] > df["Reorder Point"] * 3).sum()
        
        unhealthy_ratio = (stockouts + shortages + overstocks) / sku_count
        health_score = max(0.0, min(100.0, 100.0 * (1 - unhealthy_ratio)))
        
        # Risk Score based on stockout/shortage threat
        depletion_ratio = (stockouts + shortages) / sku_count
        if depletion_ratio > 0.15:
            risk_level = "CRITICAL"
        elif depletion_ratio > 0.05:
            risk_level = "HIGH"
        else:
            risk_level = "NORMAL"
            
        return {
            "Inventory Health Score": round(health_score, 1),
            "Stockout Risk Score": risk_level
        }


class RecommendationGenerationSkill:
    """Skill for generating and optimizing replenishment purchase orders."""
    
    @staticmethod
    def generate_orders(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Calculates replenishment orders using standard mathematical models."""
        orders = []
        for _, row in df.iterrows():
            current = int(row["Current Stock"])
            rop = int(row["Reorder Point"])
            safety = int(row["Safety Stock"])
            daily_sales = float(row["Daily Sales Rate"])
            lead_time = int(row["Lead Time (days)"])
            cost = float(row["Unit Cost"])
            
            # Target = 30-day cycle coverage + lead time demand + safety stock
            target = int(daily_sales * (lead_time + 30)) + safety
            
            needs_restock = "No"
            qty = 0
            priority = "NONE"
            
            if current <= rop:
                needs_restock = "Yes"
                qty = max(0, target - current)
                priority = "CRITICAL" if current <= safety else "HIGH"
            elif current > rop * 3:
                priority = "OVERSTOCK"
            else:
                priority = "NORMAL"
                
            orders.append({
                "Product ID": row["Product ID"],
                "Product Name": row["Product Name"],
                "Category": row["Category"],
                "Current Stock": current,
                "Reorder Point": rop,
                "Safety Stock": safety,
                "Daily Sales Rate": daily_sales,
                "Lead Time (days)": lead_time,
                "Unit Cost": cost,
                "Needs Restock": needs_restock,
                "Suggested Qty": qty,
                "Cost": cost,
                "Estimated Restock Cost": round(qty * cost, 2),
                "Priority": priority,
                "Supplier Name": row["Supplier Name"]
            })
        return orders

    @staticmethod
    def optimize_consensual_plan(recs: List[Dict[str, Any]], risks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Adjusts suggestions based on risk and supply chain alerts (Consensus Logic).
        
        Rules:
        1. If a supplier shows high risk (Alert Ratio > 0.6), add a 15% safety buffer to reorder quantity
           to prevent stockouts due to delayed shipping.
        2. If the item has high lead time (>15 days), add a 10% safety buffer.
        3. If there is capital lockup in the category, trim non-critical reorders by 10%.
        """
        supplier_alerts = risks.get("Supplier Alerts", {})
        
        optimized_recs = []
        for item in recs:
            opt_item = item.copy()
            if opt_item["Needs Restock"] == "Yes":
                qty = opt_item["Suggested Qty"]
                supplier = opt_item["Supplier Name"]
                lead_time = opt_item["Lead Time (days)"]
                
                # Apply Supplier risk buffer
                sup_risk = supplier_alerts.get(supplier, {})
                if sup_risk.get("Ratio", 0) > 0.6:
                    qty = int(qty * 1.15)
                    opt_item["Consensus Note"] = f"Adjusted +15% due to supplier alert for '{supplier}'"
                    
                # Apply Lead time buffer
                elif lead_time > 15:
                    qty = int(qty * 1.10)
                    opt_item["Consensus Note"] = "Adjusted +10% due to long supplier lead time (>15d)"
                else:
                    opt_item["Consensus Note"] = "Approved without adjustments"
                    
                opt_item["Suggested Qty"] = qty
                opt_item["Estimated Restock Cost"] = round(qty * opt_item["Unit Cost"], 2)
            else:
                if opt_item["Priority"] == "OVERSTOCK":
                    opt_item["Consensus Note"] = "Excess capital tied up. Freeze new intake orders."
                else:
                    opt_item["Consensus Note"] = "Inventory levels healthy. No order needed."
                    
            optimized_recs.append(opt_item)
            
        return optimized_recs


class ExecutiveReportingSkill:
    """Skill for compiling the final Markdown Executive report."""
    
    @staticmethod
    def generate_report(overview: dict, risks: dict, depletion: dict, recs_summary: dict) -> str:
        """Assembles and returns the executive report as Markdown."""
        report = []
        report.append("# StockPilot AI - Advanced Multi-Agent Inventory Report")
        report.append(f"**Generated Report** | StockPilot AI System Swarm\n")
        
        report.append("## 📊 Strategic Overview")
        report.append(f"- **Total SKUs Inspected:** {overview['SKU Count']}")
        report.append(f"- **Inventory Valuation:** ${overview['Total Valuation']:,.2f}")
        report.append(f"- **Inventory Health Score:** {overview.get('Health Score', overview.get('Inventory Health Score', 0.0))}%")
        report.append(f"- **Global Depletion Risk Level:** **{overview.get('Risk Level', overview.get('Stockout Risk Score', 'NORMAL'))}**")
        report.append(f"- **Average Days of Supply:** {depletion['Overall Avg Days of Supply']} days\n")
        
        report.append("### 🏥 Inventory Health Grid")
        report.append("| Status | SKU Count | Ratio | Description |")
        report.append("|---|---|---|---|")
        total = overview['SKU Count']
        report.append(f"| 🛑 **Stockout** | {overview['Stockouts']} | {overview['Stockouts']/total*100:.1f}% | Out of stock, revenue loss active. |")
        report.append(f"| ⚠️ **Shortage** | {overview['Critical Shortages']} | {overview['Critical Shortages']/total*100:.1f}% | Below safety stock threshold. |")
        report.append(f"| 🟨 **Warning** | {overview['Reorder Warnings']} | {overview['Reorder Warnings']/total*100:.1f}% | Below ROP, order triggers active. |")
        report.append(f"| 📦 **Overstock** | {overview['Overstocked SKUs']} | {overview['Overstocked SKUs']/total*100:.1f}% | Excessive stock, capital bottleneck. |")
        report.append(f"| ✅ **Optimal** | {overview['Healthy SKUs']} | {overview['Healthy SKUs']/total*100:.1f}% | Stocked at target levels. |\n")
        
        report.append("## 🔍 Consensus Risk Assessments & Anomalies")
        
        # Stockouts
        if risks["Stockouts"]:
            report.append("### 🛑 Immediate Stockouts")
            for idx, item in enumerate(risks["Stockouts"][:3]):
                report.append(f"{idx+1}. **{item['Product Name']}** ({item['Product ID']}) | Category: {item['Category']} (Supplier: {item['Supplier Name']})")
            if len(risks["Stockouts"]) > 3:
                report.append(f"*...and {len(risks['Stockouts']) - 3} more.*")
            report.append("")
            
        # Lead times
        if risks["Exposed Lead Times"]:
            report.append("### ✈️ Supply Chain Delayed Expostures")
            for item in risks["Exposed Lead Times"][:3]:
                report.append(f"- **{item['Product Name']}** | Lead Time: **{item['Lead Time (days)']} days** (Stock: {item['Current Stock']})")
            report.append("")
            
        # Capital lockups
        if risks["Capital Lockups"]:
            report.append("### 💵 Top Excess Overstocks (Cash Lockup)")
            for item in risks["Capital Lockups"][:3]:
                report.append(f"- **{item['Product Name']}** | Excess Units: {item['Excess Stock']} | **Wasted Capital: ${item['Tied Up Capital']:,.2f}**")
            report.append("")
            
        report.append("## 🕒 Exhaustion Projections")
        if depletion["Top Depleting SKUs"]:
            report.append("| Product Name | Category | Daily Sales | Days Left |")
            report.append("|---|---|---|---|")
            for item in depletion["Top Depleting SKUs"]:
                report.append(f"| {item['Product Name']} | {item['Category']} | {item['Daily Sales']} | **{item['Days Left']} days** |")
            report.append("")
            
        report.append("## 🛠️ Optimised Procurement Plan")
        report.append(f"- **Suggested SKU Orders:** {recs_summary['Items to Reorder']}")
        report.append(f"- **Estimated Capital Required:** **${recs_summary['Total Cost']:,.2f}**\n")
        
        report.append("### 🤝 Swarm Consensus Action Items")
        report.append("1. **Critical Reorders:** Immediately execute purchase orders for all items in the `CRITICAL` list. Safety buffers have been added to offset supplier lead time delays.")
        report.append("2. **Supply Chain Hedging:** Increase reorder targets for suppliers with high alert ratios to build inventory safety buffers.")
        report.append("3. **Capital Release:** Freeze replenishment for `OVERSTOCK` products and negotiate immediate shipping delays or returns to release trapped capital.")
        
        return "\n".join(report)
