# -*- coding: utf-8 -*-
"""
Everest AI - Production CSV Ingestion & Normalization Pipeline
Ingests all real CSV files from D:\everest_data_zip into SQLite with relational joins and indexes.
"""
import os
import sys
import time
import sqlite3
import pandas as pd

SRC_FOLDER = r"D:\everest_data_zip"
TARGET_DB = r"D:\Everest-AI\everest_dummy.db"  # Primary database used by app.py

def clean_name(first, last):
    f = str(first).strip() if pd.notna(first) else ""
    l = str(last).strip() if pd.notna(last) else ""
    full = f"{f} {l}".strip()
    return full if full else "Unknown"

def sync_data():
    print("=" * 65)
    print(f"   Everest AI - Syncing Real Data from: {SRC_FOLDER}")
    print("=" * 65)

    if not os.path.exists(SRC_FOLDER):
        print(f"Error: Source directory {SRC_FOLDER} does not exist.")
        return False

    t_start = time.time()
    conn = sqlite3.connect(TARGET_DB)

    print("1. Ingesting Raw Core Entities...")
    
    # Core tables
    core_csvs = [
        "employees.csv", "projects.csv", "jobs.csv", "jobs_employees.csv",
        "billables.csv", "clients.csv", "contracts.csv"
    ]
    
    for c in core_csvs:
        p = os.path.join(SRC_FOLDER, c)
        if os.path.exists(p):
            tbl = c.replace(".csv", "")
            df = pd.read_csv(p, low_memory=False)
            df.to_sql(f"raw_{tbl}", conn, if_exists="replace", index=False)
            print(f"   - Loaded raw_{tbl}: {len(df):,} records")

    # Ingest timesheets (can be large)
    ts_path = os.path.join(SRC_FOLDER, "timesheet.csv")
    if os.path.exists(ts_path):
        print("   - Loading timesheet.csv (this might take a few seconds)...")
        df_ts = pd.read_csv(ts_path, low_memory=False)
        df_ts.to_sql("raw_timesheet", conn, if_exists="replace", index=False)
        print(f"   - Loaded raw_timesheet: {len(df_ts):,} records")

    print("\n2. Building Unified & Denormalized Operational Views/Tables...")

    # Load into memory for clean relational mapping
    df_emp = pd.read_sql("SELECT * FROM raw_employees", conn)
    df_proj = pd.read_sql("SELECT * FROM raw_projects", conn)
    df_job = pd.read_sql("SELECT * FROM raw_jobs", conn)
    df_je = pd.read_sql("SELECT * FROM raw_jobs_employees", conn)
    df_cli = pd.read_sql("SELECT * FROM raw_clients", conn)
    df_bill = pd.read_sql("SELECT * FROM raw_billables", conn)

    # Name lookups
    emp_lookup = {}
    for _, r in df_emp.iterrows():
        emp_lookup[str(r["id"])] = clean_name(r.get("first_name"), r.get("last_name"))

    client_lookup = {}
    for _, r in df_cli.iterrows():
        client_lookup[str(r["id"])] = str(r.get("name") or "Unknown Client").strip()

    proj_lookup = {}
    for _, r in df_proj.iterrows():
        proj_lookup[str(r["id"])] = str(r.get("name") or "Unknown Project").strip()

    job_lookup = {}
    for _, r in df_job.iterrows():
        job_lookup[str(r["id"])] = str(r.get("name") or "Unknown Job").strip()

    # 1. Normalized Employees
    df_emp_clean = pd.DataFrame({
        "id": df_emp["id"],
        "name": [clean_name(r.get("first_name"), r.get("last_name")) for _, r in df_emp.iterrows()],
        "email": df_emp.get("email", ""),
        "role": df_emp.get("title", df_emp.get("role", "Engineer")),
        "department": df_emp.get("department", "Engineering"),
        "grade": df_emp.get("grade", "A0"),
        "status": df_emp.get("status", "active"),
        "allocable": df_emp.get("allocable", 1)
    })
    df_emp_clean.to_sql("employees", conn, if_exists="replace", index=False)
    print(f"   [OK] Table 'employees' ready: {len(df_emp_clean):,} employees")

    # 2. Normalized Projects
    df_proj_clean = pd.DataFrame({
        "id": df_proj["id"],
        "name": df_proj["name"],
        "status": df_proj["status"].apply(lambda s: "Active" if str(s).lower() == "active" else "Inactive"),
        "client_name": [client_lookup.get(str(cid), "Direct Client") for cid in df_proj.get("client")],
        "pc_id": df_proj.get("coordinator"),
        "am_id": df_proj.get("account_manager"),
        "sc_id": df_proj.get("sales_coordinator")
    })
    df_proj_clean.to_sql("projects", conn, if_exists="replace", index=False)
    print(f"   [OK] Table 'projects' ready: {len(df_proj_clean):,} projects")

    # 3. Normalized Jobs
    def map_job_status(st):
        s = str(st).lower()
        if s in ["in_progress", "in progress"]:
            return "In Progress"
        elif s in ["in_review", "in review"]:
            return "In Review"
        elif s in ["backlog"]:
            return "Backlog"
        elif s in ["closed", "completed"]:
            return "Closed"
        return "In Progress"

    df_job_clean = pd.DataFrame({
        "id": df_job["id"],
        "project_id": df_job.get("project"),
        "name": df_job["name"],
        "type": df_job.get("type", "dedicated"),
        "status": df_job.get("status").apply(map_job_status),
        "jc_id": df_job.get("coordinator"),
        "allocated_hours": 160.0,
        "consumption_factor": 100
    })
    df_job_clean.to_sql("jobs", conn, if_exists="replace", index=False)
    print(f"   [OK] Table 'jobs' ready: {len(df_job_clean):,} jobs")

    # 4. Normalized Job Allocations
    df_je_clean = pd.DataFrame({
        "id": df_je.get("id"),
        "job_id": df_je.get("job"),
        "employee_id": df_je.get("employee"),
        "allocated_hours": 160.0,
        "is_shadow": df_je.get("is_shadow", 0)
    })
    df_je_clean.to_sql("job_allocations", conn, if_exists="replace", index=False)
    print(f"   [OK] Table 'job_allocations' ready: {len(df_je_clean):,} allocations")

    # 5. Normalized Billables
    def map_bill_status(st):
        s = str(st).lower()
        if s in ["billed", "paid"]:
            return "Billed"
        elif s in ["pending", "invoiced", "pending_invoice"]:
            return "Pending Invoice"
        elif s in ["contracted"]:
            return "Contracted"
        elif s in ["cancelled"]:
            return "Cancelled"
        return "Billed"

    # Map job to project
    job_to_proj = dict(zip(df_job["id"].astype(str), df_job["project"].astype(str)))
    df_bill_clean = pd.DataFrame({
        "id": df_bill.get("id"),
        "project_id": [job_to_proj.get(str(jid), None) for jid in df_bill.get("job")],
        "name": df_bill.get("name", "Milestone Invoice"),
        "amount": pd.to_numeric(df_bill.get("amount", 0), errors="coerce").fillna(0),
        "currency": "USD",
        "status": df_bill.get("status").apply(map_bill_status),
        "due_date": df_bill.get("due_date", "2026-09-30")
    })
    df_bill_clean.to_sql("billables", conn, if_exists="replace", index=False)
    print(f"   [OK] Table 'billables' ready: {len(df_bill_clean):,} billable items")

    # 6. Normalized Timesheets
    if os.path.exists(ts_path):
        df_ts_clean = pd.DataFrame({
            "id": df_ts.get("id"),
            "job_id": df_ts.get("job"),
            "employee_id": df_ts.get("employee"),
            "date": df_ts.get("date"),
            "logged_hours": pd.to_numeric(df_ts.get("logged_hours", 0), errors="coerce").fillna(0),
            "approved_hours": pd.to_numeric(df_ts.get("approved_hours", 0), errors="coerce").fillna(0),
            "status": df_ts.get("status", "Approved")
        })
        df_ts_clean.to_sql("timesheets", conn, if_exists="replace", index=False)
        print(f"   [OK] Table 'timesheets' ready: {len(df_ts_clean):,} timesheets")

    # 7. Create fast indexes
    print("\n3. Creating Query Acceleration Indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_p_status ON projects(status);",
        "CREATE INDEX IF NOT EXISTS idx_j_status ON jobs(status);",
        "CREATE INDEX IF NOT EXISTS idx_j_proj ON jobs(project_id);",
        "CREATE INDEX IF NOT EXISTS idx_ja_job ON job_allocations(job_id);",
        "CREATE INDEX IF NOT EXISTS idx_ja_emp ON job_allocations(employee_id);",
        "CREATE INDEX IF NOT EXISTS idx_ts_date ON timesheets(date);",
        "CREATE INDEX IF NOT EXISTS idx_ts_job ON timesheets(job_id);",
        "CREATE INDEX IF NOT EXISTS idx_ts_emp ON timesheets(employee_id);",
        "CREATE INDEX IF NOT EXISTS idx_b_proj ON billables(project_id);",
        "CREATE INDEX IF NOT EXISTS idx_b_status ON billables(status);"
    ]
    for idx_sql in indexes:
        try:
            conn.execute(idx_sql)
        except Exception:
            pass

    conn.commit()
    conn.close()

    elapsed = time.time() - t_start
    print("\n" + "=" * 65)
    print(f"   Real Everest Data Synced Successfully in {elapsed:.2f}s!")
    print(f"   Database: {TARGET_DB}")
    print("=" * 65)
    return True

if __name__ == "__main__":
    sync_data()
