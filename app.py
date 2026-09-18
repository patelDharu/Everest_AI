# -*- coding: utf-8 -*-
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import csv_importer
from database import get_database_status, get_all_employees
from query_engine import (
    analyze_question,
    audit_employee_responsibilities,
    reassign_employee_roles,
    get_employee_granular_roles,
    reassign_specific_entity,
    get_everest_projects_view,
    get_everest_jobs_view,
    get_everest_billables_view,
    get_everest_overdue_extensions_view,
    reset_demo_handover_data
)

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="Everest ERP | 7Span",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- AUTHENTIC 7SPAN EVEREST DESIGN SYSTEM -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Remove default Streamlit top header padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    
    /* 7Span Left Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
        width: 260px !important;
    }
    
    /* Hide Radio Circles in Navigation - Make them look like real SaaS menu items */
    div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        display: flex !important;
        align-items: center !important;
        padding: 9px 14px !important;
        border-radius: 8px !important;
        margin-bottom: 3px !important;
        color: #475569 !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"],
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        background-color: #fef2f2 !important;
        color: #dc2626 !important;
        font-weight: 600 !important;
        border-left: 3px solid #dc2626 !important;
    }
    
    /* 7Span Branding Header in Sidebar */
    .company-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 4px 6px 16px 6px;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 14px;
    }
    .company-logo-badge {
        width: 38px;
        height: 38px;
        background-color: #E22D2D;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 800;
        font-size: 1.25rem;
    }
    .company-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .company-subtitle {
        font-size: 0.76rem;
        color: #64748b;
    }
    
    /* Top Navigation Bar */
    .top-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 12px;
        margin-bottom: 16px;
        border-bottom: 1px solid #f1f5f9;
    }
    .breadcrumb-text {
        font-size: 0.88rem;
        color: #64748b;
        font-weight: 500;
    }
    .breadcrumb-current {
        color: #0f172a;
        font-weight: 600;
    }
    
    /* Quick Links Grid Card */
    .quick-link-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 16px;
        display: flex;
        align-items: center;
        gap: 14px;
        transition: all 0.15s ease-in-out;
        margin-bottom: 12px;
    }
    .quick-link-box:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        transform: translateY(-1px);
    }
    .quick-icon-box {
        width: 42px;
        height: 42px;
        border-radius: 8px;
        background-color: #fee2e2;
        color: #E22D2D;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        flex-shrink: 0;
    }
    .quick-title-text {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 2px;
    }
    .quick-subtitle-text {
        font-size: 0.78rem;
        color: #64748b;
    }
    
    /* Chatbot Panel Container */
    .chatbot-container {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.06);
    }
    .chatbot-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 10px;
        margin-bottom: 12px;
        border-bottom: 1px solid #f1f5f9;
    }
    .chatbot-title {
        font-weight: 700;
        font-size: 1.05rem;
        color: #E22D2D;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .online-badge {
        font-size: 0.72rem;
        background-color: #def7ec;
        color: #03543f;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    
    /* User Profile Footer in Sidebar */
    .profile-footer {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin-top: 20px;
    }
    .profile-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background-color: #0284c7;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE INITIALIZATION -----------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hello! 👋 I'm your **Everest AI Assistant**.\n\n"
                       "I can look up projects, revenue, or **reassign jobs in real-time** when someone leaves.\n\n"
                       "💡 **Try 1-Click Handover:** Click the red button below to assign Ganesh's jobs to **Jay Patel, Bhavik Vachhani, and Dhruv Nayak** and watch the Jobs table on the left update live!",
            "data": None
        }
    ]

if "show_assistant" not in st.session_state:
    st.session_state["show_assistant"] = True

# ----------------- SIDEBAR (AUTHENTIC 7SPAN EVEREST ERP) -----------------
with st.sidebar:
    # 7Span Logo & Branding
    st.markdown("""
    <div class="company-header">
        <div class="company-logo-badge">7</div>
        <div>
            <div class="company-title">7Span</div>
            <div class="company-subtitle">7Span Internet Pvt. Ltd.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Modern Navigation without radio dots
    nav_selection = st.radio(
        "Navigation Menu",
        [
            "📋 Work: Jobs",
            "📁 Work: Projects",
            "💰 Work: Billables",
            "🏠 Home (Quick Links)",
            "⏳ Reports: Overdue & Extensions",
            "🔄 Operations: Handover Assistant",
            "📂 Settings: Bulk CSV Ingestion"
        ],
        index=0,  # DEFAULT TO JOBS DIRECTORY!
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Assistant Toggle
    st.markdown("##### **🤖 AI Co-Pilot**")
    assistant_toggle = st.toggle("Show Everest AI Chatbot", value=st.session_state["show_assistant"])
    st.session_state["show_assistant"] = assistant_toggle
    
    st.markdown("---")
    
    # Live Database Metric
    db_status = get_database_status()
    if db_status["connected"]:
        st.caption("🟢 **Everest Database Connected**")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Projects", db_status["projects"])
            st.metric("Active Jobs", "2,610")
        with m2:
            st.metric("Employees", db_status["employees"])
            st.metric("Collected", "$235M+")
            
    # Bottom Profile (Matching user's screenshot #media_1789706458175.png)
    st.markdown("""
    <div class="profile-footer">
        <div class="profile-avatar">GT</div>
        <div style="flex-grow:1; min-width:0;">
            <div style="font-weight:600; font-size:0.86rem; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Ganesh Thamangalath</div>
            <div style="font-size:0.75rem; color:#64748b;">ganesh.t@7span.com • PM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Reset Demo Jobs (Ganesh)", use_container_width=True):
        reset_demo_handover_data()
        st.toast("✅ Ganesh's 3 demo jobs reset! Ready for handover test.")
        st.rerun()

# ----------------- MAIN EVEREST ERP CONTENT -----------------
def render_erp_content():
    # 1. JOBS DIRECTORY VIEW (DEFAULT)
    if "Jobs" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Jobs</span></div>", unsafe_allow_html=True)
        st.markdown("### **Jobs**")
        
        # Friendly non-technical banner
        st.info("💡 **Live Handover Verification:** The 3 jobs below belong to **Ganesh Thamangalath**. "
                "Use the AI Assistant on the right (or type a message) to assign them to other colleagues, and watch the **'JC (Job Coordinator)'** column update right here in real time!")
        
        # Toolbar matching Everest screenshot
        c_search, c_status, c_add = st.columns([3, 1.5, 1])
        with c_search:
            search_job = st.text_input("Search jobs...", placeholder="🔍 Search job title, project, or coordinator...", label_visibility="collapsed", key="s_job")
        with c_status:
            status_job = st.selectbox("Status", ["All", "In Progress", "Completed", "In Review"], label_visibility="collapsed", key="st_job")
        with c_add:
            st.button("➕ Job", type="primary", use_container_width=True)
            
        df_jobs = get_everest_jobs_view(search=search_job, status=status_job, limit=30)
        st.dataframe(df_jobs, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_jobs)} active jobs from Everest ERP database.")

    # 2. PROJECTS DIRECTORY VIEW
    elif "Projects" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Projects</span></div>", unsafe_allow_html=True)
        st.markdown("### **Projects**")
        
        c_search, c_status, c_add = st.columns([3, 1.5, 1])
        with c_search:
            search_proj = st.text_input("Search projects...", placeholder="🔍 Search project name or client...", label_visibility="collapsed", key="s_proj")
        with c_status:
            status_proj = st.selectbox("Status", ["All", "Active", "Archived"], label_visibility="collapsed", key="st_proj")
        with c_add:
            st.button("➕ Project", type="primary", use_container_width=True)
            
        df_proj = get_everest_projects_view(search=search_proj, status=status_proj, limit=30)
        st.dataframe(df_proj, use_container_width=True, hide_index=True)
        st.caption(f"Showing top {len(df_proj)} active projects with PC, AM, SC ownership.")

    # 3. BILLABLES VIEW
    elif "Billables" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Billables</span></div>", unsafe_allow_html=True)
        st.markdown("### **Billables**")
        
        c_search, c_status = st.columns([3.5, 1.5])
        with c_search:
            search_bill = st.text_input("Search billables...", placeholder="🔍 Search milestone or project...", label_visibility="collapsed", key="s_bill")
        with c_status:
            status_bill = st.selectbox("Status", ["All", "collected", "billed", "contracted"], label_visibility="collapsed", key="st_bill")
            
        df_bill = get_everest_billables_view(search=search_bill, status=status_bill, limit=30)
        st.dataframe(df_bill, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_bill)} billables with revenue status and coordinator details.")

    # 4. HOME (QUICK LINKS) VIEW
    elif "Home" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Home</div>", unsafe_allow_html=True)
        st.markdown("### **Quick Links**")
        
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            st.markdown("""
            <div class="quick-link-box"><div class="quick-icon-box">📢</div><div><div class="quick-title-text">What's New</div><div class="quick-subtitle-text">Check latest updates</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">📋</div><div><div class="quick-title-text">Manpower Requisition</div><div class="quick-subtitle-text">Headcount forms</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">💬</div><div><div class="quick-title-text">Discord</div><div class="quick-subtitle-text">Team chat and calls</div></div></div>
            """, unsafe_allow_html=True)
        with q2:
            st.markdown("""
            <div class="quick-link-box"><div class="quick-icon-box">📚</div><div><div class="quick-title-text">Documentation</div><div class="quick-subtitle-text">Engineering guides</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">🛡️</div><div><div class="quick-title-text">Company Policies</div><div class="quick-subtitle-text">Leave, handover SOPs</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">🎨</div><div><div class="quick-title-text">Draw.io</div><div class="quick-subtitle-text">Architecture diagrams</div></div></div>
            """, unsafe_allow_html=True)
        with q3:
            st.markdown("""
            <div class="quick-link-box"><div class="quick-icon-box">🔍</div><div><div class="quick-title-text">Case Study Finder</div><div class="quick-subtitle-text">Client success stories</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">🌊</div><div><div class="quick-title-text">Pacific</div><div class="quick-subtitle-text">Company info</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">🐙</div><div><div class="quick-title-text">GitHub</div><div class="quick-subtitle-text">Source code</div></div></div>
            """, unsafe_allow_html=True)
        with q4:
            st.markdown("""
            <div class="quick-link-box"><div class="quick-icon-box">✍️</div><div><div class="quick-title-text">Feedback & Support</div><div class="quick-subtitle-text">Anonymous feedback</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">🏜️</div><div><div class="quick-title-text">Sahara</div><div class="quick-subtitle-text">Project management</div></div></div>
            <div class="quick-link-box"><div class="quick-icon-box">⏰</div><div><div class="quick-title-text">Keka</div><div class="quick-subtitle-text">Attendance & payroll</div></div></div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### **📊 7Span Operational KPIs**")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Active Projects", "544")
        with k2:
            st.metric("Active In-Progress Jobs", "2,610")
        with k3:
            st.metric("Collected Revenue", "$235.4M USD")
        with k4:
            st.metric("Active Staff", "437")

    # 5. OVERDUE & EXTENSIONS
    elif "Overdue" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Reports > Billables > <span class='breadcrumb-current'>Overdue & Extensions</span></div>", unsafe_allow_html=True)
        st.markdown("### **Overdue & Extended Billables**")
        search_ext = st.text_input("Search extensions...", placeholder="🔍 Search justification or project...", key="s_ext")
        df_ext = get_everest_overdue_extensions_view(search=search_ext, limit=30)
        st.dataframe(df_ext, use_container_width=True, hide_index=True)

    # 6. HANDOVER MATRIX
    elif "Handover" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Operations > <span class='breadcrumb-current'>Handover SOP</span></div>", unsafe_allow_html=True)
        st.markdown("### **Employee Handover SOP Assistant**")
        
        employees = get_all_employees()
        emp_options = {f"{e['name']} ({e['role']} • {e['grade']})": e["id"] for e in employees}
        
        default_idx = 0
        for i, k in enumerate(emp_options.keys()):
            if "Ganesh Thamangalath" in k:
                default_idx = i
                break
                
        selected_from_label = st.selectbox("Select Departing Employee:", list(emp_options.keys()), index=default_idx)
        from_id = emp_options[selected_from_label]
        
        audit_data = audit_employee_responsibilities(from_id)
        granular_items = get_employee_granular_roles(from_id)
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Projects (as PC/AM/SC)", len(audit_data["projects_as_coordinator"]))
        with m2:
            st.metric("Active Jobs (as JC)", len(audit_data["jobs_as_jc"]))
        with m3:
            st.metric("Total Open Roles", audit_data["total_responsibilities"])
            
        if audit_data["total_responsibilities"] > 0:
            st.markdown("##### **Granular Reassignment Matrix:**")
            successor_options = {k: v for k, v in emp_options.items() if v != from_id}
            successor_list = list(successor_options.keys())
            
            selections = {}
            for idx, item in enumerate(granular_items, 1):
                col_item, col_succ = st.columns([3, 2])
                with col_item:
                    st.markdown(f"**{idx}. {item['name']}** (`{item['role_title']}` in *{item['project_name']}*)")
                with col_succ:
                    chosen_succ = st.selectbox(f"Assign To:", ["-- Select Colleague --"] + successor_list, key=f"mat_{item['id']}_{idx}")
                    if chosen_succ != "-- Select Colleague --":
                        selections[idx - 1] = successor_options[chosen_succ]
                st.divider()
                
            if st.button("🚀 Apply Reassignments in Database", type="primary", use_container_width=True):
                if not selections:
                    st.warning("Please select at least one colleague to assign.")
                else:
                    for item_idx, target_emp_id in selections.items():
                        it = granular_items[item_idx]
                        reassign_specific_entity(it["category"], it["type"], it["id"], target_emp_id, from_id)
                    st.success(f"✅ Handover Completed! Updated {len(selections)} roles in the database.")
                    st.rerun()
        else:
            st.success("✅ This employee has 0 active responsibilities remaining.")

    # 7. BULK CSV INGESTION
    elif "Settings" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Settings > <span class='breadcrumb-current'>Bulk CSV Sync</span></div>", unsafe_allow_html=True)
        st.markdown("### **Upload & Ingest Everest CSVs (30+ Files Supported)**")
        uploaded_files = st.file_uploader("Select 30+ CSV files at once:", type=["csv"], accept_multiple_files=True)
        if uploaded_files:
            if st.button(f"⚡ Ingest & Sync {len(uploaded_files)} Files Now", type="primary"):
                status_list = []
                for uf in uploaded_files:
                    res = csv_importer.import_single_csv(uf, uf.name)
                    status_list.append(res)
                st.success(f"✅ Successfully ingested {len(uploaded_files)} files into database!")
                st.dataframe(pd.DataFrame(status_list)[["file_name", "table_name", "rows", "status"]], use_container_width=True)
                st.rerun()


# ----------------- SIDE CHATBOT COMPONENT -----------------
def render_ai_chatbot():
    st.markdown("""
    <div class="chatbot-container">
        <div class="chatbot-header">
            <div class="chatbot-title">
                <span>🏔️</span> Everest AI Assistant
            </div>
            <div class="online-badge">● Online</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("Chat with AI to reassign jobs, check projects, or pull financials:")
    
    # Quick 1-Click Action Chips (Super user-friendly for non-technical users!)
    st.markdown("##### **⚡ Quick Actions:**")
    
    if st.button("⚡ Assign Ganesh's 3 Jobs (Jay, Bhavik, Dhruv)", type="primary", use_container_width=True):
        prompt = "Ganesh is JC, assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, and job 3 to Dhruv Nayak"
        st.session_state["messages"].append({"role": "user", "content": prompt, "data": None})
        res = analyze_question(prompt)
        st.session_state["messages"].append({"role": "assistant", "content": res["answer"], "data": res})
        st.rerun()
        
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📋 My Active Jobs", use_container_width=True):
            prompt = "Ganesh is leaving, what jobs does he have?"
            st.session_state["messages"].append({"role": "user", "content": prompt, "data": None})
            res = analyze_question(prompt)
            st.session_state["messages"].append({"role": "assistant", "content": res["answer"], "data": res})
            st.rerun()
    with c2:
        if st.button("💰 2026 Collections", use_container_width=True):
            prompt = "How much collected revenue in 2026?"
            st.session_state["messages"].append({"role": "user", "content": prompt, "data": None})
            res = analyze_question(prompt)
            st.session_state["messages"].append({"role": "assistant", "content": res["answer"], "data": res})
            st.rerun()

    st.markdown("---")
    
    # Message History
    chat_box = st.container(height=420)
    with chat_box:
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if msg.get("data") and msg["data"].get("df") is not None and not msg["data"]["df"].empty:
                    with st.expander("📊 View Data Table (Optional)", expanded=False):
                        st.dataframe(msg["data"]["df"], use_container_width=True)

    # Chat Input Box
    user_query = st.chat_input("Ask in English or Hindi (e.g. 'Assign job 1 to Jay Patel')...")
    if user_query:
        st.session_state["messages"].append({"role": "user", "content": user_query, "data": None})
        with st.spinner("Everest AI is processing..."):
            ans = analyze_question(user_query)
        st.session_state["messages"].append({"role": "assistant", "content": ans["answer"], "data": ans})
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)


# ----------------- MAIN LAYOUT RENDERER -----------------
if st.session_state["show_assistant"]:
    # 70% ERP Main View | 30% Chatbot on Right
    col_main_erp, col_side_bot = st.columns([70, 30], gap="large")
    with col_main_erp:
        render_erp_content()
    with col_side_bot:
        render_ai_chatbot()
else:
    # 100% Full Width ERP View
    render_erp_content()
