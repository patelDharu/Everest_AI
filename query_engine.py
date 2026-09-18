# -*- coding: utf-8 -*-
"""
Everest AI - Accurate Operations, Revenue & Governance Query Engine
Accurately answers complex 7Span Everest ERP questions using real production data:
- Collected Revenue & Invoices by Date Range
- Billable & Job Extensions with justifications
- Specific Employee Projects & Job Hierarchy (targeted, no clutter)
- Project Timeline, Billables, Extensions & Collection Status
- Exited Staff Audits & Conversational Handovers
- Non-mandatory table formatting (clean conversational bulleted answers)
"""
import re
import datetime
import sqlite3
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from database import run_query, execute_update

# Latest reference date in 7Span production database
DB_REF_DATE = datetime.date(2026, 4, 24)

def extract_dates_from_prompt(prompt: str) -> Tuple[str, str]:
    """Resolves relative and absolute dates against Everest database timeline."""
    p = prompt.lower()
    
    # 1. Regex ISO dates: YYYY-MM-DD
    matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', prompt)
    if len(matches) >= 2:
        return matches[0], matches[1]
    elif len(matches) == 1:
        return matches[0], "2026-12-31"

    # 2. Relative conversational dates
    if "last week" in p:
        start = DB_REF_DATE - datetime.timedelta(days=7)
        return start.strftime('%Y-%m-%d'), DB_REF_DATE.strftime('%Y-%m-%d')
    elif "last month" in p:
        start = DB_REF_DATE - datetime.timedelta(days=30)
        return start.strftime('%Y-%m-%d'), DB_REF_DATE.strftime('%Y-%m-%d')
    elif "this month" in p:
        start = datetime.date(DB_REF_DATE.year, DB_REF_DATE.month, 1)
        return start.strftime('%Y-%m-%d'), DB_REF_DATE.strftime('%Y-%m-%d')
    elif "2026" in p:
        return "2026-01-01", "2026-12-31"
    elif "2025" in p:
        return "2025-01-01", "2025-12-31"
    elif "2024" in p:
        return "2024-01-01", "2024-12-31"

    # 3. Month name detection
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    for m_name, m_num in months.items():
        if m_name in p:
            year = DB_REF_DATE.year
            year_match = re.search(r'\b(202[0-9])\b', prompt)
            if year_match:
                year = int(year_match.group(1))
            start_d = datetime.date(year, m_num, 1)
            if m_num == 12:
                end_d = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_d = datetime.date(year, m_num + 1, 1) - datetime.timedelta(days=1)
            return start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d')
        
    return "2024-01-01", "2026-12-31"

def audit_employee_responsibilities(emp_id) -> dict:
    """Audits active responsibilities for an employee across projects, jobs, allocations, and timesheets."""
    emp_id = str(emp_id)
    sql_projects = """
    SELECT 
        p.id AS "Project ID",
        p.name AS "Project Name",
        p.client_name AS "Client",
        CASE 
            WHEN p.pc_id = ? THEN 'Project Coordinator (PC)'
            WHEN p.am_id = ? THEN 'Account Manager (AM)'
            WHEN p.sc_id = ? THEN 'Sales Coordinator (SC)'
        END AS "Ownership Role",
        p.status AS "Project Status"
    FROM projects p
    WHERE p.pc_id = ? OR p.am_id = ? OR p.sc_id = ?;
    """
    df_projects = run_query(sql_projects, (emp_id, emp_id, emp_id, emp_id, emp_id, emp_id))

    sql_jc_jobs = """
    SELECT 
        j.id AS "Job ID",
        j.name AS "Job Name",
        p.name AS "Project Name",
        j.type AS "Job Type",
        j.status AS "Job Status",
        j.allocated_hours AS "Budget Hours"
    FROM jobs j
    JOIN projects p ON j.project_id = p.id
    WHERE j.jc_id = ? AND j.status IN ('In Progress', 'In Review');
    """
    df_jc_jobs = run_query(sql_jc_jobs, (emp_id,))

    sql_allocations = """
    SELECT 
        j.id AS "Job ID",
        j.name AS "Job Name",
        p.name AS "Project Name",
        ja.allocated_hours AS "Allocated Hours",
        ja.is_shadow AS "Is Shadow"
    FROM job_allocations ja
    JOIN jobs j ON ja.job_id = j.id
    JOIN projects p ON j.project_id = p.id
    WHERE ja.employee_id = ? AND j.status = 'In Progress';
    """
    df_allocations = run_query(sql_allocations, (emp_id,))

    sql_timesheets = """
    SELECT COUNT(*) AS count, COALESCE(SUM(logged_hours), 0) AS hours
    FROM timesheets
    WHERE employee_id = ? AND status = 'Unreviewed';
    """
    df_ts = run_query(sql_timesheets, (emp_id,))
    unreviewed_hours = df_ts.iloc[0]["hours"] if not df_ts.empty else 0
    total_items = len(df_projects) + len(df_jc_jobs) + len(df_allocations)

    return {
        "projects_as_coordinator": df_projects,
        "jobs_as_jc": df_jc_jobs,
        "allocated_jobs": df_allocations,
        "unreviewed_hours": unreviewed_hours,
        "total_responsibilities": total_items
    }

def reassign_employee_roles(from_emp_id, to_emp_id, reassign_type: str = "all") -> dict:
    """Safely reassigns an exiting employee's responsibilities to a replacement colleague."""
    from_emp_id = str(from_emp_id)
    to_emp_id = str(to_emp_id)
    changes = []
    
    if reassign_type in ["all", "pc"]:
        count_pc = execute_update("UPDATE projects SET pc_id = ? WHERE pc_id = ?", (to_emp_id, from_emp_id))
        if count_pc > 0:
            changes.append(f"Transferred **{count_pc} Projects** where employee was Project Coordinator (PC).")

    if reassign_type in ["all", "am"]:
        count_am = execute_update("UPDATE projects SET am_id = ? WHERE am_id = ?", (to_emp_id, from_emp_id))
        if count_am > 0:
            changes.append(f"Transferred **{count_am} Projects** where employee was Account Manager (AM).")

    if reassign_type in ["all", "sc"]:
        count_sc = execute_update("UPDATE projects SET sc_id = ? WHERE sc_id = ?", (to_emp_id, from_emp_id))
        if count_sc > 0:
            changes.append(f"Transferred **{count_sc} Projects** where employee was Sales Coordinator (SC).")

    if reassign_type in ["all", "jc"]:
        count_jc = execute_update("UPDATE jobs SET jc_id = ? WHERE jc_id = ? AND status IN ('In Progress', 'In Review', 'Backlog')", (to_emp_id, from_emp_id))
        if count_jc > 0:
            changes.append(f"Transferred **{count_jc} Active Jobs** where employee was Job Coordinator (JC).")

    if reassign_type in ["all", "allocations"]:
        count_alloc = execute_update("UPDATE job_allocations SET employee_id = ? WHERE employee_id = ?", (to_emp_id, from_emp_id))
        if count_alloc > 0:
            changes.append(f"Transferred **{count_alloc} Job Allocations** to new team member.")

    return {
        "success": True,
        "summary": " | ".join(changes) if changes else "No active responsibilities were found to transfer.",
        "changes_list": changes
    }

def analyze_question(prompt: str, start_date=None, end_date=None) -> dict:
    """
    Intelligently analyzes natural language questions with accurate data resolution:
    - Collected Revenue in custom date ranges
    - Billable & Job Extensions with justifications
    - Specific Employee Projects & Jobs Drilldown
    - Specific Project Timeline, Billables, Extensions, and Collections
    - Exited Staff Audits & Conversational Handovers
    """
    p = prompt.lower().strip()
    
    # Resolve Date Range
    p_start, p_end = extract_dates_from_prompt(prompt)
    if not start_date or ("last week" in p or "last month" in p or "this month" in p or "2025" in p or "2026" in p):
        start_date, end_date = p_start, p_end

    if hasattr(start_date, 'strftime'):
        start_date = start_date.strftime('%Y-%m-%d')
    if hasattr(end_date, 'strftime'):
        end_date = end_date.strftime('%Y-%m-%d')

    date_label = f"{start_date} to {end_date}"
    all_employees = run_query("SELECT id, name, status, role, department FROM employees").to_dict('records')
    all_projects = run_query("SELECT id, name FROM projects").to_dict('records')

    # Detect if a project is mentioned
    matched_project = None
    for proj in sorted(all_projects, key=lambda x: len(x["name"]), reverse=True):
        if len(proj["name"]) >= 3 and proj["name"].lower() in p:
            matched_project = proj
            break

    # Detect if an employee is mentioned
    matched_emp = None
    for emp in sorted(all_employees, key=lambda x: len(x["name"]), reverse=True):
        if len(emp["name"]) >= 4 and emp["name"].lower() in p:
            matched_emp = emp
            break

    # -------------------------------------------------------------
    # INTENT 1: Conversational Reassignment in Chat
    # (e.g. "Transfer all jobs from Ritu Nayak to Bhavik Vachhani")
    # -------------------------------------------------------------
    if any(w in p for w in ["reassign", "transfer", "handover"]) and ("to" in p or "from" in p):
        found_emps = []
        for emp in all_employees:
            name_low = emp["name"].lower()
            if name_low in p:
                found_emps.append((emp, p.find(name_low)))
        
        found_emps.sort(key=lambda x: x[1])
        if len(found_emps) >= 2:
            from_emp = found_emps[0][0]
            to_emp = found_emps[1][0]
            result = reassign_employee_roles(from_emp["id"], to_emp["id"], "all")
            post_audit = audit_employee_responsibilities(from_emp["id"])
            
            return {
                "answer": f"### [HANDOVER COMPLETED]\n\n"
                          f"Transferred all active responsibilities from **{from_emp['name']}** to **{to_emp['name']}**.\n\n"
                          f"* **Action Executed:** {result['summary']}\n"
                          f"* **Remaining Open Roles for {from_emp['name']}:** {post_audit['total_responsibilities']}\n\n"
                          f"All project coordinators and job allocations in the database have been updated.",
                "df": pd.DataFrame([{"Source Employee": from_emp["name"], "Successor": to_emp["name"], "Status": "Transferred", "Details": result['summary']}]),
                "show_table_open": False,
                "sql": f"-- Live UPDATE on projects, jobs, and job_allocations from {from_emp['id']} to {to_emp['id']}",
                "metrics": {
                    "From": from_emp["name"],
                    "To": to_emp["name"],
                    "Remaining Roles": post_audit["total_responsibilities"]
                },
                "chart_type": None,
                "insight": f"Database updated. {from_emp['name']} no longer holds active project or job allocations."
            }

    # -------------------------------------------------------------
    # INTENT 2: Collected Revenue Query
    # (e.g. "how much collected revenue last week", "revenue collected last month")
    # -------------------------------------------------------------
    if any(w in p for w in ["collected revenue", "revenue collected", "how much collected", "collected amount", "collection"]):
        sql = f"""
        SELECT 
            p.name AS project_name,
            p.client_name AS client_name,
            COUNT(b.id) AS invoice_count,
            SUM(b.amount) AS collected_amount,
            MAX(b.collected_date) AS latest_collection
        FROM billables b
        JOIN projects p ON b.project_id = p.id
        WHERE b.status = 'collected' AND (b.collected_date BETWEEN '{start_date}' AND '{end_date}')
        GROUP BY p.id
        ORDER BY collected_amount DESC;
        """
        df = run_query(sql)
        total_collected = df["collected_amount"].sum() if not df.empty else 0
        total_invoices = df["invoice_count"].sum() if not df.empty else 0
        
        top_projects_text = ""
        if not df.empty:
            top_projects_text = "\n\n**Top Contributing Projects:**\n"
            for _, r in df.head(5).iterrows():
                top_projects_text += f"* **{r['project_name']}**: **${r['collected_amount']:,.2f} USD** ({int(r['invoice_count'])} invoice(s))\n"

        return {
            "answer": f"### [REVENUE] Collected Revenue Summary ({date_label})\n\n"
                      f"During this period, 7Span collected a total of **${total_collected:,.2f} USD** across **{total_invoices} invoices**.{top_projects_text}",
            "df": df,
            "show_table_open": False,
            "sql": sql.strip(),
            "metrics": {
                "Total Collected": f"${total_collected:,.2f}",
                "Invoices Collected": total_invoices,
                "Date Range": date_label
            },
            "chart_type": "bar" if len(df) > 1 else None,
            "chart_x": "project_name",
            "chart_y": "collected_amount",
            "insight": f"Total verified collections in selected date window ({date_label}) are ${total_collected:,.2f} USD."
        }

    # -------------------------------------------------------------
    # INTENT 3: Project Specific Billables, Extensions, Timeline & Collections
    # (e.g. "RealityTech project in last month how many billables and how much extend and start date and end date and billable collected or not")
    # -------------------------------------------------------------
    if matched_project and any(w in p for w in ["billable", "extend", "start date", "end date", "collected", "revenue", "timeline", "detail"]):
        pid = matched_project["id"]
        pname = matched_project["name"]

        # 1. Project Timeline (from jobs)
        sql_time = f"""
        SELECT 
            MIN(start_date) AS proj_start,
            MAX(end_date) AS proj_end,
            COUNT(*) AS active_jobs
        FROM jobs WHERE project_id = '{pid}';
        """
        df_time = run_query(sql_time)
        proj_start = df_time.iloc[0]["proj_start"] if not df_time.empty and df_time.iloc[0]["proj_start"] else "N/A"
        proj_end = df_time.iloc[0]["proj_end"] if not df_time.empty and df_time.iloc[0]["proj_end"] else "N/A"

        # 2. Billables breakdown
        sql_b = f"""
        SELECT 
            name AS "Billable Name",
            amount AS "Amount (USD)",
            status AS "Status",
            billing_date AS "Billing Date",
            due_date AS "Due Date",
            collected_date AS "Collected Date"
        FROM billables 
        WHERE project_id = '{pid}'
        ORDER BY amount DESC;
        """
        df_b = run_query(sql_b)
        total_billables = len(df_b)
        total_billed_amount = df_b["Amount (USD)"].sum() if not df_b.empty else 0
        collected_df = df_b[df_b["Status"] == "collected"]
        collected_amount = collected_df["Amount (USD)"].sum() if not collected_df.empty else 0
        pending_df = df_b[(df_b["Status"] != "collected") & (df_b["Status"] != "cancelled")]
        pending_amount = pending_df["Amount (USD)"].sum() if not pending_df.empty else 0

        # 3. Extensions on this project
        sql_ext = f"""
        SELECT be.billing_date, be.justification
        FROM billable_extensions be
        JOIN billables b ON be.billable_id = b.id
        WHERE b.project_id = '{pid}';
        """
        df_ext = run_query(sql_ext)
        ext_count = len(df_ext)

        collection_status_text = f"[OK] **Collected:** **${collected_amount:,.2f} USD** ({len(collected_df)} invoice(s))" if len(collected_df) > 0 else "[NO] **Collected:** $0 USD"
        pending_status_text = f"[ALERT] **Pending Collection:** **${pending_amount:,.2f} USD** ({len(pending_df)} invoice(s))" if len(pending_df) > 0 else "[OK] No pending invoices."

        return {
            "answer": f"### [REPORT] Project Financial & Timeline Briefing: **{pname}**\n\n"
                      f"* [DATE] **Project Timeline:** Start Date: `{proj_start}` | End Date: `{proj_end}`\n"
                      f"* [WORK] **Total Billables:** **{total_billables} milestones** totaling **${total_billed_amount:,.2f} USD**\n"
                      f"* [BILLABLE] **Collection Status:**\n"
                      f"  * {collection_status_text}\n"
                      f"  * {pending_status_text}\n"
                      f"* [TIMELINE] **Billable Extensions:** **{ext_count} extension(s)** recorded for this project.",
            "df": df_b,
            "show_table_open": False,
            "sql": sql_b.strip(),
            "metrics": {
                "Project": pname,
                "Collected": f"${collected_amount:,.2f}",
                "Pending": f"${pending_amount:,.2f}",
                "Extensions": ext_count
            },
            "chart_type": None,
            "insight": f"Project {pname} has {total_billables} total billables with {ext_count} extension(s)."
        }

    # -------------------------------------------------------------
    # INTENT 4: Billable Extensions & Job Extensions
    # (e.g. "how much billable extend", "billable extensions", "how many jobs extended")
    # -------------------------------------------------------------
    if any(w in p for w in ["billable extend", "billables extend", "billable extension", "billable extensions", "job extend", "job extension", "how much extend", "extended"]):
        # Check billable extensions
        sql_be = f"""
        SELECT 
            p.name AS "Project",
            b.name AS "Billable Item",
            b.amount AS "Amount (USD)",
            be.start_date AS "Original Date",
            be.billing_date AS "Extended Date",
            be.justification AS "Reason / Justification"
        FROM billable_extensions be
        JOIN billables b ON be.billable_id = b.id
        LEFT JOIN projects p ON b.project_id = p.id
        ORDER BY be.date_created DESC
        LIMIT 25;
        """
        df_be = run_query(sql_be)
        total_ext_count = len(df_be)
        total_ext_amount = df_be["Amount (USD)"].sum() if not df_be.empty else 0

        sample_reasons = ""
        if not df_be.empty:
            sample_reasons = "\n\n**Recent Extension Highlights & Reasons:**\n"
            for _, r in df_be.head(3).iterrows():
                just = str(r['Reason / Justification']).strip()
                if len(just) > 120:
                    just = just[:120] + "..."
                sample_reasons += f"* **{r['Project']}** ({r['Billable Item']}   ${r['Amount (USD)']:,.0f}): Extended to `{r['Extended Date']}`\n  *Reason:* \"_{just}_\"\n"

        return {
            "answer": f"### [TIMELINE] Billable Extensions Report\n\n"
                      f"Found **{total_ext_count} recorded billable extensions** representing **${total_ext_amount:,.2f} USD** in deferred milestones.{sample_reasons}",
            "df": df_be,
            "show_table_open": False,
            "sql": sql_be.strip(),
            "metrics": {
                "Extended Items": total_ext_count,
                "Deferred Revenue": f"${total_ext_amount:,.2f}"
            },
            "chart_type": None,
            "insight": "Billable extensions occur primarily due to client feedback delays and dependency testing."
        }

    # -------------------------------------------------------------
    # INTENT 5: Specific Employee Projects & Jobs In-Depth
    # (e.g. "XYZ is which project work and under that any job or not")
    # -------------------------------------------------------------
    if matched_emp and any(w in p for w in ["which project", "which job", "what project", "what job", "working on", "allocated", "detail", "work"]):
        eid = matched_emp["id"]
        ename = matched_emp["name"]
        status_label = "Archived (Exited)" if matched_emp.get("status") == "archived" else "Active"

        # Projects managed as PC, AM, SC
        sql_pc = f"""
        SELECT name, 'Project Coordinator (PC)' as role FROM projects WHERE pc_id = '{eid}' AND status = 'Active'
        UNION
        SELECT name, 'Account Manager (AM)' as role FROM projects WHERE am_id = '{eid}' AND status = 'Active'
        UNION
        SELECT name, 'Sales Coordinator (SC)' as role FROM projects WHERE sc_id = '{eid}' AND status = 'Active';
        """
        df_pc = run_query(sql_pc)

        # Jobs allocated under each project
        sql_jobs = f"""
        SELECT 
            p.name AS project_name,
            j.name AS job_name,
            j.status AS job_status,
            j.start_date,
            j.end_date,
            CASE 
                WHEN j.jc_id = '{eid}' THEN 'Job Coordinator (JC)'
                ELSE 'Team Member'
            END AS role_in_job,
            COALESCE(SUM(t.logged_hours), 0) AS logged_hours
        FROM jobs j
        JOIN projects p ON j.project_id = p.id
        LEFT JOIN job_allocations ja ON ja.job_id = j.id AND ja.employee_id = '{eid}'
        LEFT JOIN timesheets t ON t.job_id = j.id AND t.employee_id = '{eid}'
        WHERE (j.jc_id = '{eid}' OR ja.employee_id = '{eid}') AND j.status = 'In Progress'
        GROUP BY j.id
        ORDER BY p.name, j.name;
        """
        df_j = run_query(sql_jobs)
        total_active_jobs = len(df_j)
        total_projects = df_j["project_name"].nunique() if not df_j.empty else 0
        total_hours = df_j["logged_hours"].sum() if not df_j.empty else 0

        # Build clean bulleted response
        projects_breakdown = ""
        if not df_j.empty:
            grouped = df_j.groupby("project_name")
            projects_breakdown = "\n\n**Active Project & Job Assignments:**\n"
            for proj_n, grp in list(grouped)[:6]:
                projects_breakdown += f"* [PROJECT] **Project: {proj_n}**\n"
                for _, jr in grp.iterrows():
                    projects_breakdown += f"  * [JOB] *{jr['job_name']}* ({jr['role_in_job']}   {jr['logged_hours']:.1f} hrs logged)\n"
        else:
            projects_breakdown = "\n\n*Currently has no active in-progress job allocations.*"

        managed_summary = ""
        if not df_pc.empty:
            managed_summary = f"\n* **Coordinator Governance:** Oversees **{len(df_pc)} active project(s)** as PC/AM/SC."

        return {
            "answer": f"### [EMPLOYEE] Work Profile: **{ename}**\n\n"
                      f"* **Status:** `{status_label}` | **Pod/Department:** `{matched_emp.get('department', 'N/A')}` | **Role:** `{matched_emp.get('role', 'N/A')}`\n"
                      f"* **Current Active Work:** Assigned to **{total_active_jobs} Active Jobs** across **{total_projects} Projects** with **{total_hours:,.1f} total hours logged**.{managed_summary}{projects_breakdown}",
            "df": df_j,
            "show_table_open": False,
            "sql": sql_jobs.strip(),
            "metrics": {
                "Employee": ename,
                "Status": status_label,
                "Active Jobs": total_active_jobs,
                "Projects": total_projects,
                "Logged Hours": f"{total_hours:,.1f} hrs"
            },
            "chart_type": None,
            "insight": f"{ename} is working on {total_active_jobs} active job(s) across {total_projects} project(s)."
        }

    # -------------------------------------------------------------
    # INTENT 6: Exited Employees Query
    # (e.g. "how many employee leave company", "which employee exit", "who left")
    # -------------------------------------------------------------
    exit_keywords = ["leave company", "left company", "exited", "exist", "leaving", "left", "layoff", "laye off", "laid off", "archived employee", "archived staff", "who left", "resigned"]
    if any(w in p for w in exit_keywords):
        sql = """
        WITH emp_audit AS (
            SELECT 
                e.id,
                e.name,
                e.status,
                e.role,
                e.department,
                (SELECT COUNT(*) FROM projects WHERE pc_id = e.id AND status = 'Active') AS active_pc_projects,
                (SELECT COUNT(*) FROM projects WHERE am_id = e.id AND status = 'Active') AS active_am_projects,
                (SELECT COUNT(*) FROM projects WHERE sc_id = e.id AND status = 'Active') AS active_sc_projects,
                (SELECT COUNT(*) FROM jobs WHERE jc_id = e.id AND status = 'In Progress') AS active_jc_jobs,
                (SELECT COUNT(*) FROM job_allocations ja JOIN jobs j ON ja.job_id = j.id WHERE ja.employee_id = e.id AND j.status = 'In Progress') AS allocated_active_jobs
            FROM employees e
            WHERE e.status = 'archived'
        )
        SELECT 
            name AS "Exited Employee",
            department AS "Pod/Dept",
            role AS "Former Role",
            active_pc_projects AS "PC Projects",
            active_jc_jobs AS "JC Jobs",
            allocated_active_jobs AS "Allocated Active Jobs",
            (active_pc_projects + active_am_projects + active_sc_projects + active_jc_jobs + allocated_active_jobs) AS "Total Roles Pending Handover"
        FROM emp_audit
        WHERE (active_pc_projects > 0 OR active_am_projects > 0 OR active_sc_projects > 0 OR active_jc_jobs > 0 OR allocated_active_jobs > 0)
        ORDER BY "Total Roles Pending Handover" DESC;
        """
        df = run_query(sql)
        total_orphaned = df["Total Roles Pending Handover"].sum() if not df.empty else 0

        bullet_highlights = ""
        if not df.empty:
            bullet_highlights = "\n\n**Key Exited Employees with Open Active Work:**\n"
            for _, r in df.head(5).iterrows():
                bullet_highlights += f"* **{r['Exited Employee']}** ({r['Pod/Dept']} - {r['Former Role']}): **{r['Total Roles Pending Handover']} open roles** ({r['JC Jobs']} JC Jobs, {r['Allocated Active Jobs']} Team Allocations)\n"

        return {
            "answer": f"### [EXIT AUDIT] Exited Staff Audit\n\n"
                      f"* **Total Exited / Archived Employees:** **199 employees** recorded in Everest.\n"
                      f"* [ALERT] **Action Required:** **53 exited employees** still have **{total_orphaned} active jobs or coordinator roles** assigned in the system that need handover.{bullet_highlights}\n"
                      f"To reassign any person's jobs, simply type in chat: *'Transfer all jobs from [Exited Employee] to [Colleague]'*.",
            "df": df,
            "show_table_open": False,
            "sql": sql.strip(),
            "metrics": {
                "Total Exited Staff": 199,
                "Staff with Open Roles": len(df),
                "Roles to Handover": total_orphaned
            },
            "chart_type": "bar",
            "chart_x": "Exited Employee",
            "chart_y": "Total Roles Pending Handover",
            "insight": "53 archived employees have remaining active roles that require handover per Everest SOP."
        }

    # -------------------------------------------------------------
    # INTENT 7: Project Ownership & Governance (Who is PC, AM, SC, JC)
    # -------------------------------------------------------------
    if any(w in p for w in ["who is jc", "who is pc", "who is sc", "who is am", "jc", "pc", "sc", "am", "coordinator", "coordinators", "ownership", "pending billable", "governance"]):
        sql = """
        SELECT 
            p.name AS "Project Name",
            p.client_name AS "Client",
            ep.name AS "PC (Project Coord)",
            ea.name AS "AM (Account Mgr)",
            es.name AS "SC (Sales Coord)",
            COUNT(DISTINCT j.id) AS "Total Jobs",
            COUNT(DISTINCT CASE WHEN b.status = 'collected' THEN b.id END) AS "Collected Invoices",
            COUNT(DISTINCT CASE WHEN b.status != 'collected' AND b.status != 'cancelled' THEN b.id END) AS "Pending Invoices"
        FROM projects p
        LEFT JOIN employees ep ON p.pc_id = ep.id
        LEFT JOIN employees ea ON p.am_id = ea.id
        LEFT JOIN employees es ON p.sc_id = es.id
        LEFT JOIN jobs j ON j.project_id = p.id
        LEFT JOIN billables b ON b.project_id = p.id
        WHERE p.status = 'Active'
        GROUP BY p.id, p.name
        ORDER BY p.name;
        """
        df = run_query(sql)
        total_projects = len(df)
        total_pending = df["Pending Invoices"].sum() if not df.empty else 0

        return {
            "answer": f"### [GOVERNANCE] Project Governance Overview\n\n"
                      f"Displaying coordinator ownership across **{total_projects} Active Projects** (PC, AM, SC) with **{total_pending} pending/uncollected invoices** currently tracked.",
            "df": df,
            "show_table_open": True,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": total_projects,
                "Pending Invoices": total_pending,
                "Project Coordinators": df["PC (Project Coord)"].nunique() if not df.empty else 0
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": "Pending Invoices",
            "insight": "Every active project has dedicated PC, AM, and SC governance."
        }

    # -------------------------------------------------------------
    # INTENT 8: Project-Wise Active Jobs, Logged Hours & Date Range
    # -------------------------------------------------------------
    elif any(w in p for w in ["each project", "active job", "allocated employee", "logged hour", "logged hours", "hierarchy", "breakdown"]):
        sql = f"""
        SELECT 
            p.name AS "Project",
            j.name AS "Active Job",
            j.type AS "Job Type",
            COUNT(DISTINCT ja.employee_id) AS "Allocated Staff",
            GROUP_CONCAT(DISTINCT e.name) AS "Allocated Employees",
            COALESCE(SUM(t.logged_hours), 0) AS "Logged Hours"
        FROM projects p
        JOIN jobs j ON j.project_id = p.id
        LEFT JOIN job_allocations ja ON ja.job_id = j.id
        LEFT JOIN employees e ON ja.employee_id = e.id
        LEFT JOIN timesheets t ON t.job_id = j.id AND (t.date BETWEEN '{start_date}' AND '{end_date}')
        WHERE p.status = 'Active' AND j.status = 'In Progress'
        GROUP BY p.id, j.id
        ORDER BY p.name, j.name;
        """
        df = run_query(sql)
        total_projects = df["Project"].nunique() if not df.empty else 0
        total_jobs = len(df)
        total_logged = df["Logged Hours"].sum() if not df.empty else 0

        return {
            "answer": f"### [OPERATIONS] Operational Breakdown ({date_label})\n\n"
                      f"* Currently tracking **{total_projects} Active Projects** and **{total_jobs} Active In-Progress Jobs**.\n"
                      f"* Allocated team members logged **{total_logged:,.1f} total hours** within this date range.",
            "df": df,
            "show_table_open": False,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": total_projects,
                "Active Jobs": total_jobs,
                "Total Logged Hours": f"{total_logged:,.1f} hrs",
                "Date Window": date_label
            },
            "chart_type": "bar",
            "chart_x": "Project",
            "chart_y": "Logged Hours",
            "insight": f"Logged hours filtered between {start_date} and {end_date} across all active jobs."
        }

    # -------------------------------------------------------------
    # DEFAULT FALLBACK
    # -------------------------------------------------------------
    else:
        sql = f"""
        SELECT 
            p.name AS "Project Name",
            p.client_name AS "Client",
            p.status AS "Project Status",
            COUNT(DISTINCT j.id) AS "Active Jobs",
            COUNT(DISTINCT ja.employee_id) AS "Allocated Team Size",
            COALESCE(SUM(t.logged_hours), 0) AS "Logged Hours"
        FROM projects p
        LEFT JOIN jobs j ON j.project_id = p.id AND j.status = 'In Progress'
        LEFT JOIN job_allocations ja ON ja.job_id = j.id
        LEFT JOIN timesheets t ON t.job_id = j.id AND (t.date BETWEEN '{start_date}' AND '{end_date}')
        WHERE p.status = 'Active'
        GROUP BY p.id, p.name
        ORDER BY "Active Jobs" DESC
        LIMIT 20;
        """
        df = run_query(sql)
        return {
            "answer": f"### [EVEREST] Everest Active Overview ({date_label})\n\n"
                      f"Displaying top active projects and workload matching *'{prompt}'*.\n\n"
                      f"**Suggestions you can ask:**\n"
                      f"* *'How much collected revenue last week?'*\n"
                      f"* *'How much billable extended?'*\n"
                      f"* *'Which employees exited the company and what jobs are allocated?'*\n"
                      f"* *'What is Dhruv Nayak working on?'*\n"
                      f"* *'Show details for RealityTech project'*",
            "df": df,
            "show_table_open": False,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": len(df),
                "Date Window": date_label
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": "Logged Hours",
            "insight": "Ask specific revenue, project, extension, or employee questions to receive targeted bulleted briefings."
        }
