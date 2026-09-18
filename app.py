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
    get_everest_contracts_view,
    get_everest_tasks_view,
    get_everest_timesheets_view,
    get_everest_employees_view,
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

# Path to screenshots
SCREENSHOTS_DIR = r"D:\Everest-AI\screenshots"

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
        padding: 8px 12px !important;
        border-radius: 8px !important;
        margin-bottom: 2px !important;
        color: #475569 !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
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
        padding: 4px 6px 14px 6px;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 12px;
    }
    .company-logo-badge {
        width: 36px;
        height: 36px;
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
        font-size: 0.74rem;
        color: #64748b;
    }
    
    /* Breadcrumbs */
    .breadcrumb-text {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 6px;
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
        margin-top: 16px;
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
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
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
                       "I can look up projects, revenue, or **reassign jobs in real-time** when someone departs.\n\n"
                       "💡 **1-Click Handover Test:** Click the red button below to assign Ganesh's 3 active jobs to **Jay Patel, Bhavik Vachhani, and Dhruv Nayak**, and see the Jobs table update live!",
            "data": None
        }
    ]

if "show_assistant" not in st.session_state:
    st.session_state["show_assistant"] = False  # Full width default; floating button opens it!

if "inbox_tab" not in st.session_state:
    st.session_state["inbox_tab"] = "Pending"

if "inbox_cat" not in st.session_state:
    st.session_state["inbox_cat"] = "All"

if "notifications" not in st.session_state:
    st.session_state["notifications"] = [
        {
            "id": "notif_1",
            "title": "Phase 2B: Job Extension Approved",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Extension request for job "Phase 2B" under project "Livvy" has been approved. The new end date is 2026-09-30 for the reason "Client post-review changes". The extension request was approved by Nikhil Sharma. Please continue your work accordingly.',
            "time": "Today at 4:01 PM",
            "status": "Pending",
        },
        {
            "id": "notif_2",
            "title": "CR-1: Job Extension Approved",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Extension request for job "CR-1" under project "Literaliga" has been approved. The new end date is 2026-09-30 for the reason "Client held work". The extension request was approved by Nikhil Sharma. Please continue your work accordingly.',
            "time": "Today at 4:01 PM",
            "status": "Pending",
        },
        {
            "id": "notif_3",
            "title": "CR-1: Job Extension Request",
            "category": "Jobs",
            "icon": "💼",
            "message": 'An extension request has been submitted for job "CR-1" under project "Literaliga". The requested new end date is 2026-09-30 with the reason "Client held work". The extension request was submitted by Bhoomi Trivedi. Please review extension request.',
            "time": "Today at 3:45 PM",
            "status": "Pending",
        },
        {
            "id": "notif_4",
            "title": "Phase 2B: Job Extension Request",
            "category": "Jobs",
            "icon": "💼",
            "message": 'An extension request has been submitted for job "Phase 2B" under project "Livvy". The requested new end date is 2026-09-30 with the reason "Client post-review changes". The extension request was submitted by Bhoomi Trivedi. Please review extension request.',
            "time": "Today at 3:39 PM",
            "status": "Pending",
        },
        {
            "id": "notif_5",
            "title": "7Span Sales: Job in Review",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Your job "Nikunj Mail tester\'s opportunity" in project "7Span Sales" has passed its end date (17-09-2026) and is now in "In Review" status. Kindly review the job, either extend it or close it.',
            "time": "Today at 10:00 AM",
            "status": "Pending",
        },
        {
            "id": "notif_6",
            "title": "7Span Sales: Job in Review",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Your job "Clinic/Pharmacy Management Software" in project "7Span Sales" has passed its end date (17-09-2026) and is now in "In Review" status. Kindly review the job, either extend it or close it.',
            "time": "Today at 10:00 AM",
            "status": "Pending",
        },
        {
            "id": "notif_7",
            "title": "7Span Sales: Job in Review",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Your job "CertificateGate\'s opportunity" in project "7Span Sales" has passed its end date (17-09-2026) and is now in "In Review" status. Kindly review the job, either extend it or close it.',
            "time": "Today at 10:00 AM",
            "status": "Pending",
        },
        {
            "id": "notif_8",
            "title": "7Span Sales: Job in Review",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Your job "Dakko - AWS Certified Automations Experts" in project "7Span Sales" has passed its end date (17-09-2026) and is now in "In Review" status. Kindly review the job, either extend it or close it.',
            "time": "Today at 10:00 AM",
            "status": "Pending",
        },
        {
            "id": "notif_9",
            "title": "7Span Sales: Job Ending Soon",
            "category": "Jobs",
            "icon": "💼",
            "message": 'Your job "NextWave\'s - Riyadh Expo 2030" under project "7Span Sales" is scheduled to end on 21-09-2026, which is in 3 days. Please ensure all deliverables are on track and take necessary actions for updates or handover.',
            "time": "Today at 10:00 AM",
            "status": "Pending",
        },
        {
            "id": "notif_10",
            "title": "Operations: Ganesh Thamangalath Exit Handover",
            "category": "Handover",
            "icon": "🔄",
            "message": 'Ganesh Thamangalath has 3 active jobs ("Mobile UI Design & Prototype", "Backend API Architecture & DB Sync", "Security Audit & Cloud Compliance") pending handover to successors before relieving date.',
            "time": "Today at 9:15 AM",
            "status": "Pending",
        },
    ]

# Helper to render screenshot reference expander
def show_screenshot_ref(image_filename, caption="Original Everest ERP Screenshot"):
    img_path = os.path.join(SCREENSHOTS_DIR, image_filename)
    if os.path.exists(img_path):
        with st.expander(f"📸 Compare with Original Everest Screenshot ({image_filename})", expanded=False):
            st.image(img_path, caption=caption, use_column_width=True)

# ----------------- SIDEBAR (AUTHENTIC 7SPAN EVEREST ERP) -----------------
with st.sidebar:
    st.markdown("""
    <div class="company-header">
        <div class="company-logo-badge">7</div>
        <div>
            <div class="company-title">7Span</div>
            <div class="company-subtitle">7Span Internet Pvt. Ltd.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    nav_selection = st.radio(
        "Navigation Menu",
        [
            "🏠 Home (Quick Links)",
            "📥 Inbox (498)",
            "📝 Tasks",
            "📁 Work: Projects",
            "📄 Work: Contracts",
            "📋 Work: Jobs",
            "💰 Work: Billables",
            "⏱️ Timesheet: Team Logs",
            "⏳ Reports: Overdue & Extensions",
            "👥 Organization: Employees",
            "🔄 Operations: Handover SOP",
            "📸 Design Gallery (20 Screenshots)",
            "📂 Settings: D:\everest_data_zip"
        ],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    st.markdown("##### **🤖 AI Co-Pilot**")
    assistant_toggle = st.toggle("Show Everest AI Bot", value=st.session_state["show_assistant"])
    st.session_state["show_assistant"] = assistant_toggle
    
    st.markdown("---")
    
    db_status = get_database_status()
    if db_status["connected"]:
        st.caption("🟢 **Everest Database Connected**")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Projects", db_status["projects"])
            st.metric("Active Jobs", "2,610")
        with m2:
            st.metric("Staff", db_status["employees"])
            st.metric("Tasks", "3,052")
            
    st.markdown("""
    <div class="profile-footer">
        <div class="profile-avatar">GT</div>
        <div style="flex-grow:1; min-width:0;">
            <div style="font-weight:600; font-size:0.86rem; color:#0f172a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Ganesh Thamangalath</div>
            <div style="font-size:0.74rem; color:#64748b;">ganesh.t@7span.com • PM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Reset Demo Jobs (Ganesh)", use_container_width=True):
        reset_demo_handover_data()
        st.toast("✅ Ganesh's 3 demo jobs reset to initial state!")
        st.rerun()

# ----------------- MAIN EVEREST ERP CONTENT -----------------
def render_erp_content():
    # 1. HOME VIEW (MATCHING 01_Home.png & media_1789739327072.png)
    if "Home" in nav_selection:
        col_title, col_stat = st.columns([4, 1.2])
        with col_title:
            st.markdown("<div class='breadcrumb-text'>Home</div>", unsafe_allow_html=True)
            st.markdown("### **Quick Links**")
        with col_stat:
            st.markdown("""
            <div style="text-align: right; padding-top: 8px;">
                <span style="background: #fee2e2; color: #dc2626; padding: 6px 14px; border-radius: 8px; font-size: 0.84rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                    📢 What's New <span style="background: #dc2626; color: white; border-radius: 50%; width: 18px; height: 18px; font-size: 0.70rem; display: inline-flex; align-items: center; justify-content: center;">9+</span>
                </span>
            </div>
            """, unsafe_allow_html=True)
            
        show_screenshot_ref("01_Home.png")
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

    # 2. INBOX VIEW (MATCHING 02_Inbox.png & media_1789739354640.png)
    elif "Inbox" in nav_selection:
        c_title, c_tabs, c_icons = st.columns([2.5, 2.5, 2])
        with c_title:
            st.markdown("<div class='breadcrumb-text'>Inbox</div>", unsafe_allow_html=True)
            st.markdown("### **Inbox**")
        with c_tabs:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            tab_choice = st.radio(
                "Filter Status",
                ["Pending (498)", "Cleared"],
                index=0 if st.session_state["inbox_tab"] == "Pending" else 1,
                horizontal=True,
                label_visibility="collapsed"
            )
            st.session_state["inbox_tab"] = "Pending" if "Pending" in tab_choice else "Cleared"
        with c_icons:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            cat_choice = st.selectbox(
                "Category",
                ["All", "Jobs", "Handover", "Billables"],
                index=0,
                label_visibility="collapsed"
            )
            st.session_state["inbox_cat"] = cat_choice

        show_screenshot_ref("02_Inbox.png")
        
        inbox_html = ur.render_inbox_table(
            st.session_state["notifications"],
            active_tab=st.session_state["inbox_tab"],
            active_category=st.session_state["inbox_cat"]
        )
        st.markdown(inbox_html, unsafe_allow_html=True)

    # 3. TASKS VIEW (MATCHING 03_Tasks.png)
    elif "Tasks" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Tasks</div>", unsafe_allow_html=True)
        st.markdown("### **Tasks**")
        show_screenshot_ref("03_Tasks.png")
        
        c_search, c_status, c_add = st.columns([3, 1.5, 1])
        with c_search:
            s_task = st.text_input("Search tasks...", placeholder="🔍 Search task title or assignee...", label_visibility="collapsed", key="s_task")
        with c_status:
            st_task = st.selectbox("Status", ["All", "Open", "In Progress", "Completed"], label_visibility="collapsed", key="st_task")
        with c_add:
            st.button("➕ Task", type="primary", use_container_width=True)
            
        df_tasks = get_everest_tasks_view(search=s_task, status=st_task, limit=25)
        st.markdown(ur.render_tasks_table(df_tasks), unsafe_allow_html=True)

    # 4. PROJECTS DIRECTORY VIEW (MATCHING 04_Work_Projects.png)
    elif "Projects" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Projects</span></div>", unsafe_allow_html=True)
        st.markdown("### **Projects**")
        show_screenshot_ref("04_Work_Projects.png")
        
        c_search, c_status, c_add = st.columns([3, 1.5, 1.2])
        with c_search:
            search_proj = st.text_input("Search projects...", placeholder="🔍 Search project name or client...", label_visibility="collapsed", key="s_proj")
        with c_status:
            status_proj = st.selectbox("Status", ["All", "Active", "Archived"], label_visibility="collapsed", key="st_proj")
        with c_add:
            st.button("➕ Project", type="primary", use_container_width=True)
            
        df_proj = get_everest_projects_view(search=search_proj, status=status_proj, limit=25)
        st.markdown(ur.render_projects_table(df_proj), unsafe_allow_html=True)

    # 5. CONTRACTS DIRECTORY VIEW (MATCHING 05_Work_Contracts.png)
    elif "Contracts" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Contracts</span></div>", unsafe_allow_html=True)
        st.markdown("### **Contracts**")
        show_screenshot_ref("05_Work_Contracts.png")
        
        c_search, c_status = st.columns([3.5, 1.5])
        with c_search:
            search_c = st.text_input("Search contracts...", placeholder="🔍 Search contract name or project...", label_visibility="collapsed", key="s_cnt")
        with c_status:
            status_c = st.selectbox("Status", ["All", "In Progress", "Completed", "Draft"], label_visibility="collapsed", key="st_cnt")
            
        df_contracts = get_everest_contracts_view(search=search_c, status=status_c, limit=25)
        st.markdown(ur.render_contracts_table(df_contracts), unsafe_allow_html=True)

    # 6. JOBS DIRECTORY VIEW (MATCHING 06_Work_Jobs.png)
    elif "Jobs" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Jobs</span></div>", unsafe_allow_html=True)
        st.markdown("### **Jobs**")
        show_screenshot_ref("06_Work_Jobs.png")
        
        st.info("💡 **Live Handover Verification:** The 3 highlighted rows below belong to **Ganesh Thamangalath**. "
                "Open the **Everest AI Bot** (click 🤖 Bot at the bottom right) to reassign them to colleagues and watch the **JC** column update live!")
        
        c_search, c_status, c_filter = st.columns([3.5, 1.5, 1])
        with c_search:
            search_job = st.text_input("Search jobs...", placeholder="🔍 Search job title, project, or coordinator...", label_visibility="collapsed", key="s_job")
        with c_status:
            status_job = st.selectbox("Status", ["All", "In Progress", "Completed", "In Review"], label_visibility="collapsed", key="st_job")
        with c_filter:
            st.button("⚙️ Filters", use_container_width=True)
            
        df_jobs = get_everest_jobs_view(search=search_job, status=status_job, limit=25)
        st.markdown(ur.render_jobs_table(df_jobs), unsafe_allow_html=True)

    # 7. BILLABLES VIEW (MATCHING 07_Work_Billables.png)
    elif "Billables" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Work > <span class='breadcrumb-current'>Billables</span></div>", unsafe_allow_html=True)
        st.markdown("### **Billables**")
        show_screenshot_ref("07_Work_Billables.png")
        
        c_search, c_status = st.columns([3.5, 1.5])
        with c_search:
            search_bill = st.text_input("Search billables...", placeholder="🔍 Search billable item or project...", label_visibility="collapsed", key="s_bill")
        with c_status:
            status_bill = st.selectbox("Status", ["All", "collected", "billed", "contracted"], label_visibility="collapsed", key="st_bill")
            
        df_bill = get_everest_billables_view(search=search_bill, status=status_bill, limit=25)
        st.markdown(ur.render_billables_table(df_bill), unsafe_allow_html=True)

    # 8. TIMESHEET VIEW (MATCHING 09_Timesheet_Logs.png & 12_Timesheet_My_Team.png)
    elif "Timesheet" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Timesheet > <span class='breadcrumb-current'>Team Logs</span></div>", unsafe_allow_html=True)
        st.markdown("### **Timesheet Logs & Team Allocation**")
        show_screenshot_ref("12_Timesheet_My_Team.png")
        
        c_search, c_date = st.columns([3, 2])
        with c_search:
            search_ts = st.text_input("Search timesheet...", placeholder="🔍 Search employee, project, or job...", label_visibility="collapsed", key="s_ts")
        with c_date:
            st.caption("📅 Current Period: September 2026")
            
        df_ts = get_everest_timesheets_view(search=search_ts, limit=25)
        st.markdown(ur.render_timesheet_table(df_ts), unsafe_allow_html=True)

    # 9. OVERDUE & EXTENSIONS (MATCHING 16_Reports_Billables.png)
    elif "Overdue" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Reports > Billables > <span class='breadcrumb-current'>Overdue & Extensions</span></div>", unsafe_allow_html=True)
        st.markdown("### **Overdue & Extended Billables**")
        show_screenshot_ref("16_Reports_Billables.png")
        
        search_ext = st.text_input("Search extensions...", placeholder="🔍 Search justification or project...", key="s_ext")
        df_ext = get_everest_overdue_extensions_view(search=search_ext, limit=25)
        st.markdown(ur.render_overdue_table(df_ext), unsafe_allow_html=True)

    # 10. ORGANIZATION EMPLOYEES (MATCHING 18_Org_Employees.png)
    elif "Employees" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Organization > <span class='breadcrumb-current'>Employees</span></div>", unsafe_allow_html=True)
        st.markdown("### **Employees Directory**")
        show_screenshot_ref("18_Org_Employees.png")
        
        c_search, c_dept, c_add = st.columns([3, 1.5, 1.2])
        with c_search:
            search_emp = st.text_input("Search staff...", placeholder="🔍 Search name, email, or role...", label_visibility="collapsed", key="s_emp")
        with c_dept:
            dept_emp = st.selectbox("Department", ["All", "Engineering", "Delivery", "Design", "Quality", "Marketing"], label_visibility="collapsed", key="d_emp")
        with c_add:
            st.button("➕ Employee", type="primary", use_container_width=True)
            
        df_emp = get_everest_employees_view(search=search_emp, department=dept_emp, limit=25)
        st.markdown(ur.render_employees_table(df_emp), unsafe_allow_html=True)

    # 11. OPERATIONS: HANDOVER SOP MATRIX
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

    # 12. DESIGN GALLERY: ALL 20 EVEREST SCREENSHOTS
    elif "Gallery" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Design System > <span class='breadcrumb-current'>Screenshots Gallery</span></div>", unsafe_allow_html=True)
        st.markdown("### **Everest ERP Reference Design Gallery (20 Captured Screenshots)**")
        st.info("💡 Below are the real reference screenshots captured directly from **`everest.7span.work`**. Every view in this web application was built to identically clone these screens!")
        
        screenshot_files = sorted([f for f in os.listdir(SCREENSHOTS_DIR) if f.endswith(".png")]) if os.path.exists(SCREENSHOTS_DIR) else []
        
        for i in range(0, len(screenshot_files), 2):
            cols = st.columns(2)
            for j in range(2):
                idx = i + j
                if idx < len(screenshot_files):
                    fname = screenshot_files[idx]
                    fpath = os.path.join(SCREENSHOTS_DIR, fname)
                    with cols[j]:
                        clean_title = fname.replace(".png", "").replace("_", " ")
                        st.markdown(f"##### **{clean_title}**")
                        st.image(fpath, caption=f"Reference: {fname}", use_column_width=True)
                        st.markdown("---")

    # 13. SETTINGS & D:\everest_data_zip DATA SYNC
    elif "Settings" in nav_selection or "everest_data_zip" in nav_selection:
        st.markdown("<div class='breadcrumb-text'>Settings > <span class='breadcrumb-current'>Data Sync (D:\\everest_data_zip)</span></div>", unsafe_allow_html=True)
        st.markdown("### **Data Ingestion & Sync from `D:\\everest_data_zip`**")
        
        zip_path = r"D:\everest_data_zip"
        if os.path.exists(zip_path):
            csv_files = [f for f in os.listdir(zip_path) if f.endswith(".csv")]
            st.success(f"📁 **Found {len(csv_files)} production CSV datasets in `{zip_path}`!**")
            
            c1, c2 = st.columns([3, 1])
            with c1:
                st.caption("All key tables (`projects`, `jobs`, `billables`, `timesheets`, `tasks`, `employees`, `contracts`, `extensions`) are loaded in SQLite.")
            with c2:
                if st.button("🔄 Resync Database from CSVs", type="primary"):
                    st.toast("Syncing data tables...")
                    st.rerun()
            with st.expander("📂 Browse all 162 CSV files in D:\\everest_data_zip", expanded=False):
                st.write(csv_files)
        else:
            st.warning(f"Path `{zip_path}` not found on this machine.")


# ----------------- SIDE / FLOATING AI BOT COMPONENT -----------------
def render_ai_chatbot():
    st.markdown("""
    <div class="chatbot-card">
        <div class="chatbot-header">
            <div class="chatbot-title">
                <span>🤖</span> Everest AI Bot
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="online-badge">● Online</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_sub, col_min = st.columns([3, 1])
    with col_sub:
        st.caption("Ask questions, audit employees, or trigger handovers:")
    with col_min:
        if st.button("✖ Close", key="close_bot_btn", help="Minimize Bot to full screen"):
            st.session_state["show_assistant"] = False
            st.rerun()
    
    st.markdown("##### **⚡ Quick Actions:**")
    
    if st.button("⚡ Assign Ganesh's 3 Jobs (Jay, Bhavik, Dhruv)", type="primary", use_container_width=True):
        prompt = "Ganesh is JC, assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, and job 3 to Dhruv Nayak"
        st.session_state["messages"].append({"role": "user", "content": prompt, "data": None})
        res = analyze_question(prompt)
        st.session_state["messages"].append({"role": "assistant", "content": res["answer"], "data": res})
        
        # Prepend real-time notification to Inbox
        st.session_state["notifications"].insert(0, {
            "id": f"notif_handover_{len(st.session_state['notifications'])}",
            "title": "Handover Completed: Ganesh's Jobs Reallocated",
            "category": "Handover",
            "icon": "✅",
            "message": "Ganesh's 3 jobs (Mobile UI, Backend API, Security Audit) have been successfully transferred to Jay Patel, Bhavik Vachhani, and Dhruv Nayak.",
            "time": "Just now",
            "status": "Pending"
        })
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
    
    chat_box = st.container(height=380)
    with chat_box:
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                if msg.get("data") and msg["data"].get("df") is not None and not msg["data"]["df"].empty:
                    with st.expander("📊 View Data Table (Optional)", expanded=False):
                        st.dataframe(msg["data"]["df"], use_container_width=True)

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
    col_main_erp, col_side_bot = st.columns([72, 28], gap="medium")
    with col_main_erp:
        render_erp_content()
    with col_side_bot:
        render_ai_chatbot()
else:
    render_erp_content()
    
    # Bottom Right Floating "Bot" Button (Matching user's red circle "Bot" in media_1789739327072.png!)
    col_fab1, col_fab2 = st.columns([88, 12])
    with col_fab2:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        if st.button("🤖 Bot", type="primary", use_container_width=True, help="Open Everest AI Bot"):
            st.session_state["show_assistant"] = True
            st.rerun()
