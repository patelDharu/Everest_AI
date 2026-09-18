import sqlite3
import os

DB_FILE = "everest_dummy.db"
SQL_FILE = "everest_dummy.sql"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("Building Everest Dummy Database structure...")

# 1. Departments / Pods
cursor.execute("""
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
""")

# 2. Employees
cursor.execute("""
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code TEXT NOT NULL,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    role TEXT NOT NULL,
    department_id INTEGER,
    email TEXT NOT NULL,
    allocable TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);
""")

# 3. Projects
cursor.execute("""
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client_name TEXT NOT NULL,
    status TEXT NOT NULL,
    pc_id INTEGER,
    am_id INTEGER,
    sc_id INTEGER,
    created_date TEXT NOT NULL,
    FOREIGN KEY (pc_id) REFERENCES employees(id),
    FOREIGN KEY (am_id) REFERENCES employees(id),
    FOREIGN KEY (sc_id) REFERENCES employees(id)
);
""")

# 4. Contracts
cursor.execute("""
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- Fixed, Hourly, Dedicated, Bucket, Recurring
    status TEXT NOT NULL,
    project_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
""")

# 5. Jobs
cursor.execute("""
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    project_id INTEGER,
    contract_id INTEGER,
    type TEXT NOT NULL,
    status TEXT NOT NULL, -- Backlog, In Progress, In Review, Closed
    jc_id INTEGER,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    allocated_hours REAL DEFAULT 0,
    consumption_factor REAL DEFAULT 100,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (contract_id) REFERENCES contracts(id),
    FOREIGN KEY (jc_id) REFERENCES employees(id)
);
""")

# 6. Billables
cursor.execute("""
CREATE TABLE billables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    project_id INTEGER,
    job_id INTEGER,
    amount REAL NOT NULL,
    currency TEXT NOT NULL, -- INR, USD, NZD
    status TEXT NOT NULL, -- Contracted, Billed, Collected
    billing_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
""")

# 7. Timesheets
cursor.execute("""
CREATE TABLE timesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    job_id INTEGER,
    date TEXT NOT NULL,
    logged_hours REAL NOT NULL,
    approved_hours REAL DEFAULT 0,
    unapproved_hours REAL DEFAULT 0,
    status TEXT NOT NULL, -- Draft, Logged, Approved, Unreviewed
    tag TEXT NOT NULL, -- Development, Meetings, QA, Bugfix
    description TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
""")

print("Inserting realistic 7Span Everest data (Pods, Projects, Overdue Billables, Utilization)...")

# Insert Pods
pods = ['Neo', 'Ark', 'Air', 'Dash', 'Flex', 'Bolt', 'Strike']
for p in pods:
    cursor.execute("INSERT INTO departments (name) VALUES (?)", (p,))

# Insert Employees
employees = [
    (171, 'Smit Parmar', 'A0', 'Engineering', 3, 'smit.p@7span.com', 'Yes'),
    (173, 'Parth Dhameliya', 'A0', 'Engineering', 3, 'parth.d@7span.com', 'Yes'),
    (175, 'Devansh Patel', 'A0', 'Engineering', 4, 'devansh@7span.com', 'Yes'),
    (178, 'Simaran Karangiya', 'A0', 'Engineering', 3, 'simaran@7span.com', 'Yes'),
    (184, 'Bhavdip Gediya', 'A0', 'Engineering', 1, 'bhavdip@7span.com', 'Yes'),
    (191, 'Dhara Matholiya', 'A0', 'Delivery', 7, 'dhara@7span.com', 'No'),
    (201, 'Nikhil Sharma', 'Lead', 'Coordinator', 1, 'nikhil@7span.com', 'Yes'),
    (202, 'Mitesh Thakar', 'Senior', 'Coordinator', 5, 'mitesh@7span.com', 'Yes'),
    (203, 'Akshay Vadsara', 'Lead', 'Coordinator', 2, 'akshay@7span.com', 'Yes'),
    (204, 'Bhavik Maradiya', 'A0', 'Engineering', 4, 'bhavik@7span.com', 'Yes'),
    (205, 'Jay Patel', 'A0', 'Engineering', 3, 'jay.p@7span.com', 'Yes'),
]
for e in employees:
    cursor.execute("INSERT INTO employees (employee_code, name, grade, role, department_id, email, allocable) VALUES (?, ?, ?, ?, ?, ?, ?)", e)

# Insert Projects
projects = [
    ('FasTicket', 'FasTicket Inc', 'Active', 7, 8, 9, '2026-05-10'),
    ('Catchmeee', 'Catchmeee Media', 'Active', 7, 8, 9, '2026-05-01'),
    ('DDJS - RTO ERP Platform', 'DDJS Govt', 'Active', 7, 8, 9, '2026-08-15'),
    ('My Medical English', 'MME Global', 'Active', 7, 8, 9, '2026-09-01'),
    ('AccRegLab', 'AccRegLab UK', 'Active', 7, 8, 9, '2026-06-01'),
    ('Ride and Stride', 'Ride & Stride NZ', 'Active', 7, 8, 9, '2026-07-15'),
    ('Spark Solar', 'Spark Ltd', 'Active', 7, 8, 9, '2026-04-16'),
]
for p in projects:
    cursor.execute("INSERT INTO projects (name, client_name, status, pc_id, am_id, sc_id, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)", p)

# Insert Contracts
contracts = [
    ('Hourly-1', 'Hourly', 'In Progress', 1),
    ('Fixed-1', 'Fixed', 'In Progress', 2),
    ('Fixed-2', 'Fixed', 'In Progress', 3),
    ('Fixed-3', 'Fixed', 'In Progress', 4),
    ('Hourly-2', 'Hourly', 'In Progress', 5),
    ('Fixed-4', 'Fixed', 'In Progress', 6),
    ('Recurring-1', 'Recurring', 'In Progress', 7),
]
for c in contracts:
    cursor.execute("INSERT INTO contracts (name, type, status, project_id) VALUES (?, ?, ?, ?)", c)

# Insert Jobs
jobs = [
    ('1.0 - Feature Development', 1, 1, 'Hourly', 'In Progress', 8, '2026-05-15', '2026-10-30', 250, 100),
    ('Design & BA Phase', 2, 2, 'Fixed', 'In Progress', 8, '2026-05-05', '2026-09-30', 120, 100),
    ('Discovery & SRS Finalisation', 3, 3, 'Fixed', 'In Progress', 7, '2026-08-20', '2026-11-15', 300, 100),
    ('Core Web Portal Support', 4, 4, 'Fixed', 'In Progress', 7, '2026-09-01', '2026-12-15', 180, 100),
    ('Development - Jun 26', 5, 5, 'Hourly', 'In Progress', 8, '2026-06-01', '2026-10-15', 200, 100),
    ('Ride Phase 1 MVP', 6, 6, 'Fixed', 'In Progress', 9, '2026-07-20', '2026-10-31', 150, 100),
    ('Website AMC & Support', 7, 7, 'Recurring', 'In Progress', 7, '2026-04-16', '2026-12-31', 100, 100),
]
for j in jobs:
    cursor.execute("INSERT INTO jobs (name, project_id, contract_id, type, status, jc_id, start_date, end_date, allocated_hours, consumption_factor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", j)

# Insert Billables (Including the Overdue ones from your screenshot!)
billables = [
    ('FasTicket - Feature Dev 1.1', 1, 1, 720, 'USD', 'Billed', '2026-06-01', '2026-06-08'), # 102 days overdue
    ('Catchmeee - Design Phase', 2, 2, 800, 'USD', 'Billed', '2026-06-08', '2026-06-15'),   # 95 days overdue
    ('AccRegLab - Jun Dev Week 4', 5, 5, 101, 'USD', 'Billed', '2026-06-30', '2026-07-07'),  # 73 days overdue
    ('AccRegLab - Asia Cup SRS', 5, 5, 300, 'USD', 'Billed', '2026-06-30', '2026-07-07'),    # 73 days overdue
    ('Ride and Stride - Phase 1', 6, 6, 3440, 'NZD', 'Billed', '2026-08-31', '2026-09-07'),  # 11 days overdue
    ('DDJS - SRS Sign-off Milestone', 3, 3, 62500, 'INR', 'Contracted', '2026-10-15', '2026-10-22'),
    ('DDJS - Discovery Kickoff', 3, 3, 100000, 'INR', 'Collected', '2026-09-14', '2026-09-21'),
    ('My Medical English - Design', 4, 4, 2700, 'INR', 'Collected', '2026-09-10', '2026-09-17'),
]
for b in billables:
    cursor.execute("INSERT INTO billables (name, project_id, job_id, amount, currency, status, billing_date, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", b)

# Insert Timesheets (Including Unreviewed hours from your screenshot!)
timesheets = [
    # Bhavik Maradiya: 59h unreviewed
    (10, 1, '2026-09-14', 8, 0, 8, 'Unreviewed', 'Development', 'Built API endpoints for ticket queue'),
    (10, 1, '2026-09-15', 8.5, 0, 8.5, 'Unreviewed', 'Development', 'Optimized database indexes and query speed'),
    (10, 1, '2026-09-16', 7.5, 0, 7.5, 'Unreviewed', 'Bugfix', 'Resolved webhook timeout issue on Stripe'),
    # Jay Patel: 55.5h unreviewed
    (11, 2, '2026-09-14', 8, 0, 8, 'Unreviewed', 'Development', 'Implemented user profile and avatar upload'),
    (11, 2, '2026-09-15', 8, 0, 8, 'Unreviewed', 'Development', 'Created mobile responsive layouts'),
    # Approved logs
    (1, 3, '2026-09-14', 8, 8, 0, 'Approved', 'Development', 'Setup base repository and Docker environment'),
    (2, 3, '2026-09-14', 8, 8, 0, 'Approved', 'Development', 'Frontend boilerplate with Tailwind and React'),
    (3, 4, '2026-09-15', 6, 6, 0, 'Approved', 'QA', 'Manual test execution of login flow'),
    (4, 4, '2026-09-15', 7, 7, 0, 'Approved', 'Meetings', 'Client sprint planning discussion'),
]
for t in timesheets:
    cursor.execute("INSERT INTO timesheets (employee_id, job_id, date, logged_hours, approved_hours, unapproved_hours, status, tag, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", t)

conn.commit()

# Also dump to SQL script for MySQL compatibility
with open(SQL_FILE, 'w') as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()

print(f"SUCCESS: Created '{DB_FILE}' (SQLite) and '{SQL_FILE}' (MySQL dump).")
