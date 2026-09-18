# -*- coding: utf-8 -*-
import os
import streamlit as st
import pandas as pd
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
import everest_ui_renderer as ur

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
        font-size: 0.90rem !important;
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
    
    /* Breadcrumbs */
    .breadcrumb-text {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .breadcrumb-current {
        color: #0f172a;
        font-weight: 600;
    }
    
    /* Profile Footer */
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

    /* Chatbot Box */
    .chatbot-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    }
    .chatbot-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 10px;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 12px;
    }
    .chatbot-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #dc2626;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .online-badge {
        font-size: 0.72rem;
        background-color: #def7ec;
        color: #03543f;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE INITIALIZATION -----------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hello! 👋 I'm your **Everest AI Assistant**.\n\n"
                       "I can answer operational questions, audit project roles, or **reassign jobs in real time** when employees depart.\n\n"
                       "💡 **Test 1-Click Handover:** Click the red button below to assign Ganesh's 3 active jobs to **Jay Patel, Bhavik Vachhani, and Dhruv Nayak**, and see the Jobs table update live on the left!",
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
    
    # Modern Navigation
    nav_selection = st.radio(
        "Navigation Menu",
        [
            "📋 Work: Jobs",
            "📁 Work: Projects",
            "💰 Work: Billables",
            "🏠 Home (Quick Links)",
            "⏳ Reports: Overdue & Extensions",
            "🔄 Operations: Handover SOP",
            "📂 Settings: Bulk CSV Sync"
        ],
        index=0,  # DEFAULT TO JOBS VIEW
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Assistant Toggle
    st.markdown("##### **🤖 AI Co-Pilot**")
    assistant_toggle = st.toggle("Show Everest AI Assistant", value=st.session_state["show_assistant"])
    st.session_state["show_assistant"] = assistant_toggle
    
    st.markdown("---")
    
    # Live Database Metrics
    db_status = get_database_status()
    if db_status["connected"]:
        st.caption("🟢 **Everest Database Connected**")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Projects", db_status["projects"])
            st.metric("Active Jobs", "2,610")
        with m2:
            st.metric("Staff", db_status["employees"])
            st.metric("Collected", "$235M+")
            
    # Bottom Profile (Matching user's screenshot media_1789706458175.png)
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
        st.toast("✅ Ganesh's 3 demo jobs reset to initial state!")
        st.rerun()

# ----------------- MAIN EVEREST ERP CONTENT -----------------
def render_erp_content():
    # 1. JOBS DIRECTORY VIEW (DEFAULT)
    if "Jobs" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Jobs</span></div>", unsafe_allow_html=True)
        st.markdown("### **Jobs**")
        
        # User-friendly banner explaining the live demo
        st.info("💡 **Live Handover Verification:** The 3 highlighted rows below belong to **Ganesh Thamangalath**. "
                "Use the AI Assistant on the right (or 1-click handover) to reassign them to colleagues, and watch the **'JC'** column update right here in real time!")
        
        # Top toolbar
        c_search, c_status, c_filter = st.columns([3.5, 1.5, 1])
        with c_search:
            search_job = st.text_input("Search jobs...", placeholder="🔍 Search job title, project, or coordinator...", label_visibility="collapsed", key="s_job")
        with c_status:
            status_job = st.selectbox("Status", ["All", "In Progress", "Completed", "In Review"], label_visibility="collapsed", key="st_job")
        with c_filter:
            st.button("⚙️ Filters", use_container_width=True)
            
        df_jobs = get_everest_jobs_view(search=search_job, status=status_job, limit=25)
        # Render authentic Everest table!
        st.markdown(ur.render_jobs_table(df_jobs), unsafe_allow_html=True)

    # 2. PROJECTS DIRECTORY VIEW
    elif "Projects" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Projects</span></div>", unsafe_allow_html=True)
        st.markdown("### **Projects**")
        
        c_search, c_status, c_add = st.columns([3, 1.5, 1.2])
        with c_search:
            search_proj = st.text_input("Search projects...", placeholder="🔍 Search project name or client...", label_visibility="collapsed", key="s_proj")
        with c_status:
            status_proj = st.selectbox("Status", ["All", "Active", "Archived"], label_visibility="collapsed", key="st_proj")
        with c_add:
            st.button("➕ Project", type="primary", use_container_width=True)
            
        df_proj = get_everest_projects_view(search=search_proj, status=status_proj, limit=25)
        # Render authentic Everest table!
        st.markdown(ur.render_projects_table(df_proj), unsafe_allow_html=True)

    # 3. BILLABLES VIEW
    elif "Billables" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Billables</span></div>", unsafe_allow_html=True)
        st.markdown("### **Billables**")
        
        c_search, c_status = st.columns([3.5, 1.5])
        with c_search:
            search_bill = st.text_input("Search billables...", placeholder="🔍 Search billable item or project...", label_visibility="collapsed", key="s_bill")
        with c_status:
            status_bill = st.selectbox("Status", ["All", "collected", "billed", "contracted"], label_visibility="collapsed", key="st_bill")
            
        df_bill = get_everest_billables_view(search=search_bill, status=status_bill, limit=25)
        # Render authentic Everest table!
        st.markdown(ur.render_billables_table(df_bill), unsafe_allow_html=True)

    # 4. HOME (QUICK LINKS) VIEW
    elif "Home" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Home</div>", unsafe_allow_html=True)
        st.markdown("### **Quick Links**")
        # Render authentic 4-column Quick Links grid!
        st.markdown(ur.render_quick_links_grid(), unsafe_allow_html=True)

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
        df_ext = get_everest_overdue_extensions_view(search=search_ext, limit=25)
        # Render authentic Everest table!
        st.markdown(ur.render_overdue_table(df_ext), unsafe_allow_html=True)

    # 6. OPERATIONS: HANDOVER SOP
    elif "Handover" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Operations > <span class='breadcrumb-current'>Handover SOP Matrix</span></div>", unsafe_allow_html=True)
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

    # 7. BULK CSV SYNC
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
    <div class="chatbot-card">
        <div class="chatbot-header">
            <div class="chatbot-title">
                <span>🏔️</span> Everest AI Assistant
            </div>
            <div class="online-badge">● Online</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.caption("Ask questions, audit employees, or trigger live handovers:")
    
    # 1-Click Action Buttons for Non-Technical Users
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
    
    # Message History Container
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
    # 70% Authentic Everest ERP | 30% AI Copilot
    col_main_erp, col_side_bot = st.columns([70, 30], gap="large")
    with col_main_erp:
        render_erp_content()
    with col_side_bot:
        render_ai_chatbot()
else:
    # 100% Full Width ERP View
    render_erp_content()
