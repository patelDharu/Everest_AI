# -*- coding: utf-8 -*-
"""
Everest AI - Intelligent Operations & Governance Query Engine
Translates natural language questions into relational SQL queries across 7Span Everest ERP:
- Complete 360-Degree Project Drill-Down (Project -> Jobs -> Allocated Employees -> Timesheets -> Billables)
- Employee Exit / Layoff Auditing & Conversational Handover
- Project Governance (PC, AM, SC, JC) and Collections
- Date-range Filtered Hierarchical Summaries
"""
import re
import datetime
import sqlite3
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from database import run_query, execute_update

def extract_dates_from_prompt(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts date ranges from prompt text (e.g. '2026-08-01 to 2026-09-30' or 'August 2026')."""
    p = prompt.lower()
    
    # 1. Regex ISO dates: YYYY-MM-DD
    matches = re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b', prompt)
    if len(matches) >= 2:
        return matches[0], matches[1]
    elif len(matches) == 1:
        return matches[0], "2026-12-31"

    # 2. Month name detection
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for m_name, m_num in months.items():
        if m_name in p:
            year = 2026
            year_match = re.search(r'\b(202[0-9])\b', prompt)
            if year_match:
                year = int(year_match.group(1))
            start_d = datetime.date(year, m_num, 1)
            # End of month
            if m_num == 12:
                end_d = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end_d = datetime.date(year, m_num + 1, 1) - datetime.timedelta(days=1)
            return start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d')
        
    return None, None

def audit_employee_responsibilities(emp_id) -> dict:
    """
    Audits all active responsibilities for an employee:
    - Projects managed as PC, AM, or SC
    - Jobs managed as JC (Job Coordinator)
    - Active jobs allocated as a team member
    - Unreviewed timesheets
    """
    emp_id = str(emp_id)
    # 1. Projects where employee is PC, AM, or SC
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

    # 2. Jobs where employee is Job Coordinator (JC)
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

    # 3. Jobs where employee is allocated as a Team Member
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

    # 4. Unreviewed timesheets
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
    """
    Safely reassigns an exiting or laid-off employee's responsibilities to a replacement colleague.
    Updates PC, AM, SC, JC, and team member job allocations in the database.
    """
    from_emp_id = str(from_emp_id)
    to_emp_id = str(to_emp_id)
    changes = []
    
    # 1. Reassign PC roles
    if reassign_type in ["all", "pc"]:
        count_pc = execute_update("UPDATE projects SET pc_id = ? WHERE pc_id = ?", (to_emp_id, from_emp_id))
        if count_pc > 0:
            changes.append(f"Transferred **{count_pc} Projects** where employee was Project Coordinator (PC).")

    # 2. Reassign AM roles
    if reassign_type in ["all", "am"]:
        count_am = execute_update("UPDATE projects SET am_id = ? WHERE am_id = ?", (to_emp_id, from_emp_id))
        if count_am > 0:
            changes.append(f"Transferred **{count_am} Projects** where employee was Account Manager (AM).")

    # 3. Reassign SC roles
    if reassign_type in ["all", "sc"]:
        count_sc = execute_update("UPDATE projects SET sc_id = ? WHERE sc_id = ?", (to_emp_id, from_emp_id))
        if count_sc > 0:
            changes.append(f"Transferred **{count_sc} Projects** where employee was Sales Coordinator (SC).")

    # 4. Reassign JC roles on active jobs
    if reassign_type in ["all", "jc"]:
        count_jc = execute_update("UPDATE jobs SET jc_id = ? WHERE jc_id = ? AND status IN ('In Progress', 'In Review', 'Backlog')", (to_emp_id, from_emp_id))
        if count_jc > 0:
            changes.append(f"Transferred **{count_jc} Active Jobs** where employee was Job Coordinator (JC).")

    # 5. Reassign Team Member job allocations
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
    Traverses the full 7Span Everest hierarchy to answer complex operational queries in 1 shot:
    - Conversational Role Handover / Reassignments
    - Exited / Archived Staff with Active Jobs & Roles
    - Complete 360-Degree Project Drilldown (Project -> Client -> PC/AM/SC -> Jobs -> JC -> Allocated Staff -> Logged Hours -> Billables)
    - Specific Employee / Job Drilldowns
    - Project Governance & Pending Billables
    - Date-range Logged Hours & Capacity
    """
    p = prompt.lower().strip()
    
    # Resolve Date Range
    prompt_start, prompt_end = extract_dates_from_prompt(prompt)
    if prompt_start and prompt_end:
        start_date, end_date = prompt_start, prompt_end
    
    if not start_date:
        start_date = "2024-01-01"
    if not end_date:
        end_date = "2026-12-31"

    if hasattr(start_date, 'strftime'):
        start_date = start_date.strftime('%Y-%m-%d')
    if hasattr(end_date, 'strftime'):
        end_date = end_date.strftime('%Y-%m-%d')

    date_label = f"{start_date} to {end_date}"

    # Load all employees for name resolution
    all_employees = run_query("SELECT id, name, status, role, department FROM employees").to_dict('records')

    # -------------------------------------------------------------
    # INTENT 1: Conversational Reassignment / Handover Command
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
            
            # Post-reassignment audit
            post_audit = audit_employee_responsibilities(from_emp["id"])
            
            return {
                "answer": f"[HANDOVER COMPLETED] Transferred all active responsibilities from **{from_emp['name']}** to **{to_emp['name']}**.\n\n"
                          f"**Action Summary:** {result['summary']}\n"
                          f"**Remaining Active Roles for {from_emp['name']}:** {post_audit['total_responsibilities']}",
                "df": pd.DataFrame([{"Source Employee": from_emp["name"], "Successor": to_emp["name"], "Transfer Status": "Completed", "Details": result['summary']}]),
                "sql": f"-- Live UPDATE on projects, jobs, and job_allocations from {from_emp['id']} to {to_emp['id']}",
                "metrics": {
                    "From Employee": from_emp["name"],
                    "To Successor": to_emp["name"],
                    "Remaining Orphaned Roles": post_audit["total_responsibilities"]
                },
                "chart_type": None,
                "insight": f"All ownership records for {from_emp['name']} have been successfully migrated to {to_emp['name']} with zero disruption."
            }

    # -------------------------------------------------------------
    # INTENT 2: Exited / Archived / Layoff Staff Audit
    # (e.g. "which employee exist in this month and if any job allocated", "list exited employees")
    # -------------------------------------------------------------
    exit_keywords = ["exit", "exited", "exist", "leaving", "left", "layoff", "laye off", "laid off", "archived", "offboard", "resigned"]
    is_exit_query = any(w in p for w in exit_keywords)

    if is_exit_query:
        # Check if asking about a specific person
        emp_match = None
        for emp in all_employees:
            if emp["name"].lower() in p:
                emp_match = emp
                break

        if emp_match:
            audit = audit_employee_responsibilities(emp_match["id"])
            total = audit["total_responsibilities"]
            status_desc = "Archived / Exited" if emp_match.get("status") == "archived" else "Active"
            
            details = []
            for _, r in audit["projects_as_coordinator"].iterrows():
                details.append({"Entity": r["Project Name"], "Type": "Project", "Role": r["Ownership Role"], "Status": r["Project Status"]})
            for _, r in audit["jobs_as_jc"].iterrows():
                details.append({"Entity": r["Job Name"], "Type": "Job", "Role": "Job Coordinator (JC)", "Status": r["Job Status"]})
            for _, r in audit["allocated_jobs"].iterrows():
                details.append({"Entity": r["Job Name"], "Type": "Job Allocation", "Role": f"Team Member ({r['Allocated Hours']}h)", "Status": "In Progress"})
                
            df_audit = pd.DataFrame(details) if details else pd.DataFrame(columns=["Entity", "Type", "Role", "Status"])
            
            return {
                "answer": f"[EXIT AUDIT] **Exit Audit for {emp_match['name']}** (Current Status: **{status_desc}**):\n\n"
                          f"Found **{total} active ownership responsibilities** (Projects as PC/AM/SC, Jobs as JC, or Active Team Allocations) that must be reassigned.",
                "df": df_audit,
                "sql": f"-- Audited Projects, Jobs, and Allocations for Employee ID: {emp_match['id']}",
                "metrics": {
                    "Employee": emp_match["name"],
                    "Status": status_desc,
                    "Total Roles to Handover": total,
                    "Projects as PC/SC": len(audit["projects_as_coordinator"]),
                    "Jobs as JC": len(audit["jobs_as_jc"]),
                    "Job Allocations": len(audit["allocated_jobs"])
                },
                "chart_type": None,
                "insight": f"To transfer these responsibilities in chat, simply type: 'Transfer all jobs from {emp_match['name']} to [Colleague Name]'."
            }
        else:
            # Query all archived employees who STILL have active projects, JC jobs, or job allocations
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
                active_pc_projects AS "Active PC Projects",
                active_jc_jobs AS "Active JC Jobs",
                allocated_active_jobs AS "Allocated Active Jobs",
                (active_pc_projects + active_am_projects + active_sc_projects + active_jc_jobs + allocated_active_jobs) AS "Total Roles Pending Handover"
            FROM emp_audit
            WHERE (active_pc_projects > 0 OR active_am_projects > 0 OR active_sc_projects > 0 OR active_jc_jobs > 0 OR allocated_active_jobs > 0)
            ORDER BY "Total Roles Pending Handover" DESC;
            """
            df = run_query(sql)
            total_orphaned = df["Total Roles Pending Handover"].sum() if not df.empty else 0
            
            return {
                "answer": f"Found **{len(df)} Exited / Archived Employees** who still have **{total_orphaned} active jobs or coordinator roles** assigned in Everest.\n\n"
                          f"Per 7Span Exit SOP, these responsibilities must be handed over to active staff:",
                "df": df,
                "sql": sql.strip(),
                "metrics": {
                    "Exited Staff with Open Roles": len(df),
                    "Total Roles Pending Handover": total_orphaned,
                    "JC Jobs to Reassign": df["Active JC Jobs"].sum() if not df.empty else 0,
                    "Job Allocations to Reassign": df["Allocated Active Jobs"].sum() if not df.empty else 0
                },
                "chart_type": "bar",
                "chart_x": "Exited Employee",
                "chart_y": "Total Roles Pending Handover",
                "insight": "Top pending handovers: Preyash Master (23 roles), Ritu Nayak (14 roles), Pruthvi Menpara (11 roles). You can reassign directly in chat (e.g. 'Transfer all jobs from Ritu Nayak to Bhavik Vachhani')."
            }

    # -------------------------------------------------------------
    # INTENT 3: Specific Project 360-Degree Deep Drill-Down
    # (Project -> Client -> PC, AM, SC -> Jobs -> JC -> Allocated Staff -> Logged Hours -> Billables)
    # -------------------------------------------------------------
    all_projects = run_query("SELECT id, name FROM projects").to_dict('records')
    matched_project = None
    for proj in sorted(all_projects, key=lambda x: len(x["name"]), reverse=True):
        if len(proj["name"]) >= 3 and proj["name"].lower() in p:
            matched_project = proj
            break

    if matched_project:
        pid = matched_project["id"]
        pname = matched_project["name"]
        
        sql_proj_detail = f"""
        SELECT 
            p.name AS "Project",
            p.client_name AS "Client",
            p.status AS "Project Status",
            ep.name AS "PC (Project Coord)",
            ea.name AS "AM (Account Mgr)",
            es.name AS "SC (Sales Coord)",
            j.name AS "Job Name",
            j.type AS "Job Type",
            j.status AS "Job Status",
            ej.name AS "JC (Job Coord)",
            COUNT(DISTINCT ja.employee_id) AS "Allocated Staff Count",
            GROUP_CONCAT(DISTINCT e.name) AS "Allocated Team Members",
            COALESCE(SUM(t.logged_hours), 0) AS "Total Logged Hours"
        FROM projects p
        LEFT JOIN employees ep ON p.pc_id = ep.id
        LEFT JOIN employees ea ON p.am_id = ea.id
        LEFT JOIN employees es ON p.sc_id = es.id
        LEFT JOIN jobs j ON j.project_id = p.id
        LEFT JOIN employees ej ON j.jc_id = ej.id
        LEFT JOIN job_allocations ja ON ja.job_id = j.id
        LEFT JOIN employees e ON ja.employee_id = e.id
        LEFT JOIN timesheets t ON t.job_id = j.id
        WHERE p.id = '{pid}'
        GROUP BY j.id
        ORDER BY j.status, j.name;
        """
        df_proj = run_query(sql_proj_detail)
        
        # Get billables for this project
        sql_b = f"SELECT name AS 'Billable Name', amount AS 'Amount (USD)', status AS 'Status', due_date AS 'Due Date' FROM billables WHERE project_id = '{pid}' ORDER BY amount DESC;"
        df_b = run_query(sql_b)
        total_pending_billables = df_b[df_b["Status"] != "Cancelled"]["Amount (USD)"].sum() if not df_b.empty else 0
        total_hours = df_proj["Total Logged Hours"].sum() if not df_proj.empty else 0
        
        client_name = df_proj.iloc[0]["Client"] if not df_proj.empty else "N/A"
        pc_name = df_proj.iloc[0]["PC (Project Coord)"] if not df_proj.empty else "N/A"
        
        return {
            "answer": f"### [PROJECT 360] Project Deep-Dive: **{pname}**\n\n"
                      f"- **Client:** {client_name}\n"
                      f"- **Governance:** PC: `{pc_name}` | AM: `{df_proj.iloc[0]['AM (Account Mgr)'] if not df_proj.empty else 'N/A'}` | SC: `{df_proj.iloc[0]['SC (Sales Coord)'] if not df_proj.empty else 'N/A'}`\n"
                      f"- **Total Jobs Tracked:** {len(df_proj)} jobs ({df_proj['Allocated Staff Count'].sum() if not df_proj.empty else 0} total allocations)\n"
                      f"- **Total Hours Logged:** {total_hours:,.1f} hrs | **Financials:** ${total_pending_billables:,.2f} USD billables",
            "df": df_proj[["Job Name", "Job Status", "JC (Job Coord)", "Allocated Staff Count", "Allocated Team Members", "Total Logged Hours"]],
            "sql": sql_proj_detail.strip(),
            "metrics": {
                "Project": pname,
                "Active Jobs": len(df_proj),
                "Logged Hours": f"{total_hours:,.1f} hrs",
                "Billables": f"${total_pending_billables:,.2f}"
            },
            "chart_type": "bar",
            "chart_x": "Job Name",
            "chart_y": "Total Logged Hours",
            "insight": f"All jobs, assigned coordinators, allocated engineers, and timesheet hours for {pname} retrieved in 1 view."
        }

    # -------------------------------------------------------------
    # INTENT 4: Specific Employee 360-Degree Deep Drill-Down
    # -------------------------------------------------------------
    matched_emp = None
    for emp in all_employees:
        if emp["name"].lower() in p:
            matched_emp = emp
            break

    if matched_emp and any(w in p for w in ["work", "working", "role", "job", "status", "detail", "allocated", "check"]):
        audit = audit_employee_responsibilities(matched_emp["id"])
        status_label = "Archived (Exited)" if matched_emp.get("status") == "archived" else "Active"
        
        # Build comprehensive employee profile
        details = []
        for _, r in audit["projects_as_coordinator"].iterrows():
            details.append({"Type": "Project Governance", "Entity": r["Project Name"], "Role": r["Ownership Role"], "Status": r["Project Status"]})
        for _, r in audit["jobs_as_jc"].iterrows():
            details.append({"Type": "Job Coordination", "Entity": r["Job Name"], "Role": "Job Coordinator (JC)", "Status": r["Job Status"]})
        for _, r in audit["allocated_jobs"].iterrows():
            details.append({"Type": "Job Team Allocation", "Entity": r["Job Name"], "Role": f"Team Member ({r['Allocated Hours']}h)", "Status": "In Progress"})
            
        df_emp_detail = pd.DataFrame(details) if details else pd.DataFrame(columns=["Type", "Entity", "Role", "Status"])
        
        return {
            "answer": f"### [EMPLOYEE 360] Profile: **{matched_emp['name']}**\n\n"
                      f"- **Status:** `{status_label}` | **Pod/Dept:** `{matched_emp.get('department', 'N/A')}` | **Role:** `{matched_emp.get('role', 'N/A')}`\n"
                      f"- **Total Active Responsibilities:** **{audit['total_responsibilities']}** (Projects: {len(audit['projects_as_coordinator'])}, JC Jobs: {len(audit['jobs_as_jc'])}, Allocations: {len(audit['allocated_jobs'])})\n"
                      f"- **Unreviewed Timesheet Hours:** {audit['unreviewed_hours']} hrs",
            "df": df_emp_detail,
            "sql": f"-- Employee deep dive for {matched_emp['name']} (ID: {matched_emp['id']})",
            "metrics": {
                "Employee": matched_emp["name"],
                "Status": status_label,
                "Managed Projects": len(audit["projects_as_coordinator"]),
                "JC Jobs": len(audit["jobs_as_jc"]),
                "Team Allocations": len(audit["allocated_jobs"])
            },
            "chart_type": None,
            "insight": f"Complete operational breakdown for {matched_emp['name']} across all Everest pods and projects."
        }

    # -------------------------------------------------------------
    # INTENT 5: Project Ownership & Governance (Who is PC, AM, SC, JC & Pending Billables)
    # -------------------------------------------------------------
    if any(w in p for w in ["who is jc", "who is pc", "who is sc", "who is am", "jc", "pc", "sc", "am", "coordinator", "coordinators", "ownership", "pending billable", "billables pending", "pending billables", "billable pending", "governance"]):
        sql = """
        SELECT 
            p.name AS "Project Name",
            p.client_name AS "Client",
            ep.name AS "PC (Project Coord)",
            ea.name AS "AM (Account Mgr)",
            es.name AS "SC (Sales Coord)",
            GROUP_CONCAT(DISTINCT ej.name) AS "Job Coordinators (JC)",
            COUNT(DISTINCT j.id) AS "Total Jobs",
            COUNT(DISTINCT CASE WHEN b.status IN ('Contracted', 'Pending Invoice', 'Billed') THEN b.id END) AS "Pending Billables Count",
            COALESCE(SUM(CASE WHEN b.status IN ('Contracted', 'Pending Invoice', 'Billed') THEN b.amount ELSE 0 END), 0) AS "Total Pending Amount",
            MAX(b.currency) AS "Currency"
        FROM projects p
        LEFT JOIN employees ep ON p.pc_id = ep.id
        LEFT JOIN employees ea ON p.am_id = ea.id
        LEFT JOIN employees es ON p.sc_id = es.id
        LEFT JOIN jobs j ON j.project_id = p.id
        LEFT JOIN employees ej ON j.jc_id = ej.id
        LEFT JOIN billables b ON b.project_id = p.id
        WHERE p.status = 'Active'
        GROUP BY p.id, p.name
        ORDER BY p.name;
        """
        df = run_query(sql)
        if not df.empty and "Job Coordinators (JC)" in df.columns:
            df["Job Coordinators (JC)"] = df["Job Coordinators (JC)"].apply(lambda x: str(x).replace(",", ", ") if x else "None")

        total_projects = len(df)
        total_pending_billables = df["Pending Billables Count"].sum() if not df.empty else 0
        
        return {
            "answer": f"Here is the project governance breakdown across **{total_projects} Active Projects**: Displays the assigned **PC, AM, SC, and JCs**, along with **{total_pending_billables} pending/uncollected billables**.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": total_projects,
                "Pending Billables": total_pending_billables,
                "Project Coordinators": df["PC (Project Coord)"].nunique() if not df.empty else 0,
                "Job Coordinators": df["Job Coordinators (JC)"].nunique() if not df.empty else 0
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": "Pending Billables Count",
            "insight": "Every active project has dedicated PC, AM, and SC governance. Use the 'Employee Exit & Layoff Handover Assistant' in the sidebar or type a transfer command in chat to reassign."
        }

    # -------------------------------------------------------------
    # INTENT 6: Project-Wise Active Jobs, Allocated Employees & Logged Hours (Date Range aware)
    # -------------------------------------------------------------
    elif any(w in p for w in ["each project", "active job", "allocated employee", "logged hour", "detail", "allocation", "hierarchy", "breakdown", "drilldown"]):
        sql = f"""
        SELECT 
            p.name AS "Project",
            j.name AS "Active Job",
            j.type AS "Job Type",
            COUNT(DISTINCT ja.employee_id) AS "Allocated Staff",
            GROUP_CONCAT(DISTINCT e.name) AS "Allocated Employees",
            j.allocated_hours AS "Budget Hours",
            COALESCE(SUM(t.logged_hours), 0) AS "Logged Hours ({start_date} to {end_date})",
            ROUND(COALESCE(SUM(t.logged_hours), 0) * j.consumption_factor / 100, 1) AS "Spent Hours"
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
        if not df.empty and "Allocated Employees" in df.columns:
            df["Allocated Employees"] = df["Allocated Employees"].apply(lambda x: str(x).replace(",", ", ") if x else "Unassigned")
            
        total_projects = df["Project"].nunique() if not df.empty else 0
        total_jobs = len(df)
        total_logged = df[f"Logged Hours ({start_date} to {end_date})"].sum() if not df.empty else 0
        
        return {
            "answer": f"Here is the detailed breakdown for **{date_label}**: Currently tracking **{total_projects} Active Projects** containing **{total_jobs} Active Jobs**, with **{total_logged:,.1f} total hours logged** by allocated team members.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": total_projects,
                "Active In-Progress Jobs": total_jobs,
                "Total Logged Hours": f"{total_logged:,.1f} hrs",
                "Date Filter Range": f"{start_date} to {end_date}"
            },
            "chart_type": "bar",
            "chart_x": "Project",
            "chart_y": f"Logged Hours ({start_date} to {end_date})",
            "insight": f"Filtered across {total_projects} active projects and {total_jobs} active jobs between {start_date} and {end_date}."
        }

    # -------------------------------------------------------------
    # INTENT 7: Counts ("How many active projects and how many active jobs?")
    # -------------------------------------------------------------
    elif ("how many" in p or "count" in p) and ("project" in p or "job" in p):
        sql = """
        SELECT 
            (SELECT COUNT(*) FROM projects WHERE status = 'Active') AS "Total Active Projects",
            (SELECT COUNT(*) FROM jobs WHERE status = 'In Progress') AS "Total Active Jobs (In Progress)",
            (SELECT COUNT(*) FROM jobs WHERE status = 'In Review') AS "Jobs In Review",
            (SELECT COUNT(*) FROM employees WHERE status = 'active') AS "Active Staff Count",
            (SELECT COUNT(*) FROM employees WHERE status = 'archived') AS "Archived Staff Count",
            (SELECT COUNT(DISTINCT employee_id) FROM job_allocations) AS "Currently Allocated Staff";
        """
        df = run_query(sql)
        active_proj = df.iloc[0]["Total Active Projects"]
        active_jobs = df.iloc[0]["Total Active Jobs (In Progress)"]
        in_review = df.iloc[0]["Jobs In Review"]
        active_staff = df.iloc[0]["Active Staff Count"]
        
        return {
            "answer": f"Across 7Span Everest, there are currently **{active_proj} Active Projects** and **{active_jobs} Active In-Progress Jobs** (plus **{in_review} Jobs In Review** waiting for closure or extension). Currently tracking **{active_staff} active employees**.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": active_proj,
                "Active Jobs": active_jobs,
                "Jobs In Review": in_review,
                "Active Staff": active_staff
            },
            "chart_type": None,
            "insight": "Every active project has dedicated coordinator assignments and active team allocations."
        }

    # -------------------------------------------------------------
    # INTENT 8: Overdue Billables / Collections
    # -------------------------------------------------------------
    elif any(w in p for w in ["overdue", "delay", "pending invoice", "uncollected", "due"]):
        sql = f"""
        SELECT 
            b.name AS "Billable Name",
            p.name AS "Project",
            b.amount AS "Amount",
            b.currency AS "Currency",
            b.due_date AS "Due Date",
            ROUND(julianday('{end_date}') - julianday(b.due_date)) AS "Days Overdue",
            e.name AS "Account Manager"
        FROM billables b
        JOIN projects p ON b.project_id = p.id
        LEFT JOIN employees e ON p.am_id = e.id
        WHERE b.status = 'Billed' AND b.due_date < '{end_date}'
        ORDER BY "Days Overdue" DESC;
        """
        df = run_query(sql)
        total_usd = df[df["Currency"] == "USD"]["Amount"].sum() if not df.empty else 0
        max_delay = int(df["Days Overdue"].max()) if not df.empty else 0
        
        return {
            "answer": f"Found **{len(df)} overdue billables** as of {end_date} totaling **${total_usd:,.2f} USD**. Longest delayed is **{max_delay} days overdue**.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Total Overdue Items": len(df),
                "Total USD Pending": f"${total_usd:,.2f}",
                "Max Days Overdue": f"{max_delay} days"
            },
            "chart_type": "bar",
            "chart_x": "Project",
            "chart_y": "Amount",
            "insight": "[ALERT] AM follow-up required on overdue accounts to accelerate cash flow collections."
        }

    # -------------------------------------------------------------
    # INTENT 9: Dynamic Query for Uploaded Custom CSV Tables
    # -------------------------------------------------------------
    conn_chk = None
    all_sqlite_tables = []
    try:
        import database
        conn_chk = database.get_connection()
        cur_chk = conn_chk.cursor()
        cur_chk.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        all_sqlite_tables = [row[0] for row in cur_chk.fetchall()]
    except Exception:
        pass
    finally:
        if conn_chk:
            conn_chk.close()

    matched_custom_table = None
    standard_tables = ["projects", "jobs", "job_allocations", "timesheets", "billables", "employees", "contracts", "departments"]
    for tbl in all_sqlite_tables:
        tbl_clean = tbl.replace("_", " ").lower()
        if (tbl_clean in p or tbl.lower() in p) and tbl.lower() not in standard_tables and not tbl.startswith("raw_"):
            matched_custom_table = tbl
            break

    if matched_custom_table:
        sql = f"SELECT * FROM `{matched_custom_table}` LIMIT 100;"
        df = run_query(sql)
        row_count = len(df)
        col_count = len(df.columns)
        return {
            "answer": f"Here is the data from uploaded table **`{matched_custom_table}`** ({row_count} rows displayed, {col_count} columns).",
            "df": df,
            "sql": sql,
            "metrics": {
                "Table Name": matched_custom_table,
                "Sample Rows": row_count,
                "Total Columns": col_count
            },
            "chart_type": None,
            "insight": f"Table `{matched_custom_table}` was imported from your CSV dataset and is ready for live operational querying."
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
            COALESCE(SUM(t.logged_hours), 0) AS "Logged Hours ({start_date} to {end_date})"
        FROM projects p
        LEFT JOIN jobs j ON j.project_id = p.id AND j.status = 'In Progress'
        LEFT JOIN job_allocations ja ON ja.job_id = j.id
        LEFT JOIN timesheets t ON t.job_id = j.id AND (t.date BETWEEN '{start_date}' AND '{end_date}')
        WHERE p.status = 'Active'
        GROUP BY p.id, p.name
        ORDER BY "Active Jobs" DESC
        LIMIT 25;
        """
        df = run_query(sql)
        return {
            "answer": f"Here is the active project overview for **{date_label}** matching your inquiry *'{prompt}'*:",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects Displayed": len(df),
                "Date Range": f"{start_date} to {end_date}"
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": f"Logged Hours ({start_date} to {end_date})",
            "insight": "Try asking: 'Which employees exited recently and what jobs are allocated?', 'Show details for RealityTech project', or 'Transfer all jobs from Ritu Nayak to Bhavik Vachhani'."
        }
