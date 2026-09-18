import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import get_database_status, get_all_employees
from query_engine import (
    analyze_question,
    audit_employee_responsibilities,
    reassign_employee_roles
)

# Page Configuration
st.set_page_config(
    page_title="Everest AI | 7Span",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #E22D2D;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #6c757d;
        margin-bottom: 25px;
    }
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 12px;
    }
    div[data-testid="stExpander"] {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .handover-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://everest.7span.work/assets/everest-icon-32x32-B2CJPoPt.svg", width=40)
    st.title("Everest AI")
    st.caption("7Span Intelligent Operations Assistant")
    st.markdown("---")
    
    # Database Connection Status
    status = get_database_status()
    if status["connected"]:
        st.success(f"🟢 **Connected** ({status['mode']})")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Projects", status["projects"])
            st.metric("Timesheets", status["timesheets"])
        with col2:
            st.metric("Billables", status["billables"])
            st.metric("Employees", status["employees"])
    else:
        st.error(f"🔴 DB Error: {status.get('error', 'Disconnected')}")
    
    st.markdown("---")
    
    # Dynamic Date Range Filter
    st.subheader("📅 Date Range Filter")
    date_selection = st.date_input(
        "Filter data between dates:",
        value=(date(2026, 8, 1), date(2026, 9, 30)),
        min_value=date(2026, 1, 1),
        max_value=date(2026, 12, 31)
    )
    
    start_filter, end_filter = None, None
    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_filter, end_filter = date_selection
    elif isinstance(date_selection, (tuple, list)) and len(date_selection) == 1:
        start_filter = end_filter = date_selection[0]
    else:
        start_filter, end_filter = date(2026, 8, 1), date(2026, 9, 30)

    st.caption(f"Active filter: `{start_filter}` to `{end_filter}`")
    st.markdown("---")
    
    st.subheader("💡 Quick Prompts")
    quick_prompts = [
        "Who is PC, AM, SC and JC assigned to each project?",
        "Project-wise active jobs, allocated employees and logged hours",
        "Check if Mitesh Thakar has any jobs assigned",
        "How many active projects and active jobs?",
        "Show overdue billables and days delayed"
    ]
    
    selected_prompt = None
    for qp in quick_prompts:
        if st.button(qp, use_container_width=True, key=f"btn_{qp}"):
            selected_prompt = qp

    st.markdown("---")
    show_sql = st.checkbox("Show Generated SQL Queries", value=True)
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# ----------------- CHAT STATE -----------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "👋 **Welcome to Everest AI!**\n\nYou can ask about:\n* **Project Governance:** Who is assigned as PC, AM, SC, and JC for each project, and whether billables are pending.\n* **Employee Exit & Handover:** Check what active jobs, allocations, or coordinator roles an exiting employee has.\n* **Deep Project Breakdown:** View active jobs, allocated employees, and logged hours across custom date ranges.",
            "data": None
        }
    ]

# ----------------- MAIN VIEW -----------------
st.markdown("<div class='main-title'>🏔️ Everest AI Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Operations, Project Governance, and Employee Handover Management</div>", unsafe_allow_html=True)

# ----------------- INTERACTIVE EXIT & HANDOVER TOOL -----------------
with st.expander("🔄 **Employee Exit / Layoff Handover Assistant (SOP Policy)**", expanded=False):
    st.markdown("""
    <div class='handover-box'>
        <b>Everest Exit SOP Policy:</b> When an employee is exiting or laid off, safely audit their active responsibilities (PC, AM, SC, JC, or allocated jobs) and reassign them to a colleague in 1 click without data loss.
    </div>
    """, unsafe_allow_html=True)
    
    employees = get_all_employees()
    emp_options = {f"{e['name']} ({e['role']} • {e['grade']})": e["id"] for e in employees}
    
    col_from, col_to = st.columns(2)
    with col_from:
        selected_from_label = st.selectbox("1. Select Exiting / Departing Employee:", list(emp_options.keys()), key="select_exit_emp")
        from_id = emp_options[selected_from_label]
        
    with col_to:
        # Filter out the exiting employee from successor list
        successor_options = {k: v for k, v in emp_options.items() if v != from_id}
        selected_to_label = st.selectbox("2. Select Successor / Replacement Colleague:", list(successor_options.keys()), key="select_successor_emp")
        to_id = successor_options[selected_to_label]
        
    # Run Audit
    audit_data = audit_employee_responsibilities(from_id)
    
    st.markdown(f"#### Active Responsibilities for **{selected_from_label.split('(')[0]}**:")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Projects (as PC/AM/SC)", len(audit_data["projects_as_coordinator"]))
    with m2:
        st.metric("Active Jobs (as JC)", len(audit_data["jobs_as_jc"]))
    with m3:
        st.metric("Job Allocations", len(audit_data["allocated_jobs"]))
    with m4:
        st.metric("Unreviewed Hours", f"{audit_data['unreviewed_hours']}h")
        
    if audit_data["total_responsibilities"] > 0:
        tabs = st.tabs(["Projects as Coordinator", "Jobs as JC", "Allocated Team Jobs"])
        with tabs[0]:
            if not audit_data["projects_as_coordinator"].empty:
                st.dataframe(audit_data["projects_as_coordinator"], use_container_width=True)
            else:
                st.caption("No projects managed as PC/AM/SC.")
        with tabs[1]:
            if not audit_data["jobs_as_jc"].empty:
                st.dataframe(audit_data["jobs_as_jc"], use_container_width=True)
            else:
                st.caption("No jobs managed as JC.")
        with tabs[2]:
            if not audit_data["allocated_jobs"].empty:
                st.dataframe(audit_data["allocated_jobs"], use_container_width=True)
            else:
                st.caption("No active job allocations.")

        # Reassign Action Button
        reassign_choice = st.radio(
            "Select responsibilities to transfer:",
            ["All Responsibilities", "Only Coordinator Roles (PC, AM, SC, JC)", "Only Team Member Allocations"],
            horizontal=True
        )
        
        type_mapping = {
            "All Responsibilities": "all",
            "Only Coordinator Roles (PC, AM, SC, JC)": "jc",
            "Only Team Member Allocations": "allocations"
        }
        
        if st.button("🚀 Execute Safe Handover & Reassign in Database", type="primary", use_container_width=True):
            result = reassign_employee_roles(from_id, to_id, type_mapping[reassign_choice])
            st.success(f"✅ Handover Completed! {result['summary']}")
            st.rerun()
    else:
        st.info("✅ This employee has no active projects, jobs, or allocations. Safe to offboard.")

st.markdown("---")

# ----------------- RENDER CHAT HISTORY -----------------
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        
        if msg.get("data"):
            data = msg["data"]
            
            # Metrics Row
            if data.get("metrics"):
                cols = st.columns(len(data["metrics"]))
                for i, (k, v) in enumerate(data["metrics"].items()):
                    with cols[i]:
                        st.metric(k, v)
            
            # Data Table
            if data.get("df") is not None and not data["df"].empty:
                st.dataframe(data["df"], use_container_width=True)
            
            # Chart Visualization
            if data.get("chart_type") == "bar" and data.get("df") is not None and not data["df"].empty:
                try:
                    fig = px.bar(
                        data["df"], 
                        x=data.get("chart_x"), 
                        y=data.get("chart_y"), 
                        color=data.get("chart_x"),
                        title=f"{data.get('chart_y')} by {data.get('chart_x')}",
                        template="plotly_white"
                    )
                    fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
            
            # AI Business Insight
            if data.get("insight"):
                st.info(data["insight"])
            
            # Expandable SQL View
            if show_sql and data.get("sql"):
                with st.expander("🔍 View Generated SQL Query"):
                    st.code(data["sql"], language="sql")

# ----------------- INPUT HANDLING -----------------
user_input = st.chat_input("Ask any question (e.g. 'Who is PC, AM, SC assigned to each project?' or 'Check if Mitesh Thakar has jobs')...")

if selected_prompt:
    user_input = selected_prompt

if user_input:
    st.session_state["messages"].append({
        "role": "user",
        "content": user_input,
        "data": None
    })
    
    with st.spinner("Analyzing Everest database..."):
        result = analyze_question(user_input, start_date=start_filter, end_date=end_filter)
    
    st.session_state["messages"].append({
        "role": "assistant",
        "content": result["answer"],
        "data": result
    })
    
    st.rerun()
