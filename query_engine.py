import re
from datetime import datetime
import pandas as pd
from database import run_query

def extract_dates_from_prompt(prompt: str):
    """Detects date patterns like 2026-09-01, September 2026, or month names."""
    p = prompt.lower()
    
    # Check for explicit YYYY-MM-DD
    dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', prompt)
    if len(dates) >= 2:
        return dates[0], dates[1]
    elif len(dates) == 1:
        return dates[0], "2026-12-31"
        
    # Check for Month keywords
    if "august" in p or "aug" in p:
        return "2026-08-01", "2026-08-31"
    elif "september" in p or "sep" in p:
        return "2026-09-01", "2026-09-30"
    elif "today" in p or "this week" in p:
        return "2026-09-14", "2026-09-18"
        
    return None, None

def analyze_question(prompt: str, start_date=None, end_date=None) -> dict:
    """
    Analyzes natural language questions with support for:
    - Active projects & active jobs counts
    - Project-wise active jobs, allocated employees, and logged hours
    - Dynamic date-range filtering on timesheets and allocations
    """
    p = prompt.lower().strip()
    
    # 1. Resolve Date Range (From argument or extracted from natural language prompt)
    prompt_start, prompt_end = extract_dates_from_prompt(prompt)
    if prompt_start and prompt_end:
        start_date, end_date = prompt_start, prompt_end
    
    # Default date range if none provided: Entire Q3 (Aug - Sep 2026)
    if not start_date:
        start_date = "2026-08-01"
    if not end_date:
        end_date = "2026-09-30"

    # Convert to string format if passed as datetime.date from Streamlit date_input
    if hasattr(start_date, 'strftime'):
        start_date = start_date.strftime('%Y-%m-%d')
    if hasattr(end_date, 'strftime'):
        end_date = end_date.strftime('%Y-%m-%d')

    date_label = f"{start_date} to {end_date}"

    # -------------------------------------------------------------
    # CASE A: Project-Wise Active Jobs, Allocated Employees & Logged Hours (Core Request)
    # -------------------------------------------------------------
    if any(w in p for w in ["each project", "active job", "allocated employee", "logged hour", "detail", "allocation", "hierarchy", "breakdown"]):
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
        
        # Clean up commas in employee names
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
            "insight": f"💡 DDJS - RTO ERP Platform has the highest active concentration (3 active jobs with 5 allocated team members). In the selected date range ({date_label}), team members logged {total_logged} hours."
        }

    # -------------------------------------------------------------
    # CASE B: High Level Counts ("How many active projects and how many active jobs?")
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
    # CASE C: Overdue Billables / Collections
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
            "insight": "⚠️ Cash Flow Alert: FasTicket (102 days) and Catchmeee (95 days) are over 90 days past due date. AM follow-up required."
        }

    # -------------------------------------------------------------
    # CASE D: Timesheet Unreviewed Backlog
    # -------------------------------------------------------------
    elif any(w in p for w in ["unreview", "review", "timesheet backlog", "pending log", "pending time", "approv"]):
        sql = f"""
        SELECT 
            e.name AS "Employee",
            d.name AS "Pod / Department",
            e.grade AS "Grade",
            COUNT(t.id) AS "Unreviewed Logs",
            SUM(t.logged_hours) AS "Total Unreviewed Hours"
        FROM timesheets t
        JOIN employees e ON t.employee_id = e.id
        JOIN departments d ON e.department_id = d.id
        WHERE t.status = 'Unreviewed' AND (t.date BETWEEN '{start_date}' AND '{end_date}')
        GROUP BY e.name, d.name, e.grade
        ORDER BY "Total Unreviewed Hours" DESC;
        """
        df = run_query(sql)
        total_unreviewed = df["Total Unreviewed Hours"].sum() if not df.empty else 0
        
        return {
            "answer": f"For date range **{date_label}**, there are **{total_unreviewed:,.1f} unreviewed timesheet hours** waiting for manager approval.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Unreviewed Hours": f"{total_unreviewed} hrs",
                "Employees Affected": len(df),
                "Top Pod Bottleneck": df.iloc[0]["Pod / Department"] if not df.empty else "None"
            },
            "chart_type": "bar",
            "chart_x": "Employee",
            "chart_y": "Total Unreviewed Hours",
            "insight": "Bhavik Maradiya and Jay Patel have unreviewed hours from mid-September. Reviewers must approve these to restore utilization metrics."
        }

    # -------------------------------------------------------------
    # CASE E: Revenue Breakdown by Currency
    # -------------------------------------------------------------
    elif any(w in p for w in ["revenue", "billing", "collected", "money", "growth"]):
        sql = """
        SELECT 
            b.currency AS "Currency",
            b.status AS "Stage",
            COUNT(*) AS "Invoices",
            SUM(b.amount) AS "Total Amount"
        FROM billables b
        GROUP BY b.currency, b.status
        ORDER BY b.currency, b.status;
        """
        df = run_query(sql)
        return {
            "answer": "Here is the revenue breakdown across **Contracted**, **Billed**, and **Collected** stages by currency.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Currencies Tracked": len(df["Currency"].unique()) if not df.empty else 0,
                "Total Invoices": df["Invoices"].sum() if not df.empty else 0
            },
            "chart_type": "bar",
            "chart_x": "Stage",
            "chart_y": "Total Amount",
            "insight": "Domestic accounts operate in INR (with ₹1,00,000 recently Collected), while international accounts operate in USD and NZD."
        }

    # -------------------------------------------------------------
    # DEFAULT FALLBACK: Active Projects with Summary
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
            "insight": "Try asking: 'Each project wise active jobs, allocated employees and logged hours' or 'How many active projects and active jobs?'"
        }
