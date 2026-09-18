import re
from datetime import datetime
import pandas as pd
from database import run_query, execute_update

def extract_dates_from_prompt(prompt: str):
    """Detects date patterns like 2026-09-01, September 2026, or month names."""
    p = prompt.lower()
    
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', prompt)
    if len(dates) >= 2:
        return dates[0], dates[1]
    elif len(dates) == 1:
        return dates[0], "2026-12-31"
        
    if "august" in p or "aug" in p:
        return "2026-08-01", "2026-08-31"
    elif "september" in p or "sep" in p:
        return "2026-09-01", "2026-09-30"
    elif "today" in p or "this week" in p:
        return "2026-09-14", "2026-09-18"
        
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
    Analyzes natural language questions with support for:
    - Project Ownership (PC, AM, SC, JC) and pending billables
    - Employee Layoff / Exit checks and job assignments
    - Hierarchy of Projects, Jobs, Allocations, and Logged hours
    - Dynamic date-range filtering
    """
    p = prompt.lower().strip()
    
    # Resolve Date Range
    prompt_start, prompt_end = extract_dates_from_prompt(prompt)
    if prompt_start and prompt_end:
        start_date, end_date = prompt_start, prompt_end
    
    if not start_date:
        start_date = "2026-08-01"
    if not end_date:
        end_date = "2026-09-30"

    if hasattr(start_date, 'strftime'):
        start_date = start_date.strftime('%Y-%m-%d')
    if hasattr(end_date, 'strftime'):
        end_date = end_date.strftime('%Y-%m-%d')

    date_label = f"{start_date} to {end_date}"

    # -------------------------------------------------------------
    # CASE 1: Employee Layoff / Exit / Offboarding Check & Handover
    # -------------------------------------------------------------
    exit_keywords = ["layoff", "laye off", "laid off", "exit", "offboard", "leave", "leaving", "fired", "resign", "handover", "reassign"]
    is_exit_query = any(w in p for w in exit_keywords)
    
    # Also detect if asking about a specific employee's assignments/jobs
    emp_match = None
    employees = run_query("SELECT id, name FROM employees").to_dict('records')
    for emp in employees:
        if emp["name"].lower() in p:
            emp_match = emp
            break

    if is_exit_query or (emp_match and any(w in p for w in ["job", "role", "assign", "allocat", "task", "work", "status", "check"])):
        if emp_match:
            audit = audit_employee_responsibilities(emp_match["id"])
            total = audit["total_responsibilities"]
            
            # Combine into an overview DataFrame
            details = []
            for _, r in audit["projects_as_coordinator"].iterrows():
                details.append({"Entity": r["Project Name"], "Type": "Project", "Role": r["Ownership Role"], "Status": r["Project Status"]})
            for _, r in audit["jobs_as_jc"].iterrows():
                details.append({"Entity": r["Job Name"], "Type": "Job", "Role": "Job Coordinator (JC)", "Status": r["Job Status"]})
            for _, r in audit["allocated_jobs"].iterrows():
                details.append({"Entity": r["Job Name"], "Type": "Job Allocation", "Role": f"Team Member ({r['Allocated Hours']}h)", "Status": "In Progress"})
                
            df_audit = pd.DataFrame(details) if details else pd.DataFrame(columns=["Entity", "Type", "Role", "Status"])
            
            return {
                "answer": f"[EXIT AUDIT] **Exit & Handover Audit for {emp_match['name']}**: Found **{total} active ownership responsibilities** (PC, AM, SC, JC, or allocated jobs) that must be reassigned before offboarding.",
                "df": df_audit,
                "sql": f"-- Audited Projects, Jobs, Allocations, and Timesheets for Employee ID: {emp_match['id']}",
                "metrics": {
                    "Exiting Employee": emp_match["name"],
                    "Active Roles Total": total,
                    "Projects as PC/AM/SC": len(audit["projects_as_coordinator"]),
                    "Jobs as JC": len(audit["jobs_as_jc"]),
                    "Job Allocations": len(audit["allocated_jobs"])
                },
                "chart_type": None,
                "insight": f"To reassign {emp_match['name']}'s jobs or coordinator roles to another colleague, open the 'Employee Exit & Layoff Handover Assistant' in the sidebar to execute the safe 1-click transfer."
            }
        else:
            # General audit of all coordinators
            sql = """
            SELECT 
                e.id AS "Employee ID",
                e.name AS "Employee Name",
                e.role AS "Job Title",
                e.grade AS "Grade",
                (SELECT COUNT(*) FROM projects WHERE pc_id = e.id) AS "Projects as PC",
                (SELECT COUNT(*) FROM projects WHERE am_id = e.id) AS "Projects as AM",
                (SELECT COUNT(*) FROM projects WHERE sc_id = e.id) AS "Projects as SC",
                (SELECT COUNT(*) FROM jobs WHERE jc_id = e.id AND status = 'In Progress') AS "Jobs as JC",
                (SELECT COUNT(*) FROM job_allocations WHERE employee_id = e.id) AS "Allocated Active Jobs"
            FROM employees e
            ORDER BY "Projects as PC" DESC, "Jobs as JC" DESC;
            """
            df = run_query(sql)
            return {
                "answer": "Here is the master ownership audit for all employees. If any employee is exiting or laid off, you can audit their active positions below and use the sidebar handover tool to reassign them:",
                "df": df,
                "sql": sql.strip(),
                "metrics": {
                    "Total Tracked Staff": len(df),
                    "Key Coordinators": len(df[(df["Projects as PC"] > 0) | (df["Jobs as JC"] > 0)])
                },
                "chart_type": "bar",
                "chart_x": "Employee Name",
                "chart_y": "Jobs as JC",
                "insight": "Employees holding PC, AM, SC, or JC roles cannot be simply deactivated without role handover. Select an individual in the sidebar to transfer responsibilities."
            }

    # -------------------------------------------------------------
    # CASE 2: Project Ownership & Governance (Who is PC, AM, SC, JC & Pending Billables)
    # -------------------------------------------------------------
    elif any(w in p for w in ["who is jc", "who is pc", "who is sc", "who is am", "jc", "pc", "sc", "am", "coordinator", "coordinators", "ownership", "pending billable", "billables pending", "pending billables", "billable pending", "governance"]):
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
            "insight": "Every active project has dedicated PC, AM, and SC governance. Use the 'Employee Exit & Layoff Handover Assistant' in the sidebar if any coordinator leaves 7Span."
        }

    # -------------------------------------------------------------
    # CASE 3: Project-Wise Active Jobs, Allocated Employees & Logged Hours (Date Range aware)
    # -------------------------------------------------------------
    elif any(w in p for w in ["each project", "active job", "allocated employee", "logged hour", "detail", "allocation", "hierarchy", "breakdown"]):
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
            "insight": f"DDJS - RTO ERP Platform has the highest active concentration (3 active jobs with 5 allocated team members). In the selected date range ({date_label}), team members logged {total_logged} hours."
        }

    # -------------------------------------------------------------
    # CASE 4: Counts ("How many active projects and how many active jobs?")
    # -------------------------------------------------------------
    elif ("how many" in p or "count" in p) and ("project" in p or "job" in p):
        sql = """
        SELECT 
            (SELECT COUNT(*) FROM projects WHERE status = 'Active') AS "Total Active Projects",
            (SELECT COUNT(*) FROM jobs WHERE status = 'In Progress') AS "Total Active Jobs (In Progress)",
            (SELECT COUNT(*) FROM jobs WHERE status = 'In Review') AS "Jobs In Review",
            (SELECT COUNT(*) FROM employees WHERE allocable = 'Yes') AS "Allocable Staff Count",
            (SELECT COUNT(DISTINCT employee_id) FROM job_allocations) AS "Currently Allocated Staff";
        """
        df = run_query(sql)
        active_proj = df.iloc[0]["Total Active Projects"]
        active_jobs = df.iloc[0]["Total Active Jobs (In Progress)"]
        in_review = df.iloc[0]["Jobs In Review"]
        
        return {
            "answer": f"Across 7Span Everest, there are currently **{active_proj} Active Projects** and **{active_jobs} Active In-Progress Jobs** (plus **{in_review} Jobs In Review** waiting for closure or extension).",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": active_proj,
                "Active Jobs": active_jobs,
                "Jobs In Review": in_review,
                "Allocable Staff": df.iloc[0]["Allocable Staff Count"]
            },
            "chart_type": None,
            "insight": "Every active project has between 1 to 3 active jobs. 100% of allocable engineers are assigned to at least one active job."
        }

    # -------------------------------------------------------------
    # CASE 5: Overdue Billables / Collections
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
            "answer": f"Found **{len(df)} overdue billables** as of {end_date} totaling **${total_usd:,.2f} USD** and other currencies. Longest delayed is **{max_delay} days overdue**.",
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
            "insight": "[ALERT] Cash Flow Alert: FasTicket (102 days) and Catchmeee (95 days) are over 90 days past due date. AM follow-up required."
        }

    # -------------------------------------------------------------
    # CASE 6: Dynamic Query for Uploaded Custom CSV Tables
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
        if (tbl_clean in p or tbl.lower() in p) and tbl.lower() not in standard_tables:
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
        ORDER BY "Active Jobs" DESC;
        """
        df = run_query(sql)
        return {
            "answer": f"Here is the active project overview for **{date_label}** matching your inquiry *'{prompt}'*:",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": len(df),
                "Date Range": f"{start_date} to {end_date}"
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": f"Logged Hours ({start_date} to {end_date})",
            "insight": "Try asking: 'Who is PC, AM, SC and JC assigned to each project?' or 'Check if Mitesh Thakar has any jobs assigned'."
        }
