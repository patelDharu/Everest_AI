import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_database_status
from query_engine import analyze_question

# Page Configuration
st.set_page_config(
    page_title="Everest AI | 7Span",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for ChatGPT-like appearance
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
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 10px 15px;
        border-left: 4px solid #E22D2D;
    }
    div[data-testid="stExpander"] {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
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
    st.subheader("💡 Quick Prompts")
    quick_prompts = [
        "Show overdue billables and days delayed",
        "Which employees have unreviewed timesheets?",
        "List all projects, clients, and allocated hours",
        "Show our department pods and team members",
        "What is our revenue collected vs billed?"
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
            "content": "👋 **Welcome to Everest AI!** I am your 7Span intelligent assistant.\n\nYou can ask me any question about **projects, overdue billables, timesheet approvals, department pods, or revenues** in plain English or Hinglish.",
            "data": None
        }
    ]

# ----------------- MAIN CHAT VIEW -----------------
st.markdown("<div class='main-title'>🏔️ Everest AI Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Ask anything about 7Span Everest operations, projects, margins, and financials</div>", unsafe_allow_html=True)

# Render Chat History
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        
        # Render rich components if attached
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
            if data.get("chart_type") == "bar" and data.get("df") is not None:
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
user_input = st.chat_input("Ask a question about Everest (e.g., 'Show overdue billables' or 'Unreviewed timesheet backlog')...")

# If user clicked a sidebar prompt, use it
if selected_prompt:
    user_input = selected_prompt

if user_input:
    # 1. Append User Message
    st.session_state["messages"].append({
        "role": "user",
        "content": user_input,
        "data": None
    })
    
    # 2. Process with Query Engine
    with st.spinner("Analyzing Everest database..."):
        result = analyze_question(user_input)
    
    # 3. Append Assistant Response
    st.session_state["messages"].append({
        "role": "assistant",
        "content": result["answer"],
        "data": result
    })
    
    st.rerun()
