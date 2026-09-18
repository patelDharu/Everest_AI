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

# ----------------- AUTHENTIC 7SPAN EVEREST STYLING -----------------
st.markdown("""
<style>
    /* Global font & background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Header Bar */
    .everest-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background-color: #ffffff;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 16px;
    }
    
    .breadcrumb-nav {
        color: #64748b;
        font-size: 0.88rem;
        font-weight: 500;
        margin-bottom: 8px;
    }
    .breadcrumb-active {
        color: #0f172a;
        font-weight: 600;
    }
    
    /* 7Span Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    
    .company-badge {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 4px;
        margin-bottom: 18px;
    }
    .company-logo {
        width: 38px;
        height: 38px;
        background-color: #E22D2D;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 800;
        font-size: 1.2rem;
    }
    .company-name {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .company-sub {
        font-size: 0.76rem;
        color: #64748b;
    }
    
    /* User Profile Footer in Sidebar */
    .user-profile-pill {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        margin-top: 25px;
    }
    .user-avatar {
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
    
    /* Quick Links Grid Card */
    .quick-link-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 16px;
        display: flex;
        align-items: center;
        gap: 14px;
        transition: all 0.15s ease-in-out;
        text-decoration: none !important;
        margin-bottom: 12px;
    }
    .quick-link-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        transform: translateY(-1px);
    }
    .quick-icon {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        background-color: #fee2e2;
        color: #E22D2D;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        flex-shrink: 0;
    }
    .quick-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 2px;
    }
    .quick-desc {
        font-size: 0.78rem;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE INITIALIZATION -----------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "### 🏔️ Welcome to Everest AI Operations Co-Pilot\n\n"
                       "I am connected to 7Span's Everest ERP production database.\n\n"
                       "**Try these instant actions:**\n"
                       "* Type: *'Ganesh is leaving, what jobs does he have?'*\n"
                       "* Type: *'Assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, job 3 to Dhruv Nayak'*\n"
                       "* Watch the **Jobs & Projects Table on the left update in real-time**!",
            "data": None
        }
    ]

if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Split View (ERP + Side Assistant)"

# ----------------- SIDEBAR NAVIGATION (EVEREST ERP CLONE) -----------------
with st.sidebar:
    # 7Span Branding
    st.markdown("""
    <div class="company-badge">
        <div class="company-logo">7</div>
        <div>
            <div class="company-name">7Span</div>
            <div class="company-sub">7Span Internet Pvt. Ltd.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("##### **Navigation**")
    
    # Navigation Radio matching screenshots
    nav_selection = st.radio(
        "Navigation",
        [
            "🏠 Home (Quick Links)",
            "📁 Work: Projects",
            "📋 Work: Jobs",
            "💰 Work: Billables",
            "⏳ Reports: Overdue & Extensions",
            "🔄 Operations: Handover Assistant",
            "📂 Settings: Bulk CSV Ingestion"
        ],
        index=2, # Default to Jobs to show live instant updates
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Layout Split-Screen Mode Controller
    st.markdown("##### **🖥️ View Layout**")
    layout_mode = st.selectbox(
        "Layout Mode:",
        ["Split View (ERP + Side Assistant)", "Full-Width Everest ERP", "Full-Width AI Assistant"],
        index=0,
        label_visibility="collapsed"
    )
    st.session_state["view_mode"] = layout_mode
    
    st.markdown("---")
    
    # Live Database Connection Metric
    db_status = get_database_status()
    if db_status["connected"]:
        st.caption(f"🟢 **Database Connected** (Mode: {db_status['mode']})")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Projects", db_status["projects"])
            st.metric("Jobs", "2,610")
        with m2:
            st.metric("Staff", db_status["employees"])
            st.metric("Collected", "$235M+")
    
    st.markdown("---")
    
    # Logged-in Employee Profile (Matching screenshot #media_1789706458175.png)
    st.markdown("""
    <div class="user-profile-pill">
        <div class="user-avatar">GT</div>
        <div style="flex-grow:1; min-width:0;">
            <div style="font-weight:600; font-size:0.86rem; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Ganesh Thamangalath</div>
            <div style="font-size:0.75rem; color:#64748b;">ganesh.t@7span.com • PM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Reset Demo Jobs for Ganesh", use_container_width=True):
        reset_demo_handover_data()
        st.success("✅ Demo jobs reset! Ganesh has 3 active jobs ready for handover.")
        st.rerun()

# ----------------- MAIN LAYOUT RENDERING -----------------

# Helper function to render the Everest ERP View
def render_everest_portal():
    current_page = nav_selection
    
    # 1. HOME VIEW (Matching screenshot #media_1789708497073.png)
    if "Home" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Home</div>", unsafe_allow_html=True)
        st.markdown("### **Quick Links**")
        
        # Grid of Quick Links matching user's screenshot
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            st.markdown("""
            <div class="quick-link-card">
                <div class="quick-icon">📢</div>
                <div>
                    <div class="quick-title">What's New</div>
                    <div class="quick-desc">Check latest company updates</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">📋</div>
                <div>
                    <div class="quick-title">Manpower Requisition</div>
                    <div class="quick-desc">Hiring & headcount forms</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">💬</div>
                <div>
                    <div class="quick-title">Discord</div>
                    <div class="quick-desc">Team chat and calls</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with q2:
            st.markdown("""
            <div class="quick-link-card">
                <div class="quick-icon">📚</div>
                <div>
                    <div class="quick-title">Documentation</div>
                    <div class="quick-desc">Engineering & process guides</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">🛡️</div>
                <div>
                    <div class="quick-title">Company Policies</div>
                    <div class="quick-desc">Leave, handover & SOPs</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">🎨</div>
                <div>
                    <div class="quick-title">Draw.io</div>
                    <div class="quick-desc">Architecture diagrams</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with q3:
            st.markdown("""
            <div class="quick-link-card">
                <div class="quick-icon">🔍</div>
                <div>
                    <div class="quick-title">Case Study Finder</div>
                    <div class="quick-desc">Client success stories</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">🌊</div>
                <div>
                    <div class="quick-title">Pacific</div>
                    <div class="quick-desc">Find company info</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">🐙</div>
                <div>
                    <div class="quick-title">GitHub</div>
                    <div class="quick-desc">Code repositories</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with q4:
            st.markdown("""
            <div class="quick-link-card">
                <div class="quick-icon">✍️</div>
                <div>
                    <div class="quick-title">Feedback & Support</div>
                    <div class="quick-desc">Anonymous internal feedback</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">🏜️</div>
                <div>
                    <div class="quick-title">Sahara</div>
                    <div class="quick-desc">Project management tool</div>
                </div>
            </div>
            <div class="quick-link-card">
                <div class="quick-icon">⏰</div>
                <div>
                    <div class="quick-title">Keka</div>
                    <div class="quick-desc">Attendance & payroll</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### **📊 Live ERP Operational Status**")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Active Projects", "544", "+12 this quarter")
        with k2:
            st.metric("Active In-Progress Jobs", "2,610", "All pods tracked")
        with k3:
            st.metric("Total Collected Revenue", "$235.4M USD", "2,698 Invoices")
        with k4:
            st.metric("Recorded Extensions", "323 Milestones", "Justifications logged")

    # 2. PROJECTS VIEW (Matching screenshot #media_1789708497100.png)
    elif "Projects" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Work > <span class='breadcrumb-active'>Projects</span></div>", unsafe_allow_html=True)
        st.markdown("### **Projects**")
        
        # Toolbar
        t1, t2, t3 = st.columns([3, 1.5, 1])
        with t1:
            search_p = st.text_input("Search projects...", placeholder="Filter by project or client...", key="search_proj_input", label_visibility="collapsed")
        with t2:
            status_p = st.selectbox("Status", ["All", "Active", "Archived"], key="status_proj_select", label_visibility="collapsed")
        with t3:
            st.button("➕ Project", type="primary", use_container_width=True)
            
        df_p = get_everest_projects_view(search=search_p, status=status_p, limit=30)
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        st.caption(f"Showing top {len(df_p)} active projects from Everest ERP database.")

    # 3. JOBS VIEW (Matching screenshot #media_1789708516090.png)
    elif "Jobs" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Work > <span class='breadcrumb-active'>Jobs</span></div>", unsafe_allow_html=True)
        st.markdown("### **Jobs**")
        
        # Live Notification Banner highlighting Ganesh's jobs
        st.info("💡 **Live Verification View:** Ganesh Thamangalath's jobs are pinned at the top. When you prompt the AI Assistant to reassign jobs, you will see the **'JC (Job Coordinator)'** column update right here!")
        
        # Toolbar
        t1, t2 = st.columns([3.5, 1.5])
        with t1:
            search_j = st.text_input("Search jobs...", placeholder="Filter by job name, project, or coordinator...", key="search_job_input", label_visibility="collapsed")
        with t2:
            status_j = st.selectbox("Status", ["All", "In Progress", "Completed", "In Review"], key="status_job_select", label_visibility="collapsed")
            
        df_j = get_everest_jobs_view(search=search_j, status=status_j, limit=30)
        st.dataframe(df_j, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_j)} active jobs. JC assignments reflect live SQLite database state.")

    # 4. BILLABLES VIEW (Matching screenshot #media_1789708516099.png)
    elif "Billables" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Work > <span class='breadcrumb-active'>Billables</span></div>", unsafe_allow_html=True)
        st.markdown("### **Billables**")
        
        t1, t2 = st.columns([3.5, 1.5])
        with t1:
            search_b = st.text_input("Search billables...", placeholder="Search milestones or projects...", key="search_bill_input", label_visibility="collapsed")
        with t2:
            status_b = st.selectbox("Status", ["All", "collected", "billed", "contracted"], key="status_bill_select", label_visibility="collapsed")
            
        df_b = get_everest_billables_view(search=search_b, status=status_b, limit=30)
        st.dataframe(df_b, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df_b)} billable records with coordinator governance.")

    # 5. OVERDUE & EXTENSIONS VIEW (Matching screenshot #media_1789708547862.png)
    elif "Overdue" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Reports > Billables > <span class='breadcrumb-active'>Overdue & Extensions</span></div>", unsafe_allow_html=True)
        st.markdown("### **Overdue & Extended Billables**")
        
        search_ext = st.text_input("Search extension justifications...", placeholder="Search reasons or projects...", key="search_ext_input")
        df_ext = get_everest_overdue_extensions_view(search=search_ext, limit=30)
        st.dataframe(df_ext, use_container_width=True, hide_index=True)
        st.caption(f"Displaying {len(df_ext)} recorded billable extensions with client and engineering justifications.")

    # 6. HANDOVER ASSISTANT VIEW (Interactive UI)
    elif "Handover" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Operations > <span class='breadcrumb-active'>Employee Exit Handover SOP</span></div>", unsafe_allow_html=True)
        st.markdown("### **Employee Exit / Layoff Handover Assistant**")
        
        employees = get_all_employees()
        emp_options = {f"{e['name']} ({e['role']} • {e['grade']})": e["id"] for e in employees}
        
        default_idx = 0
        for i, k in enumerate(emp_options.keys()):
            if "Ganesh Thamangalath" in k:
                default_idx = i
                break
                
        selected_from_label = st.selectbox("1. Select Exiting / Departing Employee:", list(emp_options.keys()), index=default_idx, key="select_exit_emp_main")
        from_id = emp_options[selected_from_label]
        
        audit_data = audit_employee_responsibilities(from_id)
        granular_items = get_employee_granular_roles(from_id)
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Projects (as PC/AM/SC)", len(audit_data["projects_as_coordinator"]))
        with m2:
            st.metric("Active Jobs (as JC)", len(audit_data["jobs_as_jc"]))
        with m3:
            st.metric("Job Allocations", len(audit_data["allocated_jobs"]))
        with m4:
            st.metric("Total Open Roles", audit_data["total_responsibilities"])
            
        if audit_data["total_responsibilities"] > 0:
            handover_mode = st.radio(
                "Handover Workflow:",
                [
                    "🎯 Granular Multi-Recipient Handover (Assign different jobs to different people)",
                    "⚡ Bulk Handover (Reassign all roles to one person)"
                ],
                horizontal=True
            )
            
            successor_options = {k: v for k, v in emp_options.items() if v != from_id}
            successor_list = list(successor_options.keys())
            
            if "Granular" in handover_mode:
                st.markdown("""
                <div style='background-color: #f1f5f9; padding: 12px; border-radius: 8px; margin-bottom: 14px; font-size: 0.92rem;'>
                    <b>Granular Assignment Matrix:</b> Choose an individual successor for each specific project or job below. 
                    For example, assign Job 1 to Jay Patel, Job 2 to Bhavik Vachhani, Job 3 to Dhruv Nayak.
                </div>
                """, unsafe_allow_html=True)
                
                selections = {}
                for idx, item in enumerate(granular_items, 1):
                    col_item, col_succ = st.columns([3, 2])
                    with col_item:
                        st.markdown(f"**{idx}. {item['name']}**  \n`Role:` {item['role_title']} | `Project:` {item['project_name']}")
                    with col_succ:
                        chosen_succ = st.selectbox(
                            f"Assign To:",
                            ["-- Keep Current / Skip --"] + successor_list,
                            key=f"gran_main_{item['category']}_{item['id']}_{idx}"
                        )
                        if chosen_succ != "-- Keep Current / Skip --":
                            selections[idx - 1] = successor_options[chosen_succ]
                    st.divider()
                    
                if st.button("🚀 Apply Granular Reassignments in Database", type="primary", use_container_width=True):
                    if not selections:
                        st.warning("Please select at least one colleague to reassign.")
                    else:
                        updated_count = 0
                        for item_idx, target_emp_id in selections.items():
                            it = granular_items[item_idx]
                            c = reassign_specific_entity(it["category"], it["type"], it["id"], target_emp_id, from_id)
                            updated_count += c
                        st.success(f"✅ Handover Completed! Reassigned {len(selections)} responsibilities in the Everest database.")
                        st.rerun()
            else:
                selected_to_label = st.selectbox("Select Single Replacement Colleague:", successor_list, key="bulk_to_select")
                to_id = successor_options[selected_to_label]
                if st.button("🚀 Execute Safe Bulk Handover in Database", type="primary", use_container_width=True):
                    res = reassign_employee_roles(from_id, to_id, "all")
                    st.success(f"✅ Handover Completed! {res['summary']}")
                    st.rerun()
        else:
            st.success("✅ This employee has 0 remaining active responsibilities in the Everest database.")

    # 7. BULK CSV INGESTION
    elif "Settings" in current_page:
        st.markdown("<div class='breadcrumb-nav'>Settings > <span class='breadcrumb-active'>Bulk CSV Sync</span></div>", unsafe_allow_html=True)
        st.markdown("### **Upload & Sync Everest CSV Files (30+ Files Supported)**")
        
        uploaded_files = st.file_uploader(
            "Select or drop 30+ CSV files at once from your computer:",
            type=["csv"],
            accept_multiple_files=True,
            key="bulk_csv_uploader_main"
        )
        if uploaded_files:
            st.info(f"Selected **{len(uploaded_files)} CSV files**. Ready to ingest into Everest Database.")
            if st.button(f"⚡ Ingest & Sync {len(uploaded_files)} Files Now", type="primary"):
                progress_bar = st.progress(0)
                status_list = []
                save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "csvs")
                os.makedirs(save_dir, exist_ok=True)
                for idx, uf in enumerate(uploaded_files):
                    file_path = os.path.join(save_dir, uf.name)
                    with open(file_path, "wb") as f_out:
                        f_out.write(uf.getvalue())
                    res = csv_importer.import_single_csv(uf, uf.name)
                    status_list.append(res)
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                st.success(f"✅ Ingested {len(uploaded_files)} CSV files into Everest Database!")
                st.dataframe(pd.DataFrame(status_list)[["file_name", "table_name", "rows", "status"]], use_container_width=True)
                st.rerun()


# Helper function to render the AI Assistant
def render_ai_copilot():
    st.markdown("""
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #e2e8f0;">
        <div style="font-weight:700; font-size:1.1rem; color:#E22D2D;">🏔️ Everest AI Co-Pilot</div>
        <span style="font-size:0.75rem; background:#fee2e2; color:#991B1B; padding:2px 8px; border-radius:12px; font-weight:600;">LIVE CONNECTED</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("Ask operations questions or command role transfers:")
    
    # 1-Click Action Buttons for Instant Verification
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⚡ Reassign Ganesh (Jay, Bhavik, Dhruv)", use_container_width=True):
            user_prompt = "Ganesh is JC, assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, and job 3 to Dhruv Nayak"
            st.session_state["messages"].append({"role": "user", "content": user_prompt, "data": None})
            result = analyze_question(user_prompt)
            st.session_state["messages"].append({"role": "assistant", "content": result["answer"], "data": result})
            st.rerun()
            
    with c2:
        if st.button("🔄 Reset Demo Jobs (Ganesh)", use_container_width=True):
            reset_demo_handover_data()
            st.session_state["messages"].append({
                "role": "assistant",
                "content": "### [RESET COMPLETED]\n\nGanesh Thamangalath's 3 active jobs have been reset in the Everest database:\n* **Job 1: Mobile UI Design & Prototype**\n* **Job 2: Backend API Architecture & DB Sync**\n* **Job 3: Security Audit & Cloud Compliance**\n\nReady for another live handover test!",
                "data": None
            })
            st.rerun()
            
    c3, c4 = st.columns(2)
    with c3:
        if st.button("🔍 Ganesh's Active Jobs", use_container_width=True):
            user_prompt = "Ganesh is leaving, what jobs does he have?"
            st.session_state["messages"].append({"role": "user", "content": user_prompt, "data": None})
            result = analyze_question(user_prompt)
            st.session_state["messages"].append({"role": "assistant", "content": result["answer"], "data": result})
            st.rerun()
            
    with c4:
        if st.button("💰 2026 Collected Revenue", use_container_width=True):
            user_prompt = "How much collected revenue in 2026?"
            st.session_state["messages"].append({"role": "user", "content": user_prompt, "data": None})
            result = analyze_question(user_prompt)
            st.session_state["messages"].append({"role": "assistant", "content": result["answer"], "data": result})
            st.rerun()

    st.markdown("---")

    # Render Chat History Container
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if msg.get("data") and msg["data"].get("df") is not None and not msg["data"]["df"].empty:
                    with st.expander("📊 View Data Details (Optional)", expanded=msg["data"].get("show_table_open", False)):
                        st.dataframe(msg["data"]["df"], use_container_width=True)

    # Chat Input
    prompt_input = st.chat_input("Command role transfer or ask ERP questions...")
    if prompt_input:
        st.session_state["messages"].append({"role": "user", "content": prompt_input, "data": None})
        with st.spinner("Executing Everest AI operations..."):
            res = analyze_question(prompt_input)
        st.session_state["messages"].append({"role": "assistant", "content": res["answer"], "data": res})
        st.rerun()


# ----------------- VIEW DISPATCHER -----------------
current_view_mode = st.session_state.get("view_mode", "Split View (ERP + Side Assistant)")

if current_view_mode == "Split View (ERP + Side Assistant)":
    col_erp, col_ai = st.columns([65, 35], gap="large")
    with col_erp:
        render_everest_portal()
    with col_ai:
        render_ai_copilot()

elif current_view_mode == "Full-Width Everest ERP":
    render_everest_portal()

elif current_view_mode == "Full-Width AI Assistant":
    st.markdown("## 🏔️ **Everest AI Operations Assistant**")
    render_ai_copilot()
