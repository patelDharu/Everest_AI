import sqlite3
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_PATHS = [
    os.path.join(SCRIPT_DIR, "everest_dummy.db"),
    os.path.join(SCRIPT_DIR, "..", "everest_dummy.db"),
    r"C:\Users\hp\.gemini\antigravity\scratch\everest_dummy.db",
    r"C:\Users\hp\.gemini\antigravity\scratch\capture_everest_sidebar\everest_dummy.db",
    "everest_dummy.db"
]

DB_PATH = None
for p in POSSIBLE_PATHS:
    if os.path.exists(p):
        DB_PATH = os.path.abspath(p)
        break

def get_connection():
    if not DB_PATH or not os.path.exists(DB_PATH):
        print(f"Error: Database file 'everest_dummy.db' not found.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def format_table(headers, rows):
    if not rows:
        return "No records found."
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val) if val is not None else ""))
    
    header_str = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * widths[i] for i in range(len(headers)))
    row_strs = [" | ".join(f"{str(v if v is not None else ''):<{widths[i]}}" for i, v in enumerate(row)) for row in rows]
    return f"{header_str}\n{sep_str}\n" + "\n".join(row_strs)

def execute_query(sql, description=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        print("\n" + "=" * 60)
        print(f"SQL EXECUTED: {sql}")
        print("=" * 60)
        print(format_table(headers, rows))
        print("=" * 60)
        if description:
            print(f"AI INSIGHT: {description}\n")
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        conn.close()

def handle_question(q):
    q_lower = q.lower()
    
    # 1. Overdue billables / invoices
    if "overdue" in q_lower or "due" in q_lower or "delay" in q_lower:
        sql = """
        SELECT 
            b.name AS Billable,
            p.name AS Project,
            b.amount AS Amount,
            b.currency AS Currency,
            b.due_date AS Due_Date,
            ROUND(julianday('2026-09-18') - julianday(b.due_date)) AS Days_Overdue,
            e.name AS AM_Name
        FROM billables b
        JOIN projects p ON b.project_id = p.id
        LEFT JOIN employees e ON p.am_id = e.id
        WHERE b.status = 'Billed' AND b.due_date < '2026-09-18'
        ORDER BY Days_Overdue DESC;
        """
        desc = "FasTicket and Catchmeee have significant overdue balances exceeding 90+ days. Follow up with AM Mitesh Thakar."
        execute_query(sql, desc)
    
    # 2. Unreviewed timesheets / backlog
    elif "unreview" in q_lower or "review" in q_lower or "backlog" in q_lower or "pending time" in q_lower:
        sql = """
        SELECT 
            e.name AS Employee,
            d.name AS Department_Pod,
            COUNT(t.id) AS Log_Count,
            SUM(t.logged_hours) AS Total_Unreviewed_Hours
        FROM timesheets t
        JOIN employees e ON t.employee_id = e.id
        JOIN departments d ON e.department_id = d.id
        WHERE t.status = 'Unreviewed'
        GROUP BY e.name, d.name
        ORDER BY Total_Unreviewed_Hours DESC;
        """
        desc = "Bhavik Maradiya (Dash) and Jay Patel (Air) have over 55+ unreviewed hours each. Reviewers must approve these to restore utilization metrics."
        execute_query(sql, desc)
        
    # 3. Project allocations / employees per project
    elif "project" in q_lower and ("employee" in q_lower or "allocat" in q_lower or "team" in q_lower):
        sql = """
        SELECT 
            p.name AS Project,
            p.client_name AS Client,
            p.status AS Status,
            COUNT(j.id) AS Total_Jobs,
            SUM(j.allocated_hours) AS Total_Allocated_Hours,
            e.name AS Project_Coordinator
        FROM projects p
        LEFT JOIN jobs j ON j.project_id = p.id
        LEFT JOIN employees e ON p.pc_id = e.id
        GROUP BY p.id, p.name;
        """
        desc = "Shows active projects with total jobs and allocated hours under PC Nikhil Sharma."
        execute_query(sql, desc)

    # 4. Department / Pod list or utilization
    elif "pod" in q_lower or "department" in q_lower:
        sql = """
        SELECT 
            d.name AS Pod_Name,
            COUNT(e.id) AS Total_Employees,
            GROUP_CONCAT(e.name, ', ') AS Team_Members
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id
        GROUP BY d.id, d.name;
        """
        desc = "7Span pods breakdown: Neo, Ark, Air, Dash, Flex, Bolt, Strike."
        execute_query(sql, desc)

    # 5. General Revenue
    elif "revenue" in q_lower or "collected" in q_lower or "billable" in q_lower:
        sql = """
        SELECT 
            b.currency AS Currency,
            b.status AS Stage,
            COUNT(*) AS Count,
            SUM(b.amount) AS Total_Amount
        FROM billables b
        GROUP BY b.currency, b.status;
        """
        desc = "Summary of billables across Contracted, Billed, and Collected stages in INR, USD, and NZD."
        execute_query(sql, desc)

    # Default fallback: Show all projects
    else:
        sql = "SELECT id, name, client_name, status, created_date FROM projects LIMIT 10;"
        desc = f"Showing active projects matching your inquiry '{q}'."
        execute_query(sql, desc)

def main():
    print("\n" + "=" * 60)
    print("🤖 EVEREST 360° AI ORACLE (Interactive CLI)")
    print("=" * 60)
    print("Ask any question about Everest in plain English or Hinglish!")
    print("Sample questions you can try:")
    print("  1. 'Show me all overdue billables and who the AM is'")
    print("  2. 'Which employees have unreviewed hours?'")
    print("  3. 'List all projects, clients, and allocated hours'")
    print("  4. 'Show me our department pods and team members'")
    print("  5. 'What is our total revenue collected vs billed?'")
    print("Type 'exit' or 'quit' to close.\n")
    
    while True:
        try:
            user_input = input("❓ Ask Everest AI > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            handle_question(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
