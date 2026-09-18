BEGIN TRANSACTION;
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
INSERT INTO "billables" VALUES(1,'FasTicket - Feature Dev 1.1',1,1,720.0,'USD','Billed','2026-06-01','2026-06-08');
INSERT INTO "billables" VALUES(2,'Catchmeee - Design Phase',2,3,800.0,'USD','Billed','2026-06-08','2026-06-15');
INSERT INTO "billables" VALUES(3,'AccRegLab - Jun Dev Week 4',5,9,101.0,'USD','Billed','2026-06-30','2026-07-07');
INSERT INTO "billables" VALUES(4,'AccRegLab - Asia Cup SRS',5,9,300.0,'USD','Billed','2026-06-30','2026-07-07');
INSERT INTO "billables" VALUES(5,'Ride and Stride - Phase 1',6,10,3440.0,'NZD','Billed','2026-08-31','2026-09-07');
INSERT INTO "billables" VALUES(6,'DDJS - SRS Sign-off Milestone',3,5,62500.0,'INR','Contracted','2026-10-15','2026-10-22');
INSERT INTO "billables" VALUES(7,'DDJS - Discovery Kickoff',3,5,100000.0,'INR','Collected','2026-09-14','2026-09-21');
INSERT INTO "billables" VALUES(8,'My Medical English - Design',4,8,2700.0,'INR','Collected','2026-09-10','2026-09-17');
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- Fixed, Hourly, Dedicated, Bucket, Recurring
    status TEXT NOT NULL,
    project_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
INSERT INTO "contracts" VALUES(1,'Hourly-1','Hourly','In Progress',1);
INSERT INTO "contracts" VALUES(2,'Fixed-1','Fixed','In Progress',2);
INSERT INTO "contracts" VALUES(3,'Fixed-2','Fixed','In Progress',3);
INSERT INTO "contracts" VALUES(4,'Fixed-3','Fixed','In Progress',4);
INSERT INTO "contracts" VALUES(5,'Hourly-2','Hourly','In Progress',5);
INSERT INTO "contracts" VALUES(6,'Fixed-4','Fixed','In Progress',6);
INSERT INTO "contracts" VALUES(7,'Recurring-1','Recurring','In Progress',7);
INSERT INTO "contracts" VALUES(8,'Dedicated-1','Dedicated','In Progress',8);
CREATE TABLE departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
INSERT INTO "departments" VALUES(1,'Neo');
INSERT INTO "departments" VALUES(2,'Ark');
INSERT INTO "departments" VALUES(3,'Air');
INSERT INTO "departments" VALUES(4,'Dash');
INSERT INTO "departments" VALUES(5,'Flex');
INSERT INTO "departments" VALUES(6,'Bolt');
INSERT INTO "departments" VALUES(7,'Strike');
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
INSERT INTO "employees" VALUES(1,'171','Smit Parmar','A0','Frontend Engineer',3,'smit.p@7span.com','Yes');
INSERT INTO "employees" VALUES(2,'173','Parth Dhameliya','A0','Backend Engineer',3,'parth.d@7span.com','Yes');
INSERT INTO "employees" VALUES(3,'175','Devansh Patel','A0','Fullstack Engineer',4,'devansh@7span.com','Yes');
INSERT INTO "employees" VALUES(4,'178','Simaran Karangiya','A0','UI/UX Designer',3,'simaran@7span.com','Yes');
INSERT INTO "employees" VALUES(5,'184','Bhavdip Gediya','A0','QA Engineer',1,'bhavdip@7span.com','Yes');
INSERT INTO "employees" VALUES(6,'191','Dhara Matholiya','A0','Delivery Coordinator',7,'dhara@7span.com','No');
INSERT INTO "employees" VALUES(7,'201','Nikhil Sharma','Lead','Project Coordinator',1,'nikhil@7span.com','Yes');
INSERT INTO "employees" VALUES(8,'202','Mitesh Thakar','Senior','Job Coordinator',5,'mitesh@7span.com','Yes');
INSERT INTO "employees" VALUES(9,'203','Akshay Vadsara','Lead','Account Manager',2,'akshay@7span.com','Yes');
INSERT INTO "employees" VALUES(10,'204','Bhavik Maradiya','A0','Backend Engineer',4,'bhavik@7span.com','Yes');
INSERT INTO "employees" VALUES(11,'205','Jay Patel','A0','Frontend Engineer',3,'jay.p@7span.com','Yes');
INSERT INTO "employees" VALUES(12,'206','Darshak Ribadiya','A0','Mobile Engineer',1,'darshak@7span.com','Yes');
INSERT INTO "employees" VALUES(13,'207','Ujas Patel','A0','DevOps Engineer',2,'ujas@7span.com','Yes');
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
INSERT INTO "job_allocations" VALUES(1,1,1,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(2,1,2,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(3,2,12,120.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(4,3,4,80.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(5,3,11,40.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(6,5,4,50.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(7,5,5,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(8,6,1,120.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(9,6,11,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(10,7,2,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(11,7,10,80.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(12,8,3,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(13,8,5,80.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(14,9,10,120.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(15,9,13,80.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(16,10,12,150.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(17,11,13,100.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(18,12,1,160.0,'No','Yes');
INSERT INTO "job_allocations" VALUES(19,12,2,160.0,'No','Yes');
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
INSERT INTO "jobs" VALUES(1,'1.0 - Core Feature Dev',1,1,'Hourly','In Progress',8,'2026-05-15','2026-10-30',200.0,100.0);
INSERT INTO "jobs" VALUES(2,'1.1 - Mobile App Sync',1,1,'Hourly','In Progress',8,'2026-08-01','2026-11-15',120.0,100.0);
INSERT INTO "jobs" VALUES(3,'Design & BA Phase',2,2,'Fixed','In Progress',8,'2026-05-05','2026-09-30',120.0,100.0);
INSERT INTO "jobs" VALUES(4,'Video Streaming Architecture',2,2,'Fixed','In Review',8,'2026-06-01','2026-09-10',80.0,100.0);
INSERT INTO "jobs" VALUES(5,'Discovery & SRS Finalisation',3,3,'Fixed','In Progress',7,'2026-08-20','2026-11-15',150.0,100.0);
INSERT INTO "jobs" VALUES(6,'Frontend Portal Engineering',3,3,'Fixed','In Progress',7,'2026-09-01','2026-12-30',220.0,100.0);
INSERT INTO "jobs" VALUES(7,'Database & API Microservices',3,3,'Fixed','In Progress',7,'2026-09-01','2026-12-30',180.0,100.0);
INSERT INTO "jobs" VALUES(8,'Core Web Platform Support',4,4,'Fixed','In Progress',7,'2026-09-01','2026-12-15',180.0,100.0);
INSERT INTO "jobs" VALUES(9,'Development - Jun 26',5,5,'Hourly','In Progress',8,'2026-06-01','2026-10-15',200.0,100.0);
INSERT INTO "jobs" VALUES(10,'Ride Phase 1 MVP',6,6,'Fixed','In Progress',9,'2026-07-20','2026-10-31',150.0,100.0);
INSERT INTO "jobs" VALUES(11,'Website AMC & Support',7,7,'Recurring','In Progress',7,'2026-04-16','2026-12-31',100.0,100.0);
INSERT INTO "jobs" VALUES(12,'Dedicated BI Team',8,8,'Dedicated','In Progress',7,'2026-07-07','2026-12-31',320.0,100.0);
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
INSERT INTO "projects" VALUES(1,'FasTicket','FasTicket Inc','Active',7,9,8,'2026-05-10');
INSERT INTO "projects" VALUES(2,'Catchmeee','Catchmeee Media','Active',7,9,8,'2026-05-01');
INSERT INTO "projects" VALUES(3,'DDJS - RTO ERP Platform','DDJS Govt','Active',7,9,8,'2026-08-15');
INSERT INTO "projects" VALUES(4,'My Medical English','MME Global','Active',7,9,8,'2026-09-01');
INSERT INTO "projects" VALUES(5,'AccRegLab','AccRegLab UK','Active',7,9,8,'2026-06-01');
INSERT INTO "projects" VALUES(6,'Ride and Stride','Ride & Stride NZ','Active',7,9,8,'2026-07-15');
INSERT INTO "projects" VALUES(7,'Spark Solar','Spark Ltd','Active',7,9,8,'2026-04-16');
INSERT INTO "projects" VALUES(8,'Bluecopa BI Portal','Bluecopa Finance','Active',7,9,8,'2026-07-07');
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
INSERT INTO "timesheets" VALUES(1,1,1,'2026-08-10',8.0,8.0,0.0,'Approved','Development','FasTicket architecture setup');
INSERT INTO "timesheets" VALUES(2,2,1,'2026-08-11',8.0,8.0,0.0,'Approved','Development','FasTicket database schema');
INSERT INTO "timesheets" VALUES(3,4,3,'2026-08-15',6.5,6.5,0.0,'Approved','Design','Catchmeee wireframes review');
INSERT INTO "timesheets" VALUES(4,10,9,'2026-08-20',8.0,8.0,0.0,'Approved','Development','AccRegLab API integration');
INSERT INTO "timesheets" VALUES(5,12,10,'2026-08-25',7.5,7.5,0.0,'Approved','Development','Ride and Stride map screens');
INSERT INTO "timesheets" VALUES(6,1,6,'2026-09-02',8.0,8.0,0.0,'Approved','Development','DDJS frontend auth components');
INSERT INTO "timesheets" VALUES(7,2,7,'2026-09-03',8.5,8.5,0.0,'Approved','Development','DDJS microservices setup');
INSERT INTO "timesheets" VALUES(8,11,6,'2026-09-05',7.0,7.0,0.0,'Approved','Development','DDJS navigation and state handling');
INSERT INTO "timesheets" VALUES(9,3,8,'2026-09-08',6.0,6.0,0.0,'Approved','Development','My Medical English lesson player');
INSERT INTO "timesheets" VALUES(10,5,5,'2026-09-09',7.0,7.0,0.0,'Approved','QA','DDJS SRS validation testing');
INSERT INTO "timesheets" VALUES(11,10,7,'2026-09-14',8.0,0.0,8.0,'Unreviewed','Development','DDJS Redis caching layer');
INSERT INTO "timesheets" VALUES(12,10,7,'2026-09-15',8.5,0.0,8.5,'Unreviewed','Development','DDJS database query indexing');
INSERT INTO "timesheets" VALUES(13,10,7,'2026-09-16',7.5,0.0,7.5,'Unreviewed','Bugfix','DDJS Stripe payment webhook retry');
INSERT INTO "timesheets" VALUES(14,11,3,'2026-09-14',8.0,0.0,8.0,'Unreviewed','Development','Catchmeee responsive mobile views');
INSERT INTO "timesheets" VALUES(15,11,3,'2026-09-15',8.0,0.0,8.0,'Unreviewed','Development','Catchmeee layout polish');
INSERT INTO "timesheets" VALUES(16,1,1,'2026-09-16',8.0,8.0,0.0,'Approved','Development','FasTicket booking workflow');
INSERT INTO "timesheets" VALUES(17,2,1,'2026-09-17',8.0,8.0,0.0,'Approved','Development','FasTicket ticket PDF export');
INSERT INTO "timesheets" VALUES(18,12,2,'2026-09-17',7.0,7.0,0.0,'Approved','Development','FasTicket offline mobile sync');
INSERT INTO "timesheets" VALUES(19,13,11,'2026-09-18',6.0,6.0,0.0,'Approved','Maintenance','Spark Solar monthly server updates');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('departments',7);
INSERT INTO "sqlite_sequence" VALUES('employees',13);
INSERT INTO "sqlite_sequence" VALUES('projects',8);
INSERT INTO "sqlite_sequence" VALUES('contracts',8);
INSERT INTO "sqlite_sequence" VALUES('jobs',12);
INSERT INTO "sqlite_sequence" VALUES('job_allocations',19);
INSERT INTO "sqlite_sequence" VALUES('billables',8);
INSERT INTO "sqlite_sequence" VALUES('timesheets',19);
COMMIT;
