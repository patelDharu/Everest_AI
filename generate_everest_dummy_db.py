import sqlite3
import os

DB_FILE = "everest_dummy.db"
SQL_FILE = "everest_dummy.sql"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("Building enhanced Everest schema with Job Allocations & Date Ranges...")

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
    status TEXT NOT NULL, -- Active, Completed, On Hold
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
    type TEXT NOT NULL, -- Fixed, Hourly, Dedicated, Bucket, Recurring
    status TEXT NOT NULL, -- In Progress, In Review, Backlog, Closed
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

# 6. Job Allocations (Who is allocated to which job and their assigned hours)
cursor.execute("""
CREATE TABLE job_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    employee_id INTEGER,
    allocated_hours REAL DEFAULT 0,
    is_shadow TEXT DEFAULT 'No',
    allow_logging TEXT DEFAULT 'Yes',
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
""")

# 7. Billables
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

# 8. Timesheets (Logs with dates for date-range filtering)
cursor.execute("""
CREATE TABLE timesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    job_id INTEGER,
    date TEXT NOT NULL,
    logged_hours REAL NOT NULL,
    approved_hours REAL DEFAULT 0,
    unapproved_hours REAL DEFAULT 0,
    status TEXT NOT NULL, -- Approved, Unreviewed, Draft
    tag TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
""")

print("Inserting rich 7Span data across Projects, Jobs, Allocations, and Timesheet Dates...")

# Insert Pods
pods = ['Neo', 'Ark', 'Air', 'Dash', 'Flex', 'Bolt', 'Strike']
for p in pods:
    cursor.execute("INSERT INTO departments (name) VALUES (?)", (p,))

# Insert Employees
employees = [
    (171, 'Smit Parmar', 'A0', 'Frontend Engineer', 3, 'smit.p@7span.com', 'Yes'),
    (173, 'Parth Dhameliya', 'A0', 'Backend Engineer', 3, 'parth.d@7span.com', 'Yes'),
    (175, 'Devansh Patel', 'A0', 'Fullstack Engineer', 4, 'devansh@7span.com', 'Yes'),
    (178, 'Simaran Karangiya', 'A0', 'UI/UX Designer', 3, 'simaran@7span.com', 'Yes'),
    (184, 'Bhavdip Gediya', 'A0', 'QA Engineer', 1, 'bhavdip@7span.com', 'Yes'),
    (191, 'Dhara Matholiya', 'A0', 'Delivery Coordinator', 7, 'dhara@7span.com', 'No'),
    (201, 'Nikhil Sharma', 'Lead', 'Project Coordinator', 1, 'nikhil@7span.com', 'Yes'),
    (202, 'Mitesh Thakar', 'Senior', 'Job Coordinator', 5, 'mitesh@7span.com', 'Yes'),
    (203, 'Akshay Vadsara', 'Lead', 'Account Manager', 2, 'akshay@7span.com', 'Yes'),
    (204, 'Bhavik Maradiya', 'A0', 'Backend Engineer', 4, 'bhavik@7span.com', 'Yes'),
    (205, 'Jay Patel', 'A0', 'Frontend Engineer', 3, 'jay.p@7span.com', 'Yes'),
    (206, 'Darshak Ribadiya', 'A0', 'Mobile Engineer', 1, 'darshak@7span.com', 'Yes'),
    (207, 'Ujas Patel', 'A0', 'DevOps Engineer', 2, 'ujas@7span.com', 'Yes'),
]
for e in employees:
    cursor.execute("INSERT INTO employees (employee_code, name, grade, role, department_id, email, allocable) VALUES (?, ?, ?, ?, ?, ?, ?)", e)

# Insert Projects
projects = [
    ('FasTicket', 'FasTicket Inc', 'Active', 7, 9, 8, '2026-05-10'),
    ('Catchmeee', 'Catchmeee Media', 'Active', 7, 9, 8, '2026-05-01'),
    ('DDJS - RTO ERP Platform', 'DDJS Govt', 'Active', 7, 9, 8, '2026-08-15'),
    ('My Medical English', 'MME Global', 'Active', 7, 9, 8, '2026-09-01'),
    ('AccRegLab', 'AccRegLab UK', 'Active', 7, 9, 8, '2026-06-01'),
    ('Ride and Stride', 'Ride & Stride NZ', 'Active', 7, 9, 8, '2026-07-15'),
    ('Spark Solar', 'Spark Ltd', 'Active', 7, 9, 8, '2026-04-16'),
    ('Bluecopa BI Portal', 'Bluecopa Finance', 'Active', 7, 9, 8, '2026-07-07'),
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
    ('Dedicated-1', 'Dedicated', 'In Progress', 8),
]
for c in contracts:
    cursor.execute("INSERT INTO contracts (name, type, status, project_id) VALUES (?, ?, ?, ?)", c)

# Insert Jobs (Multiple active jobs per project)
jobs = [
    # FasTicket (2 Active Jobs)
    ('1.0 - Core Feature Dev', 1, 1, 'Hourly', 'In Progress', 8, '2026-05-15', '2026-10-30', 200, 100),
    ('1.1 - Mobile App Sync', 1, 1, 'Hourly', 'In Progress', 8, '2026-08-01', '2026-11-15', 120, 100),
    
    # Catchmeee (2 Jobs: 1 Active, 1 In Review)
    ('Design & BA Phase', 2, 2, 'Fixed', 'In Progress', 8, '2026-05-05', '2026-09-30', 120, 100),
    ('Video Streaming Architecture', 2, 2, 'Fixed', 'In Review', 8, '2026-06-01', '2026-09-10', 80, 100),
    
    # DDJS - RTO ERP Platform (3 Active Jobs)
    ('Discovery & SRS Finalisation', 3, 3, 'Fixed', 'In Progress', 7, '2026-08-20', '2026-11-15', 150, 100),
    ('Frontend Portal Engineering', 3, 3, 'Fixed', 'In Progress', 7, '2026-09-01', '2026-12-30', 220, 100),
    ('Database & API Microservices', 3, 3, 'Fixed', 'In Progress', 7, '2026-09-01', '2026-12-30', 180, 100),
    
    # My Medical English (1 Active Job)
    ('Core Web Platform Support', 4, 4, 'Fixed', 'In Progress', 7, '2026-09-01', '2026-12-15', 180, 100),
    
    # AccRegLab (1 Active Job)
    ('Development - Jun 26', 5, 5, 'Hourly', 'In Progress', 8, '2026-06-01', '2026-10-15', 200, 100),
    
    # Ride and Stride (1 Active Job)
    ('Ride Phase 1 MVP', 6, 6, 'Fixed', 'In Progress', 9, '2026-07-20', '2026-10-31', 150, 100),
    
    # Spark Solar (1 Active Job)
    ('Website AMC & Support', 7, 7, 'Recurring', 'In Progress', 7, '2026-04-16', '2026-12-31', 100, 100),
    
    # Bluecopa (1 Active Dedicated Job)
    ('Dedicated BI Team', 8, 8, 'Dedicated', 'In Progress', 7, '2026-07-07', '2026-12-31', 320, 100),
]
for j in jobs:
    cursor.execute("INSERT INTO jobs (name, project_id, contract_id, type, status, jc_id, start_date, end_date, allocated_hours, consumption_factor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", j)

# Insert Job Allocations (Linking multiple employees to each job)
allocations = [
    # Job 1: Core Feature Dev (FasTicket)
    (1, 1, 100, 'No', 'Yes'), # Smit Parmar
    (1, 2, 100, 'No', 'Yes'), # Parth Dhameliya
    # Job 2: Mobile App Sync (FasTicket)
    (2, 12, 120, 'No', 'Yes'), # Darshak Ribadiya
    # Job 3: Design & BA Phase (Catchmeee)
    (3, 4, 80, 'No', 'Yes'),  # Simaran Karangiya
    (3, 11, 40, 'No', 'Yes'), # Jay Patel
    # Job 5: Discovery & SRS (DDJS)
    (5, 4, 50, 'No', 'Yes'),  # Simaran Karangiya
    (5, 5, 100, 'No', 'Yes'), # Bhavdip Gediya
    # Job 6: Frontend Portal Engineering (DDJS)
    (6, 1, 120, 'No', 'Yes'), # Smit Parmar
    (6, 11, 100, 'No', 'Yes'), # Jay Patel
    # Job 7: Database & API Microservices (DDJS)
    (7, 2, 100, 'No', 'Yes'), # Parth Dhameliya
    (7, 10, 80, 'No', 'Yes'), # Bhavik Maradiya
    # Job 8: Core Web Platform (My Medical English)
    (8, 3, 100, 'No', 'Yes'), # Devansh Patel
    (8, 5, 80, 'No', 'Yes'),  # Bhavdip Gediya
    # Job 9: AccRegLab Dev
    (9, 10, 120, 'No', 'Yes'), # Bhavik Maradiya
    (9, 13, 80, 'No', 'Yes'),  # Ujas Patel
    # Job 10: Ride and Stride
    (10, 12, 150, 'No', 'Yes'), # Darshak Ribadiya
    # Job 11: Spark Solar
    (11, 13, 100, 'No', 'Yes'), # Ujas Patel
    # Job 12: Bluecopa Dedicated
    (12, 1, 160, 'No', 'Yes'),  # Smit Parmar
    (12, 2, 160, 'No', 'Yes'),  # Parth Dhameliya
]
for a in allocations:
    cursor.execute("INSERT INTO job_allocations (job_id, employee_id, allocated_hours, is_shadow, allow_logging) VALUES (?, ?, ?, ?, ?)", a)

# Insert Billables
billables = [
    ('FasTicket - Feature Dev 1.1', 1, 1, 720, 'USD', 'Billed', '2026-06-01', '2026-06-08'),
    ('Catchmeee - Design Phase', 2, 3, 800, 'USD', 'Billed', '2026-06-08', '2026-06-15'),
    ('AccRegLab - Jun Dev Week 4', 5, 9, 101, 'USD', 'Billed', '2026-06-30', '2026-07-07'),
    ('AccRegLab - Asia Cup SRS', 5, 9, 300, 'USD', 'Billed', '2026-06-30', '2026-07-07'),
    ('Ride and Stride - Phase 1', 6, 10, 3440, 'NZD', 'Billed', '2026-08-31', '2026-09-07'),
    ('DDJS - SRS Sign-off Milestone', 3, 5, 62500, 'INR', 'Contracted', '2026-10-15', '2026-10-22'),
    ('DDJS - Discovery Kickoff', 3, 5, 100000, 'INR', 'Collected', '2026-09-14', '2026-09-21'),
    ('My Medical English - Design', 4, 8, 2700, 'INR', 'Collected', '2026-09-10', '2026-09-17'),
]
for b in billables:
    cursor.execute("INSERT INTO billables (name, project_id, job_id, amount, currency, status, billing_date, due_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", b)

# Insert Timesheets across various dates (August 2026 to September 2026)
timesheets = [
    # August 2026 logs
    (1, 1, '2026-08-10', 8.0, 8.0, 0, 'Approved', 'Development', 'FasTicket architecture setup'),
    (2, 1, '2026-08-11', 8.0, 8.0, 0, 'Approved', 'Development', 'FasTicket database schema'),
    (4, 3, '2026-08-15', 6.5, 6.5, 0, 'Approved', 'Design', 'Catchmeee wireframes review'),
    (10, 9, '2026-08-20', 8.0, 8.0, 0, 'Approved', 'Development', 'AccRegLab API integration'),
    (12, 10, '2026-08-25', 7.5, 7.5, 0, 'Approved', 'Development', 'Ride and Stride map screens'),
    
    # September 1 - 10, 2026 logs
    (1, 6, '2026-09-02', 8.0, 8.0, 0, 'Approved', 'Development', 'DDJS frontend auth components'),
    (2, 7, '2026-09-03', 8.5, 8.5, 0, 'Approved', 'Development', 'DDJS microservices setup'),
    (11, 6, '2026-09-05', 7.0, 7.0, 0, 'Approved', 'Development', 'DDJS navigation and state handling'),
    (3, 8, '2026-09-08', 6.0, 6.0, 0, 'Approved', 'Development', 'My Medical English lesson player'),
    (5, 5, '2026-09-09', 7.0, 7.0, 0, 'Approved', 'QA', 'DDJS SRS validation testing'),
    
    # September 11 - 18, 2026 logs (Recent logs with unreviewed items!)
    (10, 7, '2026-09-14', 8.0, 0, 8.0, 'Unreviewed', 'Development', 'DDJS Redis caching layer'),
    (10, 7, '2026-09-15', 8.5, 0, 8.5, 'Unreviewed', 'Development', 'DDJS database query indexing'),
    (10, 7, '2026-09-16', 7.5, 0, 7.5, 'Unreviewed', 'Bugfix', 'DDJS Stripe payment webhook retry'),
    (11, 3, '2026-09-14', 8.0, 0, 8.0, 'Unreviewed', 'Development', 'Catchmeee responsive mobile views'),
    (11, 3, '2026-09-15', 8.0, 0, 8.0, 'Unreviewed', 'Development', 'Catchmeee layout polish'),
    (1, 1, '2026-09-16', 8.0, 8.0, 0, 'Approved', 'Development', 'FasTicket booking workflow'),
    (2, 1, '2026-09-17', 8.0, 8.0, 0, 'Approved', 'Development', 'FasTicket ticket PDF export'),
    (12, 2, '2026-09-17', 7.0, 7.0, 0, 'Approved', 'Development', 'FasTicket offline mobile sync'),
    (13, 11, '2026-09-18', 6.0, 6.0, 0, 'Approved', 'Maintenance', 'Spark Solar monthly server updates'),
]
for t in timesheets:
    cursor.execute("INSERT INTO timesheets (employee_id, job_id, date, logged_hours, approved_hours, unapproved_hours, status, tag, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", t)

conn.commit()

# Dump SQL
with open(SQL_FILE, 'w') as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()

print(f"SUCCESS: Enhanced '{DB_FILE}' and '{SQL_FILE}' successfully created!")
