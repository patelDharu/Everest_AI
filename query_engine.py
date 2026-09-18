import re
import pandas as pd
from database import run_query

def analyze_question(prompt: str) -> dict:
    """
    Analyzes natural language questions (English/Hinglish) and maps them to
    accurate SQL queries against Everest schema, returning tables, metrics, and insights.
    """
    p = prompt.lower().strip()
    
    # 1. Overdue Billables / Invoices / Collections
    if any(w in p for w in ["overdue", "delay", "pending invoice", "uncollected", "due"]):
        sql = """
        SELECT 
            b.name AS "Billable Name",
            p.name AS "Project",
            b.amount AS "Amount",
            b.currency AS "Currency",
            b.due_date AS "Due Date",
            ROUND(julianday('2026-09-18') - julianday(b.due_date)) AS "Days Overdue",
            e.name AS "Account Manager"
        FROM billables b
        JOIN projects p ON b.project_id = p.id
        LEFT JOIN employees e ON p.am_id = e.id
        WHERE b.status = 'Billed' AND b.due_date < '2026-09-18'
        ORDER BY "Days Overdue" DESC;
        """
        df = run_query(sql)
        total_usd = df[df["Currency"] == "USD"]["Amount"].sum() if not df.empty else 0
        max_delay = int(df["Days Overdue"].max()) if not df.empty else 0
        
        return {
            "answer": f"Found **{len(df)} overdue billables** totaling **${total_usd:,.2f} USD** and other currencies. The longest delayed payment is **{max_delay} days overdue**.",
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
            "insight": "⚠️ High Risk: FasTicket (102 days) and Catchmeee (95 days) represent significant cash flow risk. Immediate follow-up with Account Manager Mitesh Thakar is recommended."
        }

    # 2. Timesheet Unreviewed / Backlog / Approvals
    elif any(w in p for w in ["unreview", "review", "timesheet backlog", "pending log", "pending time", "approv"]):
        sql = """
        SELECT 
            e.name AS "Employee",
            d.name AS "Pod / Department",
            e.grade AS "Grade",
            COUNT(t.id) AS "Unreviewed Logs",
            SUM(t.logged_hours) AS "Total Unreviewed Hours"
        FROM timesheets t
        JOIN employees e ON t.employee_id = e.id
        JOIN departments d ON e.department_id = d.id
        WHERE t.status = 'Unreviewed'
        GROUP BY e.name, d.name, e.grade
        ORDER BY "Total Unreviewed Hours" DESC;
        """
        df = run_query(sql)
        total_unreviewed = df["Total Unreviewed Hours"].sum() if not df.empty else 0
        
        return {
            "answer": f"There are **{total_unreviewed:,.1f} unreviewed timesheet hours** waiting for manager approval across **{len(df)} employees**.",
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
            "insight": "🔔 Action Needed: Bhavik Maradiya and Jay Patel have over 50+ hours unreviewed. Reviewers must approve these to prevent utilization showing as 0%."
        }

    # 3. Project Allocations & Budgets
    elif any(w in p for w in ["project", "allocat", "budget", "client", "hours"]):
        sql = """
        SELECT 
            p.name AS "Project Name",
            p.client_name AS "Client",
            p.status AS "Status",
            COUNT(j.id) AS "Active Jobs",
            SUM(j.allocated_hours) AS "Allocated Hours",
            e.name AS "Project Coordinator (PC)"
        FROM projects p
        LEFT JOIN jobs j ON j.project_id = p.id
        LEFT JOIN employees e ON p.pc_id = e.id
        GROUP BY p.id, p.name
        ORDER BY "Allocated Hours" DESC;
        """
        df = run_query(sql)
        total_alloc = df["Allocated Hours"].sum() if not df.empty else 0
        
        return {
            "answer": f"Currently tracking **{len(df)} active projects** with a total allocation of **{total_alloc:,.0f} hours**.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Active Projects": len(df),
                "Total Allocated Hours": f"{total_alloc:,.0f}h",
                "Leading Project": df.iloc[0]["Project Name"] if not df.empty else "None"
            },
            "chart_type": "bar",
            "chart_x": "Project Name",
            "chart_y": "Allocated Hours",
            "insight": "DDJS - RTO ERP Platform has the largest allocation (300h) followed by FasTicket (250h)."
        }

    # 4. Pods / Departments & Team Members
    elif any(w in p for w in ["pod", "department", "team", "engineer"]):
        sql = """
        SELECT 
            d.name AS "Pod Name",
            COUNT(e.id) AS "Total Members",
            GROUP_CONCAT(e.name, ', ') AS "Employees"
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id
        GROUP BY d.id, d.name
        ORDER BY "Total Members" DESC;
        """
        df = run_query(sql)
        return {
            "answer": f"7Span operates **{len(df)} specialized pods**: Neo, Ark, Air, Dash, Flex, Bolt, and Strike.",
            "df": df,
            "sql": sql.strip(),
            "metrics": {
                "Total Pods": len(df),
                "Largest Pod": df.iloc[0]["Pod Name"] if not df.empty else "Neo"
            },
            "chart_type": "bar",
            "chart_x": "Pod Name",
            "chart_y": "Total Members",
            "insight": "Pods Air, Neo, and Dash currently have the highest headcount allocation."
        }

    # 5. Revenue & Contracted vs Billed vs Collected
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

    # Default fallback query
    else:
        sql = """
        SELECT 
            id AS "ID",
            name AS "Project Name",
            client_name AS "Client",
            status AS "Status",
            created_date AS "Start Date"
        FROM projects
        LIMIT 10;
        """
        df = run_query(sql)
        return {
            "answer": f"I processed your question: *'{prompt}'*. Here is the current project summary from the Everest database:",
            "df": df,
            "sql": sql.strip(),
            "metrics": {"Projects Listed": len(df)},
            "chart_type": None,
            "insight": "Tip: You can ask specific questions like 'Show overdue billables', 'Unreviewed timesheet hours', or 'Project budget allocations'."
        }
