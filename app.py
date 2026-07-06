import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
import time
import json
import re
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Import local tools and skills
from tools import load_data, compile_executive_report
from skills import (
    DatasetProfilingSkill,
    InventoryAnalysisSkill,
    DemandAnalysisSkill,
    RiskAssessmentSkill,
    RecommendationGenerationSkill,
    ExecutiveReportingSkill
)
from agents import StockPilotOrchestrator
from data_generator import generate_default_dataset

# Set up page configuration
st.set_page_config(
    page_title="StockPilot AI - Mission Control Room",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load premium stylesheet
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Inject drifting glow background blobs
st.markdown("<div class='bg-glow-1'></div><div class='bg-glow-2'></div>", unsafe_allow_html=True)

# Initialize session state variables
if "df" not in st.session_state:
    st.session_state.df = None
if "file_path" not in st.session_state:
    st.session_state.file_path = None
if "analysis_run" not in st.session_state:
    st.session_state.analysis_run = False
if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []
if "agent_reports" not in st.session_state:
    st.session_state.agent_reports = {}
if "final_report" not in st.session_state:
    st.session_state.final_report = ""
if "execution_duration" not in st.session_state:
    st.session_state.execution_duration = None

# --- MONOCHROME SVG AGENT ICONS ---
AGENT_ICONS = {
    "Coordinator": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M21 9H3"/><path d="M21 15H3"/><path d="M12 3v18"/></svg>""",
    "Data Analyzer": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>""",
    "Risk Detector": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>""",
    "Demand Trend Detector": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>""",
    "Recommender": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="6" y2="12"/><polyline points="12 12 16 14"/></svg>""",
    "Report Writer": """<svg class="agent-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/></svg>"""
}

STATUS_NODES = {
    "running": """<div class="timeline-node timeline-node-running"><svg class="status-spin" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="3"><circle cx="12" cy="12" r="10" stroke="rgba(245,158,11,0.2)"/><path d="M12 2a10 10 0 0 1 10 10"/></svg></div>""",
    "done": """<div class="timeline-node timeline-node-done"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>""",
    "complete": """<div class="timeline-node timeline-node-done"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>""",
    "consensus": """<div class="timeline-node timeline-node-done"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>""",
    "error": """<div class="timeline-node timeline-node-error"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg></div>"""
}

# --- LOGO RENDERING ---
def render_logo():
    logo_svg = """
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
        <svg width="34" height="34" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#gradient)" />
            <path d="M8 20L12 14L16 17L24 9" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M18 9H24V15" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="8" cy="20" r="2.5" fill="#0EA5E9" stroke="white" stroke-width="1.5"/>
            <circle cx="24" cy="9" r="2.5" fill="#10B981" stroke="white" stroke-width="1.5"/>
            <defs>
                <linearGradient id="gradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#0EA5E9"/>
                    <stop offset="1" stop-color="#2563EB"/>
                </linearGradient>
            </defs>
        </svg>
        <span style="font-family: 'Outfit', sans-serif; font-size: 20px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.03em;">
            StockPilot <span style="background: linear-gradient(135deg, #0EA5E9 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI</span>
        </span>
    </div>
    """
    st.sidebar.markdown(logo_svg, unsafe_allow_html=True)

render_logo()
st.sidebar.markdown("<p style='font-size: 11px; color: #64748B; margin-top: -15px;'>Enterprise Swarm Console</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# -----------------------------
# System Status Sidebar
# -----------------------------
api_key = os.getenv("GEMINI_API_KEY")

st.sidebar.markdown("<p style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;'>System Connection</p>", unsafe_allow_html=True)
if api_key:
    st.sidebar.success("AI Tunnel Active")
else:
    st.sidebar.info("Consensus Mock Active")

model_choice = st.sidebar.selectbox(
    "AI Model Suite",
    [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ],
    index=0,
)
st.session_state.model_choice = model_choice

uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"], label_visibility="collapsed")

col_side1, col_side2 = st.sidebar.columns(2)
load_sample = col_side1.button("Load Data", use_container_width=True)
reset_btn = col_side2.button("Reset App", use_container_width=True)

if reset_btn:
    st.session_state.df = None
    st.session_state.file_path = None
    st.session_state.analysis_run = False
    st.session_state.agent_logs = []
    st.session_state.agent_reports = {}
    st.session_state.final_report = ""
    st.session_state.execution_duration = None
    st.rerun()

# Safe upload file validations (Security Requirement)
if uploaded_file is not None:
    try:
        file_bytes = uploaded_file.read()
        
        # Security size check
        if len(file_bytes) > 10 * 1024 * 1024:
            st.sidebar.error("Security alert: File exceeds 10MB limit.")
            st.stop()
            
        suffix = ".csv" if uploaded_file.name.endswith(".csv") else ".xlsx"
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tfile.write(file_bytes)
        tfile.close()
        
        # Load and validate columns/schema
        df_loaded = DatasetProfilingSkill.validate_and_load(tfile.name)
        st.session_state.df = df_loaded
        st.session_state.file_path = tfile.name
    except Exception as e:
        st.sidebar.error(f"Validation Failure: {e}")
        st.stop()
elif load_sample:
    sample_path = os.path.join(os.getcwd(), "sample_inventory.csv")
    if not os.path.exists(sample_path):
        df_sample = generate_default_dataset()
        df_sample.to_csv(sample_path, index=False)
    st.session_state.df = DatasetProfilingSkill.validate_and_load(sample_path)
    st.session_state.file_path = sample_path
    st.sidebar.success("Retail Dataset Loaded!")

# If no data is loaded, display premium welcome screen
if st.session_state.df is None:
    st.markdown("""<div style="text-align: center; padding: 60px 40px; background: rgba(13, 18, 30, 0.65); backdrop-filter: blur(20px); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); margin-top: 30px; box-shadow: 0 20px 50px rgba(0,0,0,0.4);">
<span style="background: rgba(14, 165, 233, 0.1); border: 1px solid rgba(14, 165, 233, 0.2); color: #38BDF8; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 12px; letter-spacing: 0.05em;">
ENTERPRISE AI OPERATING SYSTEM
</span>
<h1 style="font-size: 38px; margin-top: 16px; margin-bottom: 12px; font-weight: 800; background: linear-gradient(135deg, #FFFFFF 40%, #94A3B8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.03em;">
StockPilot AI Mission Control
</h1>
<p style="font-size: 15px; color: #94A3B8; max-width: 600px; margin: 0 auto 30px auto; line-height: 1.6;">
Multi-agent replenishment swarm powered by Google ADK and stdio MCP servers.
</p>
<div style="background: rgba(15, 22, 36, 0.45); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 10px; max-width: 540px; margin: 0 auto; padding: 24px; text-align: left; box-shadow: inset 0 0 20px rgba(0,0,0,0.2);">
<strong style="color: #0EA5E9; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 14px;">
System Launch Guide
</strong>
<div style="display: flex; flex-direction: column; gap: 14px; color: #CBD5E1; font-size: 13.5px;">
<div style="display: flex; gap: 12px; align-items: flex-start;">
<span style="background: rgba(14, 165, 233, 0.15); color: #38BDF8; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; flex-shrink: 0;">1</span>
<div>Click <strong style="color:#FFFFFF;">"Load Data"</strong> in the sidebar to initialize validated sample log schema.</div>
</div>
<div style="display: flex; gap: 12px; align-items: flex-start;">
<span style="background: rgba(14, 165, 233, 0.15); color: #38BDF8; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; flex-shrink: 0;">2</span>
<div>Optionally upload your own CSV/Excel inventory target or provide a Google Gemini API Key.</div>
</div>
<div style="display: flex; gap: 12px; align-items: flex-start;">
<span style="background: rgba(14, 165, 233, 0.15); color: #38BDF8; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px; flex-shrink: 0;">3</span>
<div>Open the <strong style="color:#FFFFFF;">Mission Control Center</strong> tab to execute swarm orchestration.</div>
</div>
</div>
</div>
</div>""", unsafe_allow_html=True)
    st.stop()

# Load verified data
df = st.session_state.df

# Calculate analytics metrics (guarantees accuracy)
overview = InventoryAnalysisSkill.compute_overview_metrics(df)
scores = RiskAssessmentSkill.calculate_health_scores(df)
overview_combined = {**overview, **scores}
risks = RiskAssessmentSkill.analyze_risks(df)
depletion = DemandAnalysisSkill.project_depletion(df)
recs_list = RecommendationGenerationSkill.generate_orders(df)
optimized_recs = RecommendationGenerationSkill.optimize_consensual_plan(recs_list, risks)

# --- EXECUTIVE COMMAND CENTER (HERO SECTION) ---
def render_executive_command_center():
    dataset_name = uploaded_file.name if uploaded_file is not None else "sample_inventory.csv"
    mode_text = "PRODUCTION Swarm Consensus" if api_key else "SIMULATION Swarm Consensus"
    mode_color = "#10B981" if api_key else "#A855F7"
    
    st.markdown(f"""
    <div style="margin-top: 10px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
            <div>
                <span style="font-family: 'Outfit', sans-serif; font-size: 30px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.03em;">
                    StockPilot <span style="background: linear-gradient(135deg, #0EA5E9 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">AI</span>
                </span>
                <span style="background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(14, 165, 233, 0.15); color: #38BDF8; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 12px; margin-left: 10px; vertical-align: middle; letter-spacing:0.04em;">
                    EXECUTIVE COMMAND CENTER
                </span>
                <p style="font-size: 13.5px; color: #64748B; margin-top: 4px; margin-bottom: 0;">
                    Multi-Agent Autonomous Swarm | Supply Chain Consensus Orchestrator
                </p>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.15); color: #34D399; font-size: 10.5px; font-weight: 700; padding: 4px 10px; border-radius: 6px; letter-spacing: 0.02em;">
                    🟢 SYSTEM STATUS ONLINE
                </span>
            </div>
        </div>
    </div>
    
    <div style="display: flex; gap: 24px; padding: 10px 16px; background: rgba(15, 22, 36, 0.4); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; margin-bottom: 24px; font-size: 11px; color: #94A3B8; letter-spacing: 0.02em;">
        <div><span style="color: #475569;">PLATFORM:</span> <strong style="color: #F8FAFC;">Google ADK v2.3</strong></div>
        <div style="width: 1px; background: rgba(255,255,255,0.06);"></div>
        <div><span style="color: #475569;">COGNITIVE ENGINE:</span> <strong style="color: #F8FAFC;">{model_choice}</strong></div>
        <div style="width: 1px; background: rgba(255,255,255,0.06);"></div>
        <div><span style="color: #475569;">TARGET LOGS:</span> <strong style="color: #F8FAFC;">{dataset_name}</strong></div>
        <div style="width: 1px; background: rgba(255,255,255,0.06);"></div>
        <div><span style="color: #475569;">CONCORDANCE:</span> <strong style="color: {mode_color};">{mode_text}</strong></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 1. Total Capital Valuation
    val_val = overview_combined.get('Total Valuation', 0.0)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-title">Capital Valuation</span>
                <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="12" y1="4" x2="12" y2="20"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
            </div>
            <div>
                <div class="kpi-value">${val_val:,.2f}</div>
                <div class="kpi-trend trend-neutral">
                    <span>● Stable Inventory Target</span>
                </div>
            </div>
            <div class="kpi-desc">Total working capital locked in warehouse inventory.</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. Health score
    health = overview_combined.get('Inventory Health Score', 0.0)
    health_cls = 'trend-up' if health >= 80 else 'trend-down' if health < 50 else 'trend-neutral'
    health_sym = '▲' if health >= 80 else '▼' if health < 50 else '●'
    health_txt = 'Optimal' if health >= 80 else 'Action Needed' if health < 50 else 'Stable'
    with col2:
        st.markdown(f"""
        <div class="kpi-card kpi-health">
            <div class="kpi-header">
                <span class="kpi-title">Health Index</span>
                <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <div>
                <div class="kpi-value">{health:.1f}%</div>
                <div class="kpi-trend {health_cls}">
                    <span>{health_sym} {health_txt} Status</span>
                </div>
            </div>
            <div class="kpi-desc">Consensus score reflecting stockouts and shortage threats.</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. Active Swarm Agents
    with col3:
        st.markdown("""
        <div class="kpi-card kpi-agents">
            <div class="kpi-header">
                <span class="kpi-title">Active Agents</span>
                <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div>
                <div class="kpi-value">6 / 6</div>
                <div class="kpi-trend trend-up">
                    <span>▲ Swarm Synced (100%)</span>
                </div>
            </div>
            <div class="kpi-desc">Orchestrated sub-agents coordinating safety consensus.</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 4. Swarm Execution Time
    exec_duration = st.session_state.get("execution_duration")
    if exec_duration is not None:
        exec_str = f"{exec_duration:.2f}s"
        trend_str = "▲ Complete"
        trend_cls = "trend-up"
        desc_str = "Total processing time of multi-agent reasoning."
    else:
        exec_str = "Standby"
        trend_str = "● Ready to Execute"
        trend_cls = "trend-neutral"
        desc_str = "Run the Swarm Controller to populate timer."
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card kpi-timer">
            <div class="kpi-header">
                <span class="kpi-title">Execution Time</span>
                <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </div>
            <div>
                <div class="kpi-value">{exec_str}</div>
                <div class="kpi-trend {trend_cls}">
                    <span>{trend_str}</span>
                </div>
            </div>
            <div class="kpi-desc">{desc_str}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # 5. Critical Alerts Count
    alerts = overview_combined.get('Stockouts', 0) + overview_combined.get('Critical Shortages', 0)
    alerts_cls = 'trend-down' if alerts > 0 else 'trend-up'
    alerts_sym = '▼' if alerts > 0 else '▲'
    alerts_txt = 'Attention Required' if alerts > 0 else 'Zero Warnings'
    with col5:
        st.markdown(f"""
        <div class="kpi-card kpi-alerts">
            <div class="kpi-header">
                <span class="kpi-title">Active Alerts</span>
                <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div>
                <div class="kpi-value">{alerts} SKUs</div>
                <div class="kpi-trend {alerts_cls}">
                    <span>{alerts_sym} {alerts_txt}</span>
                </div>
            </div>
            <div class="kpi-desc">Stockouts and items depleted below safety threshold.</div>
        </div>
        """, unsafe_allow_html=True)

render_executive_command_center()

# Initialize tabs
tab1, tab2, tab3 = st.tabs([
    "Mission Control Center", 
    "Strategic Operations Analytics", 
    "Swarm Replenishment Recommendations"
])

# --- HELPER: SKELETON LOADER CONTAINER ---
def render_skeleton_loaders(num_cards=2):
    for _ in range(num_cards):
        st.markdown("""
        <div class="skeleton-card">
            <div class="skeleton-title"></div>
            <div class="skeleton-line-1"></div>
            <div class="skeleton-line-2"></div>
        </div>
        """, unsafe_allow_html=True)

# --- HELPER: SVG RADIAL GAUGE ---
def render_svg_gauge(score):
    r = 50
    c = 314.16
    pct = (score / 100.0) * c
    dash_offset = c - pct
    
    # Angle for the tip of the progress arc
    import math
    angle = -90 + (score / 100.0) * 360
    angle_rad = math.radians(angle)
    x = 60 + r * math.cos(angle_rad)
    y = 60 + r * math.sin(angle_rad)
    
    # Corrected circumference for r=44 inner bands:
    # 2 * pi * 44 = 276.46
    # 0-50% (Critical band): length 50% = 138.23.
    # 50-80% (Warning band): length 30% = 82.94. Dashoffset = -138.23.
    # 80-100% (Optimal band): length 20% = 55.29. Dashoffset = -221.17.
    
    if score >= 80:
        grad_start = "#10B981"
        grad_end = "#34D399"
        status_lbl = "OPTIMAL"
        status_color = "#10B981"
    elif score >= 50:
        grad_start = "#F59E0B"
        grad_end = "#FBBF24"
        status_lbl = "WARNING"
        status_color = "#F59E0B"
    else:
        grad_start = "#EF4444"
        grad_end = "#F87171"
        status_lbl = "CRITICAL"
        status_color = "#EF4444"
        
    svg_gauge = f"""<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 15px 0;">
<svg width="180" height="180" viewBox="0 0 120 120" style="filter: drop-shadow(0 4px 10px rgba(0,0,0,0.35));">
<defs>
<linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="{grad_start}" />
<stop offset="100%" stop-color="{grad_end}" />
</linearGradient>
<linearGradient id="redBand" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#EF4444" stop-opacity="0.25" />
<stop offset="100%" stop-color="#EF4444" stop-opacity="0.05" />
</linearGradient>
<linearGradient id="yellowBand" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#F59E0B" stop-opacity="0.25" />
<stop offset="100%" stop-color="#F59E0B" stop-opacity="0.05" />
</linearGradient>
<linearGradient id="greenBand" x1="0%" y1="0%" x2="100%" y2="100%">
<stop offset="0%" stop-color="#10B981" stop-opacity="0.25" />
<stop offset="100%" stop-color="#10B981" stop-opacity="0.05" />
</linearGradient>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
<feGaussianBlur stdDeviation="3.0" result="coloredBlur"/>
<feMerge>
<feMergeNode in="coloredBlur"/>
<feMergeNode in="SourceGraphic"/>
</feMerge>
</filter>
<filter id="indicatorGlow">
<feGaussianBlur stdDeviation="1.5" result="blur"/>
<feMerge>
<feMergeNode in="blur"/>
<feMergeNode in="SourceGraphic"/>
</feMerge>
</filter>
</defs>
<circle cx="60" cy="60" r="{r}" stroke="rgba(255, 255, 255, 0.03)" stroke-width="8" fill="none" />
<circle cx="60" cy="60" r="55" stroke="rgba(255,255,255,0.06)" stroke-dasharray="1.5, 7.92" stroke-width="2" fill="none" />
<circle cx="60" cy="60" r="44" stroke="url(#redBand)" stroke-width="3" fill="none" stroke-dasharray="138.23 276.46" transform="rotate(-90 60 60)" />
<circle cx="60" cy="60" r="44" stroke="url(#yellowBand)" stroke-width="3" fill="none" stroke-dasharray="82.94 276.46" stroke-dashoffset="-138.23" transform="rotate(-90 60 60)" />
<circle cx="60" cy="60" r="44" stroke="url(#greenBand)" stroke-width="3" fill="none" stroke-dasharray="55.29 276.46" stroke-dashoffset="-221.17" transform="rotate(-90 60 60)" />
<circle cx="60" cy="60" r="{r}" stroke="url(#gaugeGrad)" stroke-width="8" fill="none" stroke-dasharray="{c}" stroke-dashoffset="{dash_offset}" stroke-linecap="round" transform="rotate(-90 60 60)" filter="url(#glow)" style="transition: stroke-dashoffset 1s ease-in-out;" />
<circle cx="{x}" cy="{y}" r="3.5" fill="#FFFFFF" stroke="{grad_start}" stroke-width="1.5" filter="url(#indicatorGlow)" />
<text x="60" y="58" font-family="'Outfit', sans-serif" font-size="20" font-weight="800" fill="#FFFFFF" text-anchor="middle" dominant-baseline="middle">{score:.1f}%</text>
<text x="60" y="78" font-family="'Plus Jakarta Sans', sans-serif" font-size="7" font-weight="700" fill="{status_color}" letter-spacing="0.08em" text-anchor="middle" dominant-baseline="middle">{status_lbl}</text>
</svg>
</div>"""
    return svg_gauge

# --- HELPER: AI INSIGHT CARD (AI EXPLAINABILITY) ---
def clean_pdf_string(s):
    replacements = {
        "📊": "", "🏥": "", "🔍": "", "🛠️": "", "🕒": "", "🤝": "", "✓": "[YES]", 
        "⚠️": "[WARNING]", "⏱️": "[DELAY]", "💵": "[CAPITAL]", "🟢": "[OK]", "🔴": "[CRITICAL]",
        "★": "*", "▲": "^", "▼": "v", "●": "o", "•": "-", "’": "'", "‘": "'", "“": '"', "”": '"'
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return "".join(c for c in s if ord(c) < 256)

def generate_pdf_from_text(title, text_lines):
    stream_lines = []
    stream_lines.append("BT")
    stream_lines.append("/F1 16 Tf")
    stream_lines.append("50 740 Td")
    
    clean_title = clean_pdf_string(title).replace("(", "\\(").replace(")", "\\)")
    stream_lines.append(f"({clean_title}) Tj")
    stream_lines.append("0 -24 Td")
    
    y_pos = 716
    for line in text_lines:
        line = line.strip()
        if not line:
            stream_lines.append("0 -12 Td")
            y_pos -= 12
            continue
            
        is_heading = False
        is_bullet = False
        if line.startswith("# "):
            stream_lines.append("/F1 14 Tf")
            line = line[2:]
            is_heading = True
        elif line.startswith("## "):
            stream_lines.append("/F1 12 Tf")
            line = line[3:]
            is_heading = True
        elif line.startswith("### "):
            stream_lines.append("/F1 11 Tf")
            line = line[4:]
            is_heading = True
        elif line.startswith("* ") or line.startswith("- "):
            stream_lines.append("/F1 10 Tf")
            line = "• " + line[2:]
            is_bullet = True
        else:
            stream_lines.append("/F1 10 Tf")
            
        clean_line = clean_pdf_string(line).replace("(", "\\(").replace(")", "\\)")
        
        words = clean_line.split(" ")
        current_line = ""
        for word in words:
            limit = 65 if is_bullet else 70
            if len(current_line) + len(word) + 1 > limit:
                stream_lines.append(f"({current_line}) Tj")
                stream_lines.append("0 -13 Td")
                current_line = word
                y_pos -= 13
            else:
                current_line = (current_line + " " + word).strip()
        if current_line:
            stream_lines.append(f"({current_line}) Tj")
            stream_lines.append("0 -13 Td")
            y_pos -= 13
            
        if is_heading:
            stream_lines.append("0 -6 Td")
            y_pos -= 6
            
        if y_pos < 60:
            break
            
    stream_lines.append("ET")
    stream_content = "\n".join(stream_lines).encode("latin-1", errors="ignore")
    
    objects = {}
    objects[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = "<< /Type /Pages /Kids [4 0 R] /Count 1 >>"
    objects[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects[4] = f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>"
    objects[5] = f"<< /Length {len(stream_content)} >>\nstream\n"
    
    out = bytearray()
    out.extend(b"%PDF-1.4\n")
    
    offsets = {}
    for oid in [1, 2, 3, 4]:
        offsets[oid] = len(out)
        out.extend(f"{oid} 0 obj\n{objects[oid]}\nendobj\n".encode("latin-1"))
        
    offsets[5] = len(out)
    out.extend(f"5 0 obj\n{objects[5]}".encode("latin-1"))
    out.extend(stream_content)
    out.extend(b"\nendstream\nendobj\n")
    
    xref_offset = len(out)
    out.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for oid in [1, 2, 3, 4, 5]:
        out.extend(f"{offsets[oid]:010d} 00000 n \n".encode("latin-1"))
        
    out.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1"))
    return bytes(out)

def render_ai_insight_card(confidence, impact, recommendation, agents=None):
    if agents is None:
        agents = ["Coordinator", "Data Analyzer"]
        
    agents_html = "".join(f'<span class="agent-badge badge-{a.lower().replace(" ", "")}" style="font-size: 8.5px; margin-right: 4px; padding: 2px 6px; border-radius:3px; display: inline-block;">{a}</span>' for a in agents)
    impact_class = "insight-value-critical" if impact == "Critical" else "insight-value-high" if impact == "High" else "insight-value-medium"
    
    html = f"""<div class="ai-insight-card">
<h5 style="margin: 0 0 8px 0; color: #0EA5E9; font-family: 'Outfit', sans-serif; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;">💡 Why this recommendation?</h5>
<div style="display: flex; gap: 12px; align-items: center; margin-bottom: 6px; border-bottom: 1px solid rgba(14, 165, 233, 0.08); padding-bottom: 6px; flex-wrap: wrap;">
<div class="insight-meta-item">
<span class="lbl" style="color: #64748B; text-transform: uppercase; font-size: 9.5px; letter-spacing: 0.02em; font-weight: 600;">Confidence:</span>
<span style="color: #34D399; font-weight: 700;">{confidence}</span>
</div>
<div style="width: 1px; background: rgba(255,255,255,0.08); height: 10px;"></div>
<div class="insight-meta-item">
<span class="lbl" style="color: #64748B; text-transform: uppercase; font-size: 9.5px; letter-spacing: 0.02em; font-weight: 600;">Impact:</span>
<span class="{impact_class}" style="font-weight: 700;">{impact}</span>
</div>
</div>
<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px; flex-wrap: wrap;">
<span class="lbl" style="color: #64748B; text-transform: uppercase; font-size: 9.5px; letter-spacing: 0.02em; font-weight: 600;">Contributing Agents:</span>
<div style="display: flex; flex-wrap: wrap; gap: 4px;">{agents_html}</div>
</div>
<div class="insight-recommendation" style="border-top: 1px solid rgba(255,255,255,0.04); padding-top: 6px;">
<strong>Primary Reasoning:</strong> {recommendation}
</div>
</div>"""
    return html

# --- HELPER: EXECUTIVE REPORT RENDERER ---
def render_premium_executive_report(report_text, overview, risks, depletion, reorders_summary):
    import re
    
    # Extract headings and content blocks
    pattern = r'(?m)^#+\s+(.*)$'
    headings = re.findall(pattern, report_text)
    parts = re.split(r'(?m)^#+\s+.*$', report_text)
    
    sections = {}
    for i, heading in enumerate(headings):
        clean_h = re.sub(r'[^\w\s]', '', heading).strip()
        sections[clean_h] = parts[i+1].strip()
        
    header_html = f"""<div class="executive-report-card" style="padding: 24px; background: rgba(15, 22, 36, 0.45); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.35);">
<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:12px; margin-bottom:20px;">
<div>
<h3 style="margin:0; font-family:'Outfit', sans-serif; font-size:16px; font-weight:800; color:#FFFFFF; letter-spacing:0.02em;">
STOCKPILOT AI • ADVANCED MULTI-AGENT INVENTORY BRIEF
</h3>
<span style="font-size:11px; color:#64748B;">System Swarm Consensus Document</span>
</div>
<div style="text-align:right;">
<span style="font-size:9.5px; font-weight:700; color:#0EA5E9; background:rgba(14, 165, 233, 0.08); border:1px solid rgba(14, 165, 233, 0.15); padding:3px 10px; border-radius:12px; letter-spacing:0.05em;">
OFFICIAL BRIEF
</span>
</div>
</div>"""
    
    # 1. Strategic Overview Card
    overview_text = sections.get("Strategic Overview", "")
    overview_html = ""
    if overview_text:
        bullets = re.findall(r'\*\s*(.*)', overview_text)
        if bullets:
            items_html = "".join(f'<li style="margin-bottom:8px; font-size:13px; color:#CBD5E1;"><span style="color:#0EA5E9; margin-right:6px;">•</span> {b}</li>' for b in bullets)
            overview_html = f'<ul style="list-style:none; padding:0; margin:0;">{items_html}</ul>'
        else:
            overview_html = f'<div style="font-size:13px; color:#CBD5E1;">{overview_text}</div>'
            
    # 2. Health Grid Table
    health_text = sections.get("Inventory Health Grid", "")
    health_html = ""
    if health_text:
        rows = [r.strip() for r in health_text.strip().split("\n") if r.strip()]
        table_rows = []
        for row in rows:
            if "|" in row and "---" not in row:
                cols = [c.strip() for c in row.split("|")[1:-1]]
                table_rows.append(cols)
        
        if table_rows:
            headers = table_rows[0]
            tbody_rows = table_rows[1:]
            
            thead_html = "".join(f'<th style="padding:10px; text-align:left; background:rgba(255,255,255,0.02); color:#FFFFFF; font-size:11px; font-weight:700; text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,0.06);">{h}</th>' for h in headers)
            tbody_html = ""
            for r_cols in tbody_rows:
                cols_html = "".join(f'<td style="padding:10px; color:#CBD5E1; font-size:12.5px; border-bottom:1px solid rgba(255,255,255,0.03);">{c}</td>' for c in r_cols)
                tbody_html += f'<tr>{cols_html}</tr>'
                
            health_html = f"""<div style="background:rgba(0,0,0,0.15); border:1px solid rgba(255,255,255,0.04); border-radius:6px; overflow:hidden; margin-top:12px;">
<table style="width:100%; border-collapse:collapse;">
<thead><tr>{thead_html}</tr></thead>
<tbody>{tbody_html}</tbody>
</table>
</div>"""
        else:
            health_html = f'<div style="font-size:13px; color:#CBD5E1;">{health_text}</div>'
            
    # 3. Risks Card
    risk_key = next((k for k in sections if "Risk" in k), None)
    risk_text = sections.get(risk_key or "Consensus Risk Assessments  Anomalies", "")
    
    stockout_text = sections.get("Immediate Stockouts", "")
    delay_text = sections.get("Supply Chain Delayed Expostures", "")
    overstock_text = sections.get("Top Excess Overstocks Cash Lockup", "")
    
    risks_html = ""
    if stockout_text or delay_text or overstock_text:
        if stockout_text:
            bullets = re.findall(r'\*\s*(.*)', stockout_text)
            items = "".join(f'<li style="margin-bottom:6px; font-size:12.5px; color:#CBD5E1;"><span style="color:#EF4444; font-weight:700; margin-right:6px;">⚠️</span> {b}</li>' for b in bullets)
            risks_html += f"""<div style="background:rgba(239, 68, 68, 0.04); border-left:3px solid #EF4444; padding:12px 16px; border-radius:4px; margin-bottom:12px;">
<h5 style="margin:0 0 8px 0; color:#EF4444; font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">IMMEDIATE OUT-OF-STOCK THREATS</h5>
<ul style="list-style:none; padding:0; margin:0;">{items}</ul>
</div>"""
        if delay_text:
            bullets = re.findall(r'\*\s*(.*)', delay_text)
            items = "".join(f'<li style="margin-bottom:6px; font-size:12.5px; color:#CBD5E1;"><span style="color:#F59E0B; font-weight:700; margin-right:6px;">⏱️</span> {b}</li>' for b in bullets)
            risks_html += f"""<div style="background:rgba(245, 158, 11, 0.04); border-left:3px solid #F59E0B; padding:12px 16px; border-radius:4px; margin-bottom:12px;">
<h5 style="margin:0 0 8px 0; color:#F59E0B; font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">SUPPLIER LEAD-TIME EXPOSURES</h5>
<ul style="list-style:none; padding:0; margin:0;">{items}</ul>
</div>"""
        if overstock_text:
            bullets = re.findall(r'\*\s*(.*)', overstock_text)
            items = "".join(f'<li style="margin-bottom:6px; font-size:12.5px; color:#CBD5E1;"><span style="color:#A855F7; font-weight:700; margin-right:6px;">💵</span> {b}</li>' for b in bullets)
            risks_html += f"""<div style="background:rgba(168, 85, 247, 0.04); border-left:3px solid #A855F7; padding:12px 16px; border-radius:4px;">
<h5 style="margin:0 0 8px 0; color:#A855F7; font-size:12.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">EXCESS OVERSTOCKS (CAPITAL LOCKUP)</h5>
<ul style="list-style:none; padding:0; margin:0;">{items}</ul>
</div>"""
    elif risk_text:
        risks_html = f'<div style="font-size:12.5px; color:#CBD5E1;">{risk_text}</div>'
        
    # 4. Exhaustion Projections Table
    exhaustion_text = sections.get("Exhaustion Projections", "")
    exhaustion_html = ""
    if exhaustion_text:
        rows = [r.strip() for r in exhaustion_text.strip().split("\n") if r.strip()]
        table_rows = []
        for row in rows:
            if "|" in row and "---" not in row:
                cols = [c.strip() for c in row.split("|")[1:-1]]
                table_rows.append(cols)
        
        if table_rows:
            headers = table_rows[0]
            tbody_rows = table_rows[1:]
            
            thead_html = "".join(f'<th style="padding:10px; text-align:left; background:rgba(255,255,255,0.02); color:#FFFFFF; font-size:11px; font-weight:700; text-transform:uppercase; border-bottom:1px solid rgba(255,255,255,0.06);">{h}</th>' for h in headers)
            tbody_html = ""
            for r_cols in tbody_rows:
                cols_html = "".join(f'<td style="padding:10px; color:#CBD5E1; font-size:12.5px; border-bottom:1px solid rgba(255,255,255,0.03);">{c}</td>' for c in r_cols)
                tbody_html += f'<tr>{cols_html}</tr>'
                
            exhaustion_html = f"""<div style="background:rgba(0,0,0,0.15); border:1px solid rgba(255,255,255,0.04); border-radius:6px; overflow:hidden; margin-top:12px;">
<table style="width:100%; border-collapse:collapse;">
<thead><tr>{thead_html}</tr></thead>
<tbody>{tbody_html}</tbody>
</table>
</div>"""
        else:
            exhaustion_html = f'<div style="font-size:13px; color:#CBD5E1;">{exhaustion_text}</div>'
            
    # 5. Procurement Plan Summary
    procure_text = sections.get("Optimised Procurement Plan", "") or sections.get("Optimized Procurement Plan", "")
    procure_html = ""
    if procure_text:
        bullets = re.findall(r'\*\s*(.*)', procure_text)
        if bullets:
            items_html = "".join(f'<li style="margin-bottom:8px; font-size:13px; color:#CBD5E1;"><span style="color:#10B981; margin-right:6px;">✓</span> {b}</li>' for b in bullets)
            procure_html = f'<ul style="list-style:none; padding:0; margin:0;">{items_html}</ul>'
        else:
            procure_html = f'<div style="font-size:13px; color:#CBD5E1;">{procure_text}</div>'
            
    # 6. Swarm Consensus Action Items
    action_text = sections.get("Swarm Consensus Action Items", "")
    action_html = ""
    if action_text:
        lines = [l.strip() for l in action_text.split("\n") if l.strip()]
        items_html = ""
        for line in lines:
            match = re.match(r'^(\d+)\.\s*(.*)', line)
            if match:
                num, content = match.groups()
                styled_content = content.replace("CRITICAL", '<span class="badge priority-critical" style="font-size:9px; padding:1px 4px; vertical-align:middle; display:inline-block;">CRITICAL</span>')
                styled_content = styled_content.replace("OVERSTOCK", '<span class="badge priority-overstock" style="font-size:9px; padding:1px 4px; vertical-align:middle; display:inline-block;">OVERSTOCK</span>')
                
                items_html += f"""<div style="display:flex; gap:12px; margin-bottom:12px; align-items:flex-start;">
<span style="background:rgba(14, 165, 233, 0.15); color:#38BDF8; width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px; flex-shrink:0;">{num}</span>
<div style="font-size:13px; color:#CBD5E1; line-height:1.6;">{styled_content}</div>
</div>"""
        if items_html:
            action_html = f'<div style="margin-top:12px;">{items_html}</div>'
        else:
            action_html = f'<div style="font-size:13px; color:#CBD5E1;">{action_text}</div>'
            
    # Assemble Layout
    full_report_html = f"""{header_html}
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:20px;">
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px;">
<h4 style="margin:0 0 12px 0; color:#0EA5E9; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">📊 Strategic Overview</h4>
{overview_html}
</div>
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px;">
<h4 style="margin:0 0 12px 0; color:#0EA5E9; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">🏥 Inventory Health Grid</h4>
{health_html}
</div>
</div>
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px; margin-bottom:20px;">
<h4 style="margin:0 0 12px 0; color:#EF4444; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">🔍 Consensus Risk Highlights</h4>
{risks_html}
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:20px;">
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px;">
<h4 style="margin:0 0 12px 0; color:#10B981; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">🛠️ Optimised Procurement Plan</h4>
<div style="display:flex; gap:16px; margin-bottom:14px; background:rgba(16,185,129,0.05); padding:10px 14px; border:1px solid rgba(16,185,129,0.12); border-radius:4px; width:fit-content;">
<div>
<span style="font-size:9.5px; color:#8E9AA8; text-transform:uppercase; display:block; letter-spacing:0.05em;">SKU Reorders</span>
<strong style="font-size:16px; color:#FFFFFF;">{reorders_summary.get('Items to Reorder', 0)} Items</strong>
</div>
<div style="width:1px; background:rgba(255,255,255,0.08);"></div>
<div>
<span style="font-size:9.5px; color:#8E9AA8; text-transform:uppercase; display:block; letter-spacing:0.05em;">Est. Reorder Cost</span>
<strong style="font-size:16px; color:#10B981;">${reorders_summary.get('Total Cost', 0.0):,.2f}</strong>
</div>
</div>
{procure_html}
</div>
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px;">
<h4 style="margin:0 0 12px 0; color:#F59E0B; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">🕒 Exhaustion Projections</h4>
{exhaustion_html}
</div>
</div>
<div style="background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.04); border-radius:6px; padding:16px;">
<h4 style="margin:0 0 12px 0; color:#38BDF8; font-size:13.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">🤝 Swarm Consensus Action Items</h4>
{action_html}
</div>
</div>"""
    return full_report_html

def generate_word_document_report(report_content, overview, risks, depletion, reorders_summary):
    html_report = render_premium_executive_report(report_content, overview, risks, depletion, reorders_summary)
    word_html = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
<meta charset="utf-8">
<title>StockPilot AI Executive Brief</title>
<!--[if gte mso 9]>
<xml>
<w:WordDocument>
<w:View>Print</w:View>
<w:Zoom>100</w:Zoom>
</w:WordDocument>
</xml>
<![endif]-->
<style>
body {{
    font-family: 'Arial', sans-serif;
    color: #333333;
    line-height: 1.5;
    background-color: #ffffff;
}}
.executive-report-card {{
    padding: 24px;
    border: 1px solid #cccccc;
    border-radius: 8px;
    margin-bottom: 20px;
    background-color: #f9f9f9;
}}
h3 {{
    font-size: 18px;
    color: #0A2540;
    border-bottom: 2px solid #0EA5E9;
    padding-bottom: 6px;
    font-family: 'Arial', sans-serif;
}}
h4 {{
    font-size: 14px;
    color: #0A2540;
    margin-top: 20px;
    margin-bottom: 10px;
    font-family: 'Arial', sans-serif;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    margin-bottom: 10px;
}}
th {{
    background-color: #f2f2f2;
    color: #333333;
    font-weight: bold;
    padding: 8px;
    border: 1px solid #dddddd;
    font-size: 11px;
}}
td {{
    padding: 8px;
    border: 1px solid #dddddd;
    font-size: 11px;
    color: #555555;
}}
ul {{
    padding-left: 20px;
}}
li {{
    font-size: 12px;
    color: #333333;
    margin-bottom: 6px;
}}
.badge {{
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
    border-radius: 4px;
}}
.priority-critical {{
    background-color: #ffebe9;
    color: #ff3b30;
}}
.priority-overstock {{
    background-color: #f5e6ff;
    color: #a855f7;
}}
</style>
</head>
<body>
{html_report}
</body>
</html>"""
    return word_html.encode('utf-8')

# -------------------------------------------------------------
# TAB 1: MISSION CONTROL ROOM (Live Execution & Timeline)
# -------------------------------------------------------------
with tab1:
    col_run, col_timeline = st.columns([13, 10])
    
    with col_run:
        st.subheader("Swarm Controller")
        st.markdown(
            "Launch the root orchestrator. Specialist agents will profile the dataset, "
            "perform safety stock calculations, scan supplier alerts, negotiate safety buffers, and compile summaries."
        )
        
        # Operations stepper status
        def render_operations_stepper():
            logs = st.session_state.agent_logs
            is_done = st.session_state.analysis_run
            
            step1_state = "standby"
            step2_state = "standby"
            step3_state = "standby"
            
            divider1_cls = ""
            divider2_cls = ""
            
            if is_done:
                step1_state = "completed"
                step2_state = "completed"
                step3_state = "completed"
                divider1_cls = "completed"
                divider2_cls = "completed"
            elif len(logs) > 0:
                step1_state = "completed"
                divider1_cls = "active"
                
                # Check latest log
                latest = logs[-1]
                latest_agent = latest["agent"]
                latest_status = latest["status"]
                
                if latest_agent == "Coordinator" and latest_status == "consensus":
                    step2_state = "completed"
                    step3_state = "active"
                    divider1_cls = "completed"
                    divider2_cls = "active"
                elif latest_agent == "Report Writer":
                    step2_state = "completed"
                    step3_state = "active"
                    divider1_cls = "completed"
                    divider2_cls = "active"
                else:
                    step2_state = "active"
            else:
                step1_state = "active"
                
            def get_icon(state):
                if state == "completed":
                    return """<svg class="step-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12"/></svg>"""
                elif state == "active":
                    return """<svg class="step-icon status-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>"""
                else:
                    return """<svg class="step-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/></svg>"""
                    
            st.markdown(f"""
            <div class="ops-stepper">
                <div class="step {step1_state}">
                    <div class="step-icon-wrapper">{get_icon(step1_state)}</div>
                    <div class="step-details">
                        <span class="step-title">Initialization</span>
                        <span class="step-desc">Target validation</span>
                    </div>
                </div>
                <div class="step-divider {divider1_cls}"><div class="step-divider-progress"></div></div>
                <div class="step {step2_state}">
                    <div class="step-icon-wrapper">{get_icon(step2_state)}</div>
                    <div class="step-details">
                        <span class="step-title">Swarm Execution</span>
                        <span class="step-desc">Agent reasoning</span>
                    </div>
                </div>
                <div class="step-divider {divider2_cls}"><div class="step-divider-progress"></div></div>
                <div class="step {step3_state}">
                    <div class="step-icon-wrapper">{get_icon(step3_state)}</div>
                    <div class="step-details">
                        <span class="step-title">Consensus & Report</span>
                        <span class="step-desc">Plan optimization</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        render_operations_stepper()
        
        run_analysis = st.button("Execute Swarm Analysis", use_container_width=True)
        
        st.markdown("##### Swarm Operational Timeline")
        console_placeholder = st.empty()
        
        def render_timeline():
            with console_placeholder.container():
                st.markdown("<div class='timeline-container'>", unsafe_allow_html=True)
                for index, log in enumerate(st.session_state.agent_logs):
                    agent = log["agent"]
                    status = log["status"]
                    message = log["message"]
                    output = log.get("output", "")
                    
                    badge_map = {
                        "Coordinator": "badge-coordinator",
                        "Data Analyzer": "badge-analyzer",
                        "Risk Detector": "badge-risk",
                        "Demand Trend Detector": "badge-trend",
                        "Recommender": "badge-recommender",
                        "Report Writer": "badge-writer"
                    }
                    badge_cls = badge_map.get(agent, "badge-coordinator")
                    
                    node_html = STATUS_NODES.get(status, STATUS_NODES["running"])
                    agent_icon = AGENT_ICONS.get(agent, "")
                    
                    st.markdown(f"""
                    <div class="timeline-item">
                        {node_html}
                        <div class="timeline-card">
                            <div class="timeline-header">
                                <div class="agent-name-tag">
                                    {agent_icon}
                                    <span class="agent-badge {badge_cls}">{agent}</span>
                                </div>
                                <span class="timeline-time">{datetime.now().strftime("%H:%M:%S")}</span>
                            </div>
                            <div class="timeline-body">
                                {message}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if output:
                        with st.expander(f"View {agent} Swarm Summary", expanded=(agent in ["Report Writer", "Coordinator"] and status in ["consensus", "done"])):
                            st.markdown(output)
                            
                st.markdown("</div>", unsafe_allow_html=True)

        if run_analysis:
            st.session_state.agent_logs = []
            st.session_state.agent_reports = {}
            st.session_state.final_report = ""
            st.session_state.analysis_run = False
            st.session_state.execution_duration = None
            
            start_time = time.time()
            render_operations_stepper()
            
            orchestrator = StockPilotOrchestrator(
                api_key=api_key if api_key and api_key.strip() else None,
                model=model_choice
            )
            
            # Consume analysis stream
            for step in orchestrator.run_multi_agent(st.session_state.file_path):
                st.session_state.agent_logs.append(step)
                if step["status"] == "done":
                    st.session_state.agent_reports[step["agent"]] = step["output"]
                    if step["agent"] == "Report Writer":
                        st.session_state.final_report = step["output"]
                elif step["status"] == "complete":
                    st.session_state.analysis_run = True
                    st.session_state.execution_duration = time.time() - start_time
                render_operations_stepper()
                render_timeline()
                
            st.success("Consensus Swarm Reasoning Completed!")
            st.rerun()
        elif st.session_state.agent_logs:
            render_timeline()
        else:
            st.info("System Standby. Launch the swarm analysis loop to coordinate agents.")

    with col_timeline:
        st.subheader("Active Swarm Directory")
        st.markdown("Specialist agent configurations and active operations tunnels:")
        
        agent_cards = [
            ("Coordinator", "Root Orchestrator", "Oversees agent sequence, executes consensus gates, and commits safety modifications.", "badge-coordinator"),
            ("Data Analyzer", "Specialist Agent", "Validates schema structures and profiles warehouse stock configurations.", "badge-analyzer"),
            ("Risk Detector", "Specialist Agent", "Scans capital locks, supplier delays, and impending supply threats.", "badge-risk"),
            ("Demand Trend Detector", "Specialist Agent", "Evaluates velocity logs and projects depletion curves.", "badge-trend"),
            ("Recommender", "Specialist Agent", "Computes target purchase quantities and safety stock allocations.", "badge-recommender"),
            ("Report Writer", "Specialist Agent", "Compiles executive briefings and logs optimized reorders.", "badge-writer")
        ]
        
        for name, role, desc, badge in agent_cards:
            status_text = "Standby"
            border_style = "border-left: 3px solid rgba(255,255,255,0.06);"
            bg_color = "background: rgba(15, 22, 36, 0.4);"
            
            if st.session_state.agent_logs:
                active = next((l for l in reversed(st.session_state.agent_logs) if l["agent"] == name), None)
                if active:
                    status_text = "Active/Done" if active["status"] in ["done", "complete", "consensus"] else "Executing"
                    border_style = "border-left: 3px solid #10B981;" if active["status"] in ["done", "complete", "consensus"] else "border-left: 3px solid #F59E0B;"
                    bg_color = "background: rgba(15, 22, 36, 0.65);"
                    
            agent_icon = AGENT_ICONS.get(name, "")
            
            st.markdown(f"""
            <div style="padding: 14px; margin-bottom: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.04); {border_style} {bg_color} box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="color:#FFFFFF; display:flex; align-items:center;">{agent_icon}</span>
                        <span class="agent-badge {badge}" style="font-size:11px; font-weight:700;">{name}</span>
                        <span style="font-size: 11px; color:#64748B;">{role}</span>
                    </div>
                    <span style="font-size: 11px; font-weight: 600; color:{'#10B981' if status_text == 'Active/Done' else '#F59E0B' if status_text == 'Executing' else '#64748B'};">
                        {status_text}
                    </span>
                </div>
                <div style="font-size: 12px; color: #CBD5E1; margin-top: 8px; line-height: 1.4;">
                    {desc}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Full-width Operational Reference Guide at the bottom of Tab 1
    st.markdown("---")
    with st.container(border=True):
        st.markdown("""<div style="padding: 10px;">
<h4 style="color: #0EA5E9; font-family: 'Outfit', sans-serif; margin-bottom: 12px; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; display:flex; align-items:center; gap:8px;">
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10"/><path d="M6 10h10"/></svg>
Operational Reference & Swarm Metrics Glossary
</h4>
<div style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
<p style="margin-bottom: 12px;">
This dashboard is powered by a multi-agent AI coordination swarm. Specialist agents coordinate sequentially to analyze warehouse datasets, evaluate stock level warning thresholds, and compile consensus purchase reorders. Use this guide to understand the operations and metrics:
</p>
<ul style="padding-left: 20px; margin-bottom: 6px; display: flex; flex-direction: column; gap: 10px;">
<li>
<strong style="color: #FFFFFF;">Inventory Health Score:</strong> Measures the percentage of catalog SKUs in a stable, optimal condition. Any product that has run out (<span style="color:#EF4444; font-weight:700;">Stockout</span>), has fallen below its safety threshold (<span style="color:#FBBF24; font-weight:700;">Critical Shortage</span>), or has excessive capital tied up (<span style="color:#C084FC; font-weight:700;">Overstock</span>) is marked as unhealthy. For example, in a severely depleted test dataset where 100% of the items are stockouts or shortages, the score resolves to <span style="color:#EF4444; font-weight:700;">0.0% Critical</span>.
</li>
<li>
<strong style="color: #FFFFFF;">Procurement Priorities & Badges:</strong>
<ul style="padding-left: 15px; margin-top: 6px; display: flex; flex-direction: column; gap: 4px;">
<li><span class="badge priority-critical">CRITICAL</span> Assigned when physical stock is less than or equal to the required <strong style="color:#FFFFFF;">Safety Stock</strong>. Reorder is urgent to prevent operational stoppage.</li>
<li><span class="badge priority-high">HIGH</span> Assigned when stock is below the <strong style="color:#FFFFFF;">Reorder Point (ROP)</strong> but still above Safety Stock.</li>
<li><span class="badge priority-overstock">OVERSTOCK</span> Assigned when stock is greater than 3x the ROP, locking up valuable warehouse cash. No new orders are allowed (the swarm freezes intake).</li>
<li><span class="badge priority-normal">NORMAL</span> Assigned to stable inventory lines that do not require any replenishment.</li>
</ul>
</li>
<li>
<strong style="color: #FFFFFF;">Swarm Consensus Logic:</strong> During analysis, the Risk Detector and Recommender challenge basic formulas. For example, if a supplier shows a high alert ratio, the swarm automatically increases the purchase order by 15% to hedge against shipping delays.
</li>
</ul>
</div>
</div>""", unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 2: STRATEGIC OPERATIONS ANALYTICS
# -------------------------------------------------------------
with tab2:
    if not st.session_state.analysis_run:
        st.subheader("Strategic Operations Dashboard")
        st.info("Analytics pending. Run the Swarm Controller in Mission Control to calculate statistics.")
        col_sk1, col_sk2 = st.columns(2)
        with col_sk1:
            render_skeleton_loaders(2)
        with col_sk2:
            render_skeleton_loaders(2)
    else:
        st.subheader("Strategic Operations Dashboard")
        
        # Second row metrics specific details
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        
        with col_kpi1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-title">Total Valuation</span>
                    <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                </div>
                <div>
                    <div class="kpi-value">${overview_combined['Total Valuation']:,.2f}</div>
                    <div class="kpi-trend trend-neutral">● Stable Capital Active</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi2:
            alerts_val = overview_combined['Stockouts'] + overview_combined['Critical Shortages']
            alerts_cls = 'trend-down' if alerts_val > 0 else 'trend-up'
            alerts_sym = '▼' if alerts_val > 0 else '▲'
            alerts_txt = 'Alerts Active' if alerts_val > 0 else 'Secure'
            st.markdown(f"""
            <div class="kpi-card kpi-alerts">
                <div class="kpi-header">
                    <span class="kpi-title">Shortage SKUs</span>
                    <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
                </div>
                <div>
                    <div class="kpi-value">{alerts_val} items</div>
                    <div class="kpi-trend {alerts_cls}">{alerts_sym} {alerts_txt}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi3:
            st.markdown(f"""
            <div class="kpi-card kpi-health">
                <div class="kpi-header">
                    <span class="kpi-title">Stock Units</span>
                    <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="2" y="2" width="20" height="20" rx="2"/></svg>
                </div>
                <div>
                    <div class="kpi-value">{overview_combined['Total Stock Units']:,} units</div>
                    <div class="kpi-trend trend-neutral">● Balanced Counted</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_kpi4:
            st.markdown(f"""
            <div class="kpi-card kpi-timer">
                <div class="kpi-header">
                    <span class="kpi-title">Exhaustion Speed</span>
                    <svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                </div>
                <div>
                    <div class="kpi-value">{depletion['Overall Avg Days of Supply']} Days</div>
                    <div class="kpi-trend trend-neutral">● Average Depletion</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Visuals Grid
        col_vis1, col_vis2 = st.columns(2)
        
        with col_vis1:
            with st.container(border=True):
                st.markdown("#### Inventory Health Index")
                # SVG gauge output
                st.markdown(render_svg_gauge(overview_combined["Inventory Health Score"]), unsafe_allow_html=True)
                
                # Dynamic AI Insight
                h_val = overview_combined["Inventory Health Score"]
                if h_val >= 80:
                    insight_rec = "Health score is high. Keep safety metrics as configured. Maintain lean reorders."
                    insight_imp = "Low"
                elif h_val >= 50:
                    insight_rec = "Inventory is facing moderate shortage warnings. Release orders for high-priority SKUs immediately."
                    insight_imp = "Medium"
                else:
                    insight_rec = "Immediate intervention required. High stockout rates are stalling sales. Re-optimize lead times."
                    insight_imp = "Critical"
                    
                st.markdown(render_ai_insight_card("High", insight_imp, insight_rec, ["Coordinator", "Data Analyzer", "Risk Detector"]), unsafe_allow_html=True)
                
        with col_vis2:
            with st.container(border=True):
                st.markdown("#### Capital Lockup Analysis")
                if risks["Capital Lockups"]:
                    lockups_df = pd.DataFrame(risks["Capital Lockups"])
                    fig_lock = px.bar(
                        lockups_df, x="Tied Up Capital", y="Product Name", orientation="h",
                        text=lockups_df["Tied Up Capital"].map(lambda val: f"${val:,.0f}"),
                        labels={"Tied Up Capital": "Excess Valuation Locked ($)"}
                    )
                    fig_lock.update_traces(
                        marker_color="rgba(239, 68, 68, 0.7)",
                        marker_line_color="#EF4444",
                        marker_line_width=1.2,
                        textposition="outside",
                        hovertemplate="Product: <b>%{y}</b><br>Excess Capital: <b>$%{x:,.2f}</b><extra></extra>"
                    )
                    fig_lock.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font_color='#CBD5E1', font_family='Plus Jakarta Sans',
                        margin=dict(t=20, b=10, l=10, r=40),
                        xaxis=dict(gridcolor='rgba(255,255,255,0.05)', showgrid=True, title=None),
                        yaxis=dict(showgrid=False, title=None, categoryorder='total ascending'),
                        height=250
                    )
                    st.plotly_chart(fig_lock, use_container_width=True, config={'displayModeBar': False})
                    
                    excess_sku = lockups_df.iloc[-1]["Product Name"] if not lockups_df.empty else "key items"
                    lockup_rec = f"Freeze further procurement for '{excess_sku}' to release tied-up capital and balance warehouse capacity."
                    lockup_imp = "High"
                else:
                    st.info("No excess capital lockups detected. Warehouse footprints are lean.")
                    lockup_rec = "Warehouse allocation is optimal. Continue running weekly inventory sync cycles."
                    lockup_imp = "Low"
                    
                st.markdown(render_ai_insight_card("High", lockup_imp, lockup_rec, ["Risk Detector", "Recommender"]), unsafe_allow_html=True)

        col_vis3, col_vis4 = st.columns(2)
        
        with col_vis3:
            with st.container(border=True):
                st.markdown("#### SKU Performance Velocity Map (Top 30 Valuations)")
                df_scatter_sorted = df.copy()
                df_scatter_sorted["Valuation"] = df_scatter_sorted["Current Stock"] * df_scatter_sorted["Unit Cost"]
                df_scatter_top = df_scatter_sorted.sort_values(by="Valuation", ascending=False).head(30)
                
                fig_scatter = px.scatter(
                    df_scatter_top, x="Daily Sales Rate", y="Unit Cost", color="Category",
                    size="Current Stock", hover_name="Product Name", size_max=25,
                    labels={"Daily Sales Rate": "Daily Sales Rate (Units/Day)", "Unit Cost": "Unit Cost ($)"},
                    color_discrete_sequence=["#0EA5E9", "#10B981", "#818CF8", "#F59E0B", "#EC4899"]
                )
                fig_scatter.update_traces(
                    marker=dict(
                        opacity=0.75,
                        line=dict(width=1.2, color='rgba(255,255,255,0.2)')
                    ),
                    hovertemplate="<b>%{hovertext}</b><br>Sales Rate: <b>%{x:.2f} units/day</b><br>Unit Cost: <b>$%{y:,.2f}</b><br>Current Stock: <b>%{marker.size} units</b><extra></extra>"
                )
                fig_scatter.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#CBD5E1', font_family='Plus Jakarta Sans',
                    margin=dict(t=25, b=40, l=40, r=130),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                    height=280,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=9))
                )
                st.plotly_chart(fig_scatter, use_container_width=True, config={'displayModeBar': False})
                
                scatter_rec = "Ensure safety stocks for high-velocity items (lower-right quadrants) have responsive buffers to prevent rapid depletion."
                st.markdown(render_ai_insight_card("Medium", "High", scatter_rec, ["Data Analyzer", "Demand Trend Detector"]), unsafe_allow_html=True)
                
        with col_vis4:
            with st.container(border=True):
                st.markdown("#### Stock Category Valuation Allocation")
                df_tree = df.copy()
                df_tree["Stock Valuation"] = df_tree["Current Stock"] * df_tree["Unit Cost"]
                df_tree = df_tree[df_tree["Stock Valuation"] > 0]
                
                fig_tree = px.treemap(
                    df_tree, path=["Category", "Product Name"], values="Stock Valuation",
                    color="Stock Valuation", 
                    color_continuous_scale=["#0A0E1A", "#1E293B", "#2563EB", "#0ea5e9"],
                    labels={"StockValuation": "Stock Valuation"}
                )
                fig_tree.update_traces(
                    hovertemplate="Category/Product: <b>%{id}</b><br>Stock Valuation: <b>$%{value:,.2f}</b><extra></extra>",
                    textfont=dict(family="Outfit", color="#FFFFFF"),
                    marker=dict(line=dict(color='rgba(255,255,255,0.08)', width=1))
                )
                fig_tree.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#CBD5E1', margin=dict(t=10, b=10, l=10, r=10),
                    height=280, coloraxis_showscale=False
                )
                st.plotly_chart(fig_tree, use_container_width=True, config={'displayModeBar': False})
                
                cat_val = df_tree.groupby("Category")["Stock Valuation"].sum()
                max_cat = cat_val.idxmax() if not cat_val.empty else "N/A"
                tree_rec = f"Category '{max_cat}' represents the largest capital footprint. Maintain active lead-time monitoring on these suppliers."
                st.markdown(render_ai_insight_card("High", "Medium", tree_rec, ["Data Analyzer", "Coordinator"]), unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 3: SWARM RECOMMENDATIONS
# -------------------------------------------------------------
with tab3:
    if not st.session_state.analysis_run:
        st.subheader("Replenishment Procurement Optimization")
        st.info("Replenishment recommendations are pending. Start multi-agent analysis in Mission Control to calculate reorders.")
        render_skeleton_loaders(1)
    else:
        st.subheader("Replenishment Procurement Optimization")
        st.markdown("Replenishment purchase plans compiled with safety lead buffers and overstock cuts (consensually approved).")
        
        # Recommendations Grid
        opt_df = pd.DataFrame(optimized_recs)
        
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        cat_sel = col_f1.selectbox("Filter Category", ["All"] + list(opt_df["Category"].unique()))
        prior_sel = col_f2.selectbox("Filter Priority Level", ["All", "CRITICAL", "HIGH", "OVERSTOCK", "NORMAL", "NONE"])
        query_sel = col_f3.text_input("Search SKUs or Suppliers", "")
        
        # Filter dataset
        filtered_opt = opt_df.copy()
        if cat_sel != "All":
            filtered_opt = filtered_opt[filtered_opt["Category"] == cat_sel]
        if prior_sel != "All":
            filtered_opt = filtered_opt[filtered_opt["Priority"] == prior_sel]
        if query_sel:
            filtered_opt = filtered_opt[
                filtered_opt["Product Name"].str.contains(query_sel, case=False) |
                filtered_opt["Product ID"].str.contains(query_sel, case=False) |
                filtered_opt["Supplier Name"].str.contains(query_sel, case=False)
            ]
            
        display_columns = [
            "Product ID", "Product Name", "Category", "Current Stock", 
            "Reorder Point", "Safety Stock", "Needs Restock", "Suggested Qty", 
            "Unit Cost", "Estimated Restock Cost", "Priority", "Consensus Note", "Supplier Name"
        ]
        
        # Highlight and Sorting helper function for custom HTML table
        def highlight_search(text, query):
            if not query:
                return text
            text_str = str(text)
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text_str)
            
        def render_custom_recommendations_table(df_recs, query=""):
            table_id = "recs-table"
            html_rows = []
            
            headers = [
                ("Product ID", False),
                ("Product Name", False),
                ("Category", False),
                ("Stock", True),
                ("ROP", True),
                ("Safety Stock", True),
                ("Restock?", False),
                ("Reorder Qty", True),
                ("Unit Cost", True),
                ("Estimated Cost", True),
                ("Priority", False),
                ("Consensus Note", False),
                ("Supplier", False)
            ]
            
            # Start rendering
            html_rows.append('<div class="table-container">')
            html_rows.append(f'<table id="{table_id}" class="enterprise-table">')
            
            # Headers
            html_rows.append('<thead><tr>')
            for idx, (label, is_num) in enumerate(headers):
                is_num_val = "true" if is_num else "false"
                html_rows.append(f'<th onclick="sortTable(\'{table_id}\', {idx}, {is_num_val})">{label}</th>')
            html_rows.append('</tr></thead>')
            
            # Body
            html_rows.append('<tbody>')
            for _, row in df_recs.iterrows():
                html_rows.append('<tr>')
                
                # Highlight columns where text might be searched
                p_id = highlight_search(row["Product ID"], query)
                p_name = highlight_search(row["Product Name"], query)
                cat = highlight_search(row["Category"], query)
                note = highlight_search(row["Consensus Note"], query)
                sup = highlight_search(row["Supplier Name"], query)
                
                # Badge assignments
                needs = row["Needs Restock"]
                needs_cls = "badge restock-yes" if needs == "Yes" else "restock-no"
                
                priority = row["Priority"]
                p_badge_cls = "badge priority-none"
                if priority == "CRITICAL":
                    p_badge_cls = "badge priority-critical"
                elif priority == "HIGH":
                    p_badge_cls = "badge priority-high"
                elif priority == "OVERSTOCK":
                    p_badge_cls = "badge priority-overstock"
                elif priority == "NORMAL":
                    p_badge_cls = "badge priority-normal"
                
                html_rows.append(f'<td>{p_id}</td>')
                html_rows.append(f'<td>{p_name}</td>')
                html_rows.append(f'<td>{cat}</td>')
                html_rows.append(f'<td>{int(row["Current Stock"]):,}</td>')
                html_rows.append(f'<td>{int(row["Reorder Point"]):,}</td>')
                html_rows.append(f'<td>{int(row["Safety Stock"]):,}</td>')
                html_rows.append(f'<td><span class="{needs_cls}">{needs}</span></td>')
                html_rows.append(f'<td>{int(row["Suggested Qty"]):,}</td>')
                html_rows.append(f'<td>${row["Unit Cost"]:,.2f}</td>')
                html_rows.append(f'<td>${row["Estimated Restock Cost"]:,.2f}</td>')
                html_rows.append(f'<td><span class="{p_badge_cls}">{priority}</span></td>')
                html_rows.append(f'<td>{note}</td>')
                html_rows.append(f'<td>{sup}</td>')
                
                html_rows.append('</tr>')
                
            html_rows.append('</tbody></table></div>')
            
            # Sorting JavaScript
            js_sort = """
            <script>
            if (typeof sortTable === 'undefined') {
                window.sortTable = function(tableId, colIndex, isNumeric) {
                    var table = document.getElementById(tableId);
                    if (!table) return;
                    var tbody = table.tBodies[0];
                    var rows = Array.from(tbody.rows);
                    var dir = table.getAttribute("data-sort-dir-" + colIndex) === "asc" ? "desc" : "asc";
                    
                    // Reset headings indicators
                    for (var i = 0; i < table.rows[0].cells.length; i++) {
                        table.setAttribute("data-sort-dir-" + i, "");
                    }
                    table.setAttribute("data-sort-dir-" + colIndex, dir);
                    
                    rows.sort(function(a, b) {
                        var valA = a.cells[colIndex].textContent || a.cells[colIndex].innerText;
                        var valB = b.cells[colIndex].textContent || b.cells[colIndex].innerText;
                        
                        valA = valA.replace(/[$,]/g, '').trim();
                        valB = valB.replace(/[$,]/g, '').trim();
                        
                        if (isNumeric) {
                            var nA = parseFloat(valA);
                            var nB = parseFloat(valB);
                            if (isNaN(nA)) nA = 0;
                            if (isNaN(nB)) nB = 0;
                            return dir === "asc" ? nA - nB : nB - nA;
                        } else {
                            return dir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
                        }
                    });
                    
                    rows.forEach(function(row) {
                        tbody.appendChild(row);
                    });
                }
            }
            </script>
            """
            html_rows.append(js_sort)
            return "\n".join(html_rows)
            
        # Read style.css and render custom table inside sandboxed iframe components
        css_data = ""
        if os.path.exists("style.css"):
            with open("style.css") as f:
                css_data = f.read()
                
        table_html = render_custom_recommendations_table(filtered_opt[display_columns], query_sel)
        full_html = f"""
        <html>
        <head>
            <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #07090E;
                font-family: 'Plus Jakarta Sans', sans-serif;
            }}
            {css_data}
            </style>
        </head>
        <body>
            {table_html}
        </body>
        </html>
        """
        st.components.v1.html(full_html, height=450, scrolling=True)
        
        # Procurement table explainability card (AI Explainability)
        st.markdown(render_ai_insight_card(
            "High", 
            "Critical" if filtered_opt["Priority"].eq("CRITICAL").any() else "High",
            "The procurement plan is compiled using safety-stock buffers and replenishment order logic. The swarm has frozen intake for overstock SKUs to release warehouse capital and prioritized critical reorders.",
            ["Coordinator", "Risk Detector", "Demand Trend Detector", "Recommender"]
        ), unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Export & Download Report Hub")
        
        col_exp1, col_exp2 = st.columns(2)
        
        # Prep report content
        report_content = st.session_state.final_report
        if not report_content:
            report_content = ExecutiveReportingSkill.generate_report(
                overview_combined, risks, depletion, 
                {"Items to Reorder": sum(1 for r in optimized_recs if r["Needs Restock"] == "Yes"), 
                 "Total Cost": sum(r["Estimated Restock Cost"] for r in optimized_recs if r["Needs Restock"] == "Yes")}
            )
            
        with col_exp1:
            st.markdown("#### Executive Brief Downloads")
            st.markdown("Download the swarm consensus report in professional PDF or Microsoft Word formatting.")
            
            # Helper to compile PDF
            pdf_lines = report_content.split("\n")
            pdf_data = generate_pdf_from_text("StockPilot AI Executive Report", pdf_lines)
            
            # Helper to compile Word
            word_data = generate_word_document_report(
                report_content, overview_combined, risks, depletion, 
                {"Items to Reorder": sum(1 for r in optimized_recs if r["Needs Restock"] == "Yes"), 
                 "Total Cost": sum(r["Estimated Restock Cost"] for r in optimized_recs if r["Needs Restock"] == "Yes")}
            )
            
            col_pdf, col_word = st.columns(2)
            with col_pdf:
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_data,
                    file_name=f"StockPilot_Executive_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            with col_word:
                st.download_button(
                    label="📝 Download MS Word",
                    data=word_data,
                    file_name=f"StockPilot_Executive_Report_{datetime.now().strftime('%Y%m%d')}.doc",
                    mime="application/msword",
                    use_container_width=True
                )
            
        with col_exp2:
            st.markdown("#### Recommendations CSV Plan")
            st.markdown("Download the raw SKU-level recommendations list as a CSV file to import directly into ERP systems.")
            
            csv_bytes = filtered_opt[display_columns].to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download Reorder Plan (CSV)",
                data=csv_bytes,
                file_name=f"StockPilot_Replenishment_Plan_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Executive Preview
        st.markdown("---")
        st.subheader("Executive Summary Live Preview")
        
        # Render presentation-quality report card
        st.markdown(render_premium_executive_report(
            report_content, overview_combined, risks, depletion, 
            {"Items to Reorder": sum(1 for r in optimized_recs if r["Needs Restock"] == "Yes"), 
             "Total Cost": sum(r["Estimated Restock Cost"] for r in optimized_recs if r["Needs Restock"] == "Yes")}
        ), unsafe_allow_html=True)
