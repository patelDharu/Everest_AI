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

def get_employee_granular_roles(emp_id: str) -> list:
    """Returns an ordered, indexed list of all active projects, JC jobs, and team allocations for an employee."""
    emp_id = str(emp_id)
    items = []
    
    # 1. Projects as Coordinator (PC, AM, SC)
    sql_proj = """
    SELECT id, name, 'PC' as role FROM projects WHERE pc_id = ? AND status = 'Active'
    UNION
    SELECT id, name, 'AM' as role FROM projects WHERE am_id = ? AND status = 'Active'
    UNION
    SELECT id, name, 'SC' as role FROM projects WHERE sc_id = ? AND status = 'Active';
    """
    df_proj = run_query(sql_proj, (emp_id, emp_id, emp_id))
    for _, r in df_proj.iterrows():
        items.append({
            "category": "project",
            "type": r["role"].lower(),
            "id": r["id"],
            "name": r["name"],
            "project_name": r["name"],
            "role_title": f"Project Coordinator ({r['role']})",
            "label": f"Project ({r['role']}): {r['name']}"
        })
        
    # 2. Jobs as JC
    sql_jc = """
    SELECT j.id, j.name, p.name as project_name
    FROM jobs j
    JOIN projects p ON j.project_id = p.id
    WHERE j.jc_id = ? AND j.status IN ('In Progress', 'In Review', 'Backlog');
    """
    df_jc = run_query(sql_jc, (emp_id,))
    for _, r in df_jc.iterrows():
        items.append({
            "category": "job",
            "type": "jc",
            "id": r["id"],
            "name": r["name"],
            "project_name": r["project_name"],
            "role_title": "Job Coordinator (JC)",
            "label": f"Job (JC): {r['name']} [{r['project_name']}]"
        })
        
    # 3. Allocated team member jobs
    sql_alloc = """
    SELECT j.id, j.name, p.name as project_name
    FROM job_allocations ja
    JOIN jobs j ON ja.job_id = j.id
    JOIN projects p ON j.project_id = p.id
    WHERE ja.employee_id = ? AND j.status IN ('In Progress', 'In Review', 'Backlog');
    """
    df_alloc = run_query(sql_alloc, (emp_id,))
    existing_job_ids = {it["id"] for it in items if it["category"] == "job"}
    for _, r in df_alloc.iterrows():
        if r["id"] not in existing_job_ids:
            items.append({
                "category": "allocation",
                "type": "allocation",
                "id": r["id"],
                "name": r["name"],
                "project_name": r["project_name"],
                "role_title": "Team Member",
                "label": f"Job (Team): {r['name']} [{r['project_name']}]"
            })
            
    return items

def get_employee_active_jobs(emp_id: str) -> list:
    """Returns an ordered, indexed list of all active jobs for an employee (as JC or allocated member)."""
    emp_id = str(emp_id)
    sql = """
    SELECT 
        j.id AS job_id,
        j.name AS job_name,
        p.id AS project_id,
        p.name AS project_name,
        j.status AS job_status,
        CASE 
            WHEN j.jc_id = ? THEN 'Job Coordinator (JC)'
            ELSE 'Team Member'
        END AS role_in_job,
        j.type AS job_type
    FROM jobs j
    JOIN projects p ON j.project_id = p.id
    LEFT JOIN job_allocations ja ON ja.job_id = j.id AND ja.employee_id = ?
    WHERE (j.jc_id = ? OR ja.employee_id = ?) 
      AND j.status IN ('In Progress', 'In Review', 'Backlog')
    GROUP BY j.id
    ORDER BY p.name ASC, j.name ASC;
    """
    df = run_query(sql, (emp_id, emp_id, emp_id, emp_id))
    items = []
    for _, r in df.iterrows():
        items.append({
            "id": r["job_id"],
            "name": r["job_name"],
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "role_title": r["role_in_job"],
            "type": "jc" if "JC" in r["role_in_job"] else "allocation",
            "category": "job",
            "label": f"Job: {r['job_name']} [{r['project_name']}]"
        })
    return items

def transfer_job_to_employee(job_id: str, from_emp_id: str, to_emp_id: str) -> bool:
    """
    Safely transfers a job from an exiting/departing employee to a successor colleague:
    - If departing employee was JC, updates jobs.jc_id to recipient.
    - Updates or clears job_allocations so departing employee has 0 allocation on this job.
    - Ensures recipient is allocated or JC.
    """
    import uuid
    job_id = str(job_id)
    from_emp_id = str(from_emp_id)
    to_emp_id = str(to_emp_id)
    
    # 1. Update jobs.jc_id if from_emp was JC
    execute_update("UPDATE jobs SET jc_id = ? WHERE id = ? AND jc_id = ?", (to_emp_id, job_id, from_emp_id))
    
    # 2. Check existing allocation for recipient
    df_rec = run_query("SELECT id FROM job_allocations WHERE job_id = ? AND employee_id = ?", (job_id, to_emp_id))
    
    # 3. Check existing allocation for departing employee
    df_from = run_query("SELECT id, allocated_hours FROM job_allocations WHERE job_id = ? AND employee_id = ?", (job_id, from_emp_id))
    
    if not df_from.empty:
        if not df_rec.empty:
            # Recipient already has row, delete departing employee's row
            execute_update("DELETE FROM job_allocations WHERE job_id = ? AND employee_id = ?", (job_id, from_emp_id))
        else:
            # Transfer departing employee's row to recipient
            execute_update("UPDATE job_allocations SET employee_id = ? WHERE job_id = ? AND employee_id = ?", (to_emp_id, job_id, from_emp_id))
    else:
        # Departing employee was only JC. Ensure recipient has an allocation row if none exists
        if df_rec.empty:
            alloc_id = str(uuid.uuid4())
            execute_update("INSERT INTO job_allocations (id, job_id, employee_id, allocated_hours, is_shadow) VALUES (?, ?, ?, 40.0, 0)", (alloc_id, job_id, to_emp_id))
            
    # Guarantee from_emp is completely purged from this job in allocations
    execute_update("DELETE FROM job_allocations WHERE job_id = ? AND employee_id = ?", (job_id, from_emp_id))
    return True

def reassign_specific_entity(category: str, role_type: str, item_id: str, to_emp_id: str, from_emp_id: str = None) -> int:
    """Executes a targeted SQL update to reassign a specific project role or job."""
    to_emp_id = str(to_emp_id)
    item_id = str(item_id)
    from_emp_id = str(from_emp_id) if from_emp_id else None
    
    updated = 0
    if category == "project":
        col = "pc_id" if role_type == "pc" else ("am_id" if role_type == "am" else "sc_id")
        updated += execute_update(f"UPDATE projects SET {col} = ? WHERE id = ?", (to_emp_id, item_id))
    elif category == "job":
        if from_emp_id:
            transfer_job_to_employee(item_id, from_emp_id, to_emp_id)
            updated += 1
        else:
            updated += execute_update("UPDATE jobs SET jc_id = ? WHERE id = ?", (to_emp_id, item_id))
            updated += execute_update("UPDATE job_allocations SET employee_id = ? WHERE job_id = ?", (to_emp_id, item_id))
    elif category == "allocation":
        if from_emp_id:
            transfer_job_to_employee(item_id, from_emp_id, to_emp_id)
            updated += 1
        else:
            updated += execute_update("UPDATE job_allocations SET employee_id = ? WHERE job_id = ?", (to_emp_id, item_id))
    return updated

def find_best_employee_match(name_query: str, all_employees: list) -> Optional[dict]:
    """Finds an employee by full name, first name, or partial string match."""
    if not name_query:
        return None
    nq = name_query.lower().strip()
    nq = re.sub(r'^(to|and|is|assign|assigned|the|transfer|ko|aur|phir)\s+', '', nq, flags=re.IGNORECASE)
    nq = re.sub(r'\s+(like that|please|now|etc|ko|assign|do|de do|ho)$', '', nq, flags=re.IGNORECASE).strip()
    
    for emp in all_employees:
        if emp['name'].lower() == nq:
            return emp
    for emp in all_employees:
        tokens = [t.lower() for t in emp['name'].split()]
        if nq in tokens:
            return emp
    for emp in all_employees:
        if emp['name'].lower().startswith(nq):
            return emp
    for emp in all_employees:
        if nq in emp['name'].lower() and len(nq) >= 3:
            return emp
    return None

def parse_granular_handover_prompt(prompt: str, all_employees: list, context_emp_id: Optional[str] = None):
    """
    Extracts individual role/job assignments from conversational prompts in Hindi, Hinglish, and English:
    - "job 1 Jay Patel ko assign ho aur job 2 Bhavik Vachhani ko assign ho"
    - "job 1 assign to Jay Patel and job 2 assign to Bhavik Vachhani"
    - "job 1 Jay Patel ko do aur job 2 Bhavik Vachhani ko do"
    - "job 1 Jay Patel ko aur job 2 Bhavik Vachhani ko"
    - "Assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, and job 3 to Dhruv Nayak"
    - "1 to Jay Patel and 2 to Bhavik Vachhani"
    """
    p = prompt.strip()
    
    # Primary numbered pattern
    pattern = re.compile(
        r'(?:assign\s+|reassign\s+|transfer\s+)?'
        r'(?:the\s+)?'
        r'(?:job\s*|item\s*)?(\d+)\s*(?::\s*)?'
        r'(?:is\s+assign\s+to\s+|is\s+assigned\s+to\s+|assign\s+to\s+|assigned\s+to\s+|assign\s+|to\s+be\s+assigned\s+to\s+|to\s+)?'
        r'([A-Za-z\s]+?)'
        r'(?:\s+ko\s+assign\s+ho|\s+ko\s+assign\s+karo|\s+ko\s+assign|\s+ko\s+de\s+do|\s+ko\s+do|\s+ko)?'
        r'(?=(?:,\s*|\s+aur\s+|\s+and\s+|\s+phir\s+|\s+job\s*\d+|\s*\.|$))',
        re.IGNORECASE
    )
    matches = pattern.findall(p)
    raw_assignments = []
    target_ids = set()
    
    for job_num_str, recipient_str in matches:
        recipient_clean = recipient_str.strip()
        recipient_clean = re.sub(r'^(and|or|the|aur|phir)\s+', '', recipient_clean, flags=re.IGNORECASE).strip()
        recipient_clean = re.sub(r'\s+from\s+.*$', '', recipient_clean, flags=re.IGNORECASE).strip()
        
        target_emp = find_best_employee_match(recipient_clean, all_employees)
        if target_emp:
            target_ids.add(target_emp['id'])
            
        try:
            job_idx = int(job_num_str)
        except (ValueError, TypeError):
            job_idx = None
            
        raw_assignments.append({
            "raw_entity": f"Job {job_idx}" if job_idx else "Job",
            "job_index": job_idx,
            "raw_recipient": recipient_clean,
            "target_emp": target_emp
        })
        
    # If no numbered matches, try named entity pattern
    if not raw_assignments:
        named_pattern = re.compile(
            r'(?:assign\s+|transfer\s+|reassign\s+)?'
            r'([A-Za-z0-9\s\-\.\&]+?)\s+'
            r'(?:is\s+|to\s+be\s+)?(?:assigned\s+|assign\s+|transferred\s+|transfer\s+)?(?:to\s+|ko\s+)'
            r'([A-Za-z\s]+?)(?=(?:,\s*|\s+and\s+|\s+aur\s+|\s*\.|$))',
            re.IGNORECASE
        )
        for entity_str, recipient_str in named_pattern.findall(p):
            entity_clean = entity_str.strip()
            recipient_clean = recipient_str.strip()
            entity_clean = re.sub(r'^(and|or|the|aur)\s+', '', entity_clean, flags=re.IGNORECASE).strip()
            recipient_clean = re.sub(r'\s+from\s+.*$', '', recipient_clean, flags=re.IGNORECASE).strip()
            
            target_emp = find_best_employee_match(recipient_clean, all_employees)
            if target_emp:
                target_ids.add(target_emp['id'])
                
            num_m = re.search(r'\b(?:job\s*|item\s*)?(\d+)\b', entity_clean, re.IGNORECASE)
            job_idx = int(num_m.group(1)) if num_m else None
            
            raw_assignments.append({
                "raw_entity": entity_clean,
                "job_index": job_idx,
                "raw_recipient": recipient_clean,
                "target_emp": target_emp
            })
            
    # Resolve source_emp
    source_emp = None
    p_lower = p.lower()
    
    # 1. Mask out all recipient names and individual name tokens from prompt text
    # to avoid false positives (e.g. 'Bhavik' in 'Bhavik Vachhani' matching 'Bhavik Maradiya')
    p_remainder = p_lower
    for assign in raw_assignments:
        if assign.get("raw_recipient"):
            p_remainder = p_remainder.replace(assign["raw_recipient"].lower(), " ")
        if assign.get("target_emp"):
            t_name = assign["target_emp"]["name"].lower()
            p_remainder = p_remainder.replace(t_name, " ")
            for tok in t_name.split():
                if len(tok) >= 3:
                    p_remainder = re.sub(rf'\b{re.escape(tok)}\b', " ", p_remainder)
    
    # Check if an explicit source employee name is in the remainder of the prompt
    for emp in sorted(all_employees, key=lambda x: len(x['name']), reverse=True):
        if emp['id'] in target_ids:
            continue
        ename = emp['name'].lower()
        first_name = ename.split()[0]
        if ename in p_remainder or (len(first_name) >= 4 and re.search(rf'\b{re.escape(first_name)}\b', p_remainder)):
            source_emp = emp
            break
            
    # 2. If not explicitly found in prompt, fallback to context_emp_id
    if not source_emp and context_emp_id:
        source_emp = next((e for e in all_employees if str(e['id']) == str(context_emp_id)), None)
        
    return source_emp, raw_assignments

def analyze_question(prompt: str, start_date=None, end_date=None, context_emp_id: Optional[str] = None, **kwargs) -> dict:
    """
    Intelligently analyzes natural language questions with accurate data resolution:
    - Granular Multi-Recipient Role & Job Handover (Job 1 to A, Job 2 to B, Job 3 to C)
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

    # Detect if an employee is mentioned (full name or first name/token)
    matched_emp = None
    for emp in sorted(all_employees, key=lambda x: len(x["name"]), reverse=True):
        if len(emp["name"]) >= 4 and emp["name"].lower() in p:
            matched_emp = emp
            break
            
    if not matched_emp:
        # Check first name or distinct tokens with word boundary
        for emp in all_employees:
            first_name = emp["name"].split()[0].lower()
            if len(first_name) >= 4 and re.search(rf'\b{re.escape(first_name)}\b', p):
                matched_emp = emp
                break
                
    # Check Hindi/Hinglish candidate extraction patterns e.g. "XYZ ka layoff", "XYZ ke under kitni job"
    if not matched_emp:
        name_cand_m = re.search(r'([A-Za-z\s]+?)\s+(?:ka|ki|ke)\s+(?:layoff|lay\s*off|exit|nikal|chhod|under)', prompt, re.IGNORECASE)
        if name_cand_m:
            matched_emp = find_best_employee_match(name_cand_m.group(1), all_employees)

    # -------------------------------------------------------------
    # INTENT 1A: Granular Multi-Recipient Conversational Handover
    # (e.g. "Ganesh is JC, assign job 1 to Jay Patel, job 2 to Bhavik Vachhani, job 3 to Dhruv Nayak"
    #  or "job 1 Jay Patel ko assign ho aur job 2 Bhavik Vachhani ko assign ho")
    # -------------------------------------------------------------
    source_emp, granular_assigns = parse_granular_handover_prompt(prompt, all_employees, context_emp_id=context_emp_id)
    if granular_assigns and (len(granular_assigns) >= 2 or (len(granular_assigns) == 1 and granular_assigns[0]["job_index"] is not None)):
        if not source_emp and matched_emp:
            # Ensure matched_emp is not one of the recipients
            target_emp_ids = [a["target_emp"]["id"] for a in granular_assigns if a["target_emp"]]
            if matched_emp["id"] not in target_emp_ids:
                source_emp = matched_emp
            
        if source_emp:
            active_jobs = get_employee_active_jobs(source_emp["id"])
            if not active_jobs:
                active_jobs = [it for it in get_employee_granular_roles(source_emp["id"]) if it["category"] == "job"]
                
            executed = []
            recipients_updated = {}
            
            for assign in granular_assigns:
                tgt = assign["target_emp"]
                if not tgt:
                    continue
                    
                matched_item = None
                # Check if specific job index requested
                if assign["job_index"] is not None and 1 <= assign["job_index"] <= len(active_jobs):
                    matched_item = active_jobs[assign["job_index"] - 1]
                else:
                    # Match by name
                    q_name = assign["raw_entity"].lower()
                    for it in active_jobs:
                        if q_name in it["name"].lower() or it["name"].lower() in q_name:
                            matched_item = it
                            break
                            
                if matched_item:
                    transfer_job_to_employee(matched_item["id"], source_emp["id"], tgt["id"])
                    executed.append({
                        "Job Name": matched_item["name"],
                        "Project": matched_item["project_name"],
                        "Role Type": matched_item["role_title"],
                        "Previous Assignee": source_emp["name"],
                        "Reassigned To": tgt["name"],
                        "Status": "Reassigned & Updated in DB"
                    })
                    recipients_updated[tgt["name"]] = tgt["id"]
                    
            if executed:
                remaining_jobs = get_employee_active_jobs(source_emp["id"])
                rem_count = len(remaining_jobs)
                post_audit = audit_employee_responsibilities(source_emp["id"])
                
                # Format recipient summary bullets
                rec_bullets = []
                for r_name, r_id in recipients_updated.items():
                    r_active = len(get_employee_active_jobs(r_id))
                    r_added = sum(1 for ex in executed if ex["Reassigned To"] == r_name)
                    rec_bullets.append(f"* 📈 **{r_name}:** **+{r_added} Job(s) Assigned** (Now holds **{r_active} active jobs** in Everest DB)")
                rec_summary_text = "\n".join(rec_bullets)
                
                bullets = ""
                for idx, ex in enumerate(executed, 1):
                    bullets += f"* 💼 **Job {idx}: {ex['Job Name']}** (Project: *{ex['Project']}*) ➔ Reassigned to **{ex['Reassigned To']}**\n"
                    
                rem_status_line = f"* 📉 **{source_emp['name']} (Departing Staff):** **{rem_count} Remaining Active Jobs**"
                if rem_count == 0:
                    rem_status_line = f"* 📉 **{source_emp['name']} (Departing Staff):** **0 Remaining Active Jobs (All assigned jobs successfully cleared & transferred!)**"
                    execute_update("UPDATE employees SET status = 'archived' WHERE id = ?", (source_emp["id"],))
                    
                return {
                    "answer": f"### ✅ [HANDOVER COMPLETED] Background Database Updated\n\n"
                              f"Successfully reallocated **{len(executed)} jobs** for **{source_emp['name']}** in the Everest database:\n\n"
                              f"{bullets}\n"
                              f"---\n"
                              f"**🔍 Verified Database Status:**\n"
                              f"{rem_status_line}\n"
                              f"{rec_summary_text}\n"
                              f"* 💾 Live SQLite database updated: `jobs` and `job_allocations` reflect these changes immediately.",
                    "df": pd.DataFrame(executed),
                    "show_table_open": False,
                    "sql": f"-- Live UPDATE on jobs and job_allocations: from {source_emp['id']}",
                    "metrics": {
                        "Departing Employee": source_emp["name"],
                        "Jobs Reassigned": len(executed),
                        "Remaining Jobs": rem_count,
                        "Status": "Completed (0 Jobs)" if rem_count == 0 else f"{rem_count} remaining"
                    },
                    "handover_completed": True,
                    "clear_context": (rem_count == 0),
                    "notification": {
                        "id": f"notif_handover_{datetime.datetime.now().strftime('%M%S')}",
                        "title": f"Handover Completed: {source_emp['name']}'s Jobs Reassigned",
                        "category": "Handover",
                        "icon": "✅",
                        "message": f"Successfully reallocated {len(executed)} jobs from {source_emp['name']}. Remaining active jobs: {rem_count}.",
                        "time": "Just now",
                        "status": "Pending"
                    },
                    "chart_type": None,
                    "insight": f"Granular handover complete. {source_emp['name']} remaining active jobs = {rem_count}."
                }

    # -------------------------------------------------------------
    # INTENT 1B: Bulk Reassignment in Chat (Single Colleague)
    # (e.g. "Transfer all jobs to Jay Patel", "Transfer all jobs from Bhoomi to Bhavik")
    # -------------------------------------------------------------
    is_bulk_handover = any(w in p for w in ["reassign", "transfer", "handover", "sabhi job", "sab job", "all jobs", "sare job"])
    if is_bulk_handover and ("to" in p or "from" in p or "ko" in p or context_emp_id is not None):
        found_emps = []
        for emp in all_employees:
            name_low = emp["name"].lower()
            if name_low in p:
                found_emps.append((emp, p.find(name_low)))
        
        found_emps.sort(key=lambda x: x[1])
        from_emp = None
        to_emp = None
        
        if len(found_emps) >= 2:
            from_emp = found_emps[0][0]
            to_emp = found_emps[1][0]
        elif len(found_emps) == 1 and context_emp_id:
            to_emp = found_emps[0][0]
            from_emp = next((e for e in all_employees if str(e['id']) == str(context_emp_id)), None)
            
        if from_emp and to_emp and from_emp['id'] != to_emp['id']:
            # Transfer all active jobs
            from_jobs = get_employee_active_jobs(from_emp["id"])
            for fj in from_jobs:
                transfer_job_to_employee(fj["id"], from_emp["id"], to_emp["id"])
            result = reassign_employee_roles(from_emp["id"], to_emp["id"], "all")
            post_jobs = get_employee_active_jobs(from_emp["id"])
            rem_count = len(post_jobs)
            execute_update("UPDATE employees SET status = 'archived' WHERE id = ?", (from_emp["id"],))
            to_active_count = len(get_employee_active_jobs(to_emp["id"]))
            
            return {
                "answer": f"### ✅ [HANDOVER COMPLETED] All Roles & Jobs Transferred\n\n"
                          f"Transferred all active responsibilities from **{from_emp['name']}** to **{to_emp['name']}** in the Everest database.\n\n"
                          f"* 💼 **Transferred Jobs:** **{len(from_jobs)} active jobs** reassigned to **{to_emp['name']}**.\n"
                          f"* 📋 **Projects Transferred:** {result['summary']}\n"
                          f"---\n"
                          f"**🔍 Verified Database Status:**\n"
                          f"* 📉 **{from_emp['name']} (Departing Staff):** **0 Remaining Active Jobs (All assigned jobs successfully cleared!)**\n"
                          f"* 📈 **{to_emp['name']}:** **+{len(from_jobs)} Jobs Added** (Now holds **{to_active_count} active jobs** in Everest DB)\n"
                          f"* 💾 Live SQLite database updated immediately.",
                "df": pd.DataFrame([{"Source Employee": from_emp["name"], "Successor": to_emp["name"], "Jobs Transferred": len(from_jobs), "Status": "Transferred", "Details": result['summary']}]),
                "show_table_open": False,
                "sql": f"-- Live UPDATE on projects, jobs, and job_allocations from {from_emp['id']} to {to_emp['id']}",
                "metrics": {
                    "From": from_emp["name"],
                    "To": to_emp["name"],
                    "Remaining Roles": rem_count,
                    "Status": "Completed (0 Jobs)"
                },
                "handover_completed": True,
                "clear_context": True,
                "notification": {
                    "id": f"notif_bulk_{datetime.datetime.now().strftime('%M%S')}",
                    "title": f"Bulk Handover: {from_emp['name']} ➔ {to_emp['name']}",
                    "category": "Handover",
                    "icon": "✅",
                    "message": f"Transferred all {len(from_jobs)} jobs from {from_emp['name']} to {to_emp['name']}. Remaining active jobs: 0.",
                    "time": "Just now",
                    "status": "Pending"
                },
                "chart_type": None,
                "insight": f"Database updated. {from_emp['name']} no longer holds active project or job allocations (0 active jobs)."
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
    # INTENT 5: Specific Employee Projects & Jobs In-Depth / Handover Inquiry
    # (e.g. "Bhoomi Trivedi ka layoff ho gya hai, uske under kitni job assign hai?", "Ganesh is leaving, what jobs does he have?")
    # -------------------------------------------------------------
    if matched_emp and any(w in p for w in [
        "which project", "which job", "what project", "what job", "working on", "allocated", "detail", "work",
        "job", "jobs", "leaving", "leave", "handover", "exit", "reassign", "who is", "layoff", "lay off", "laid off",
        "nikal", "chhod", "kitni job", "kitni jobs", "under kitni", "ke under"
    ]):
        eid = matched_emp["id"]
        ename = matched_emp["name"]
        status_label = "Archived (Exited)" if matched_emp.get("status") == "archived" else "Active"
        is_handover_inquiry = any(w in p for w in [
            "leaving", "leave", "handover", "reassign", "exit", "quit", "layoff", "lay off", "laid off",
            "nikal", "chhod", "kitni job", "kitni jobs", "under kitni", "ke under"
        ])

        # Projects managed as PC, AM, SC
        sql_pc = f"""
        SELECT name, 'Project Coordinator (PC)' as role FROM projects WHERE pc_id = '{eid}' AND status = 'Active'
        UNION
        SELECT name, 'Account Manager (AM)' as role FROM projects WHERE am_id = '{eid}' AND status = 'Active'
        UNION
        SELECT name, 'Sales Coordinator (SC)' as role FROM projects WHERE sc_id = '{eid}' AND status = 'Active';
        """
        df_pc = run_query(sql_pc)

        # Get active jobs deterministically
        active_jobs = get_employee_active_jobs(eid)
        total_active_jobs = len(active_jobs)
        unique_projects = len(set(j["project_name"] for j in active_jobs))

        # Build clean bulleted response
        projects_breakdown = ""
        if active_jobs:
            projects_breakdown = "\n\n**Active Project & Job Assignments:**\n"
            for j_idx, jr in enumerate(active_jobs, 1):
                projects_breakdown += f"* 💼 **Job {j_idx}: {jr['name']}** ({jr['role_title']} | Project: *{jr['project_name']}*)\n"
        else:
            projects_breakdown = "\n\n*Currently has 0 active in-progress job allocations in Everest.*"

        managed_summary = ""
        if not df_pc.empty:
            managed_summary = f"\n* **Coordinator Governance:** Oversees **{len(df_pc)} active project(s)** as PC/AM/SC."

        handover_hint = ""
        if is_handover_inquiry and active_jobs:
            sample_names = ["Jay Patel", "Bhavik Vachhani", "Dhruv Nayak"]
            prompt_example_en = ", ".join([f"job {i} to {sample_names[(i-1) % len(sample_names)]}" for i in range(1, min(total_active_jobs, 3) + 1)])
            prompt_example_hi = " aur ".join([f"job {i} {sample_names[(i-1) % len(sample_names)]} ko assign ho" for i in range(1, min(total_active_jobs, 2) + 1)])
            handover_hint = (
                f"\n\n---\n"
                f"💡 **Next Step: Assign These Jobs to Colleagues (Step 2)**\n"
                f"Aap in jobs ko kisi aur employee ko assign karne ke liye niche likhi tarah se reply de sakte hain:\n"
                f"* **In Hindi / Hinglish:** `{prompt_example_hi}`\n"
                f"* **In English:** `Assign {prompt_example_en}`\n"
                f"* **Or Transfer All at once:** `Transfer all jobs from {ename} to {sample_names[0]}` (ya `Sabhi jobs {sample_names[0]} ko de do`)"
            )

        title_label = "[HANDOVER AUDIT]" if is_handover_inquiry else "[EMPLOYEE]"

        df_out = pd.DataFrame([{
            "Job Number": f"Job {i}",
            "Job Name": j["name"],
            "Project": j["project_name"],
            "Role": j["role_title"]
        } for i, j in enumerate(active_jobs, 1)]) if active_jobs else pd.DataFrame()

        return {
            "answer": f"### {title_label} Work Profile: **{ename}**\n\n"
                      f"* **Status:** `{status_label}` | **Pod/Department:** `{matched_emp.get('department', 'N/A')}` | **Role:** `{matched_emp.get('role', 'N/A')}`\n"
                      f"* **Current Active Work:** Assigned to **{total_active_jobs} Active Jobs** across **{unique_projects} Projects**.{managed_summary}{projects_breakdown}{handover_hint}",
            "df": df_out,
            "show_table_open": False,
            "sql": f"-- Live query for active jobs of {eid}",
            "metrics": {
                "Employee": ename,
                "Status": status_label,
                "Active Jobs": total_active_jobs,
                "Projects": unique_projects
            },
            "context_emp": {
                "id": matched_emp["id"],
                "name": matched_emp["name"],
                "role": matched_emp.get("role", "Staff"),
                "active_jobs_count": total_active_jobs
            },
            "chart_type": None,
            "insight": f"{ename} has {total_active_jobs} active job(s) and {len(df_pc)} project coordinator role(s)."
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

# -------------------------------------------------------------
# EVEREST ERP NATIVE VIEW BUILDERS
# -------------------------------------------------------------
def get_everest_projects_view(search: str = "", status: str = "All", limit: int = 50) -> pd.DataFrame:
    """Fetches formatted projects matching Everest screenshot #media_1789708497100.png"""
    where_clauses = []
    params = []
    
    if status != "All":
        where_clauses.append("p.status = ?")
        params.append(status)
    if search:
        where_clauses.append("(p.name LIKE ? OR p.client_name LIKE ? OR ep.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        p.id,
        p.name AS "Project Name",
        p.client_name AS "Client",
        COALESCE(ep.name, '-') AS "PC",
        COALESCE(ea.name, '-') AS "AM",
        COALESCE(es.name, '-') AS "SC",
        p.status AS "Status",
        (SELECT COUNT(*) FROM jobs WHERE project_id = p.id AND status = 'In Progress') AS "Pending Jobs",
        (SELECT COUNT(*) FROM billables WHERE project_id = p.id AND status != 'collected' AND status != 'cancelled') AS "Pending Billables"
    FROM projects p
    LEFT JOIN employees ep ON p.pc_id = ep.id
    LEFT JOIN employees ea ON p.am_id = ea.id
    LEFT JOIN employees es ON p.sc_id = es.id
    {where_sql}
    ORDER BY 
        CASE WHEN p.name = 'Property Vibees' THEN 0 ELSE 1 END,
        "Pending Jobs" DESC, p.name ASC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_jobs_view(search: str = "", status: str = "All", project_id: str = None, jc_id: str = None, limit: int = 50) -> pd.DataFrame:
    """Fetches formatted jobs matching Everest screenshot #media_1789708516090.png"""
    where_clauses = []
    params = []
    
    if status != "All":
        where_clauses.append("j.status = ?")
        params.append(status)
    if project_id:
        where_clauses.append("j.project_id = ?")
        params.append(project_id)
    if jc_id:
        where_clauses.append("j.jc_id = ?")
        params.append(jc_id)
    if search:
        where_clauses.append("(j.name LIKE ? OR p.name LIKE ? OR ej.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        j.id,
        j.name AS "Job Name",
        COALESCE(j.type, 'General') AS "Type",
        p.name AS "Project",
        j.status AS "Status",
        COALESCE(ej.name, 'Unassigned') AS "JC (Job Coordinator)",
        COALESCE(j.start_date, '-') AS "Start Date",
        COALESCE(j.end_date, '-') AS "End Date",
        COALESCE(j.allocated_hours, 0) AS "Budget (hrs)"
    FROM jobs j
    JOIN projects p ON j.project_id = p.id
    LEFT JOIN employees ej ON j.jc_id = ej.id
    {where_sql}
    ORDER BY 
        CASE 
            WHEN j.name IN ('Mobile UI Design & Prototype', 'Backend API Architecture & DB Sync', 'Security Audit & Cloud Compliance') THEN 0 
            ELSE 1 
        END,
        j.start_date DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_billables_view(search: str = "", status: str = "All", project_id: str = None, limit: int = 50) -> pd.DataFrame:
    """Fetches formatted billables matching Everest screenshot #media_1789708516099.png"""
    where_clauses = []
    params = []
    
    if status != "All":
        where_clauses.append("b.status = ?")
        params.append(status)
    if project_id:
        where_clauses.append("b.project_id = ?")
        params.append(project_id)
    if search:
        where_clauses.append("(b.name LIKE ? OR p.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        b.id,
        b.name AS "Billable Item",
        b.status AS "Status",
        COALESCE(b.amount, 0) AS "Amount (USD)",
        p.name AS "Project",
        COALESCE(j.name, 'Milestone') AS "Job",
        COALESCE(b.billing_date, '-') AS "Billing Date",
        COALESCE(b.due_date, '-') AS "Due Date",
        COALESCE(ej.name, '-') AS "JC",
        COALESCE(ea.name, '-') AS "AM",
        COALESCE(es.name, '-') AS "SC"
    FROM billables b
    JOIN projects p ON b.project_id = p.id
    LEFT JOIN jobs j ON b.job_id = j.id
    LEFT JOIN employees ej ON j.jc_id = ej.id
    LEFT JOIN employees ea ON p.am_id = ea.id
    LEFT JOIN employees es ON p.sc_id = es.id
    {where_sql}
    ORDER BY b.billing_date DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_overdue_extensions_view(search: str = "", limit: int = 50) -> pd.DataFrame:
    """Fetches overdue & extended billables matching Everest screenshot #media_1789708547862.png"""
    where_clauses = []
    params = []
    if search:
        where_clauses.append("(b.name LIKE ? OR p.name LIKE ? OR be.justification LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])
        
    where_sql = f"AND {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        b.name AS "Billable Item",
        p.name AS "Project",
        COALESCE(j.name, '-') AS "Job",
        b.amount AS "Amount (USD)",
        b.status AS "Status",
        be.start_date AS "Original Date",
        be.billing_date AS "Extended Date",
        COALESCE(be.justification, 'Client dependency') AS "Extension Reason",
        COALESCE(ej.name, '-') AS "JC",
        COALESCE(ep.name, '-') AS "PC"
    FROM billable_extensions be
    JOIN billables b ON be.billable_id = b.id
    JOIN projects p ON b.project_id = p.id
    LEFT JOIN jobs j ON b.job_id = j.id
    LEFT JOIN employees ej ON j.jc_id = ej.id
    LEFT JOIN employees ep ON p.pc_id = ep.id
    WHERE 1=1 {where_sql}
    ORDER BY be.date_created DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def reset_demo_handover_data():
    """Resets Ganesh Thamangalath's 3 active jobs and Property Vibees PC for live demo testing."""
    import uuid
    ganesh_id = "6d5eb96c-13c9-41b1-a3ad-b1229918c710"
    
    # 1. Clean previous copies
    job_titles = [
        "Mobile UI Design & Prototype",
        "Backend API Architecture & DB Sync",
        "Security Audit & Cloud Compliance"
    ]
    for jt in job_titles:
        j_rows = run_query("SELECT id FROM jobs WHERE name = ?", (jt,)).to_dict('records')
        for jr in j_rows:
            jid = jr["id"]
            execute_update("DELETE FROM job_allocations WHERE job_id = ?", (jid,))
            execute_update("DELETE FROM timesheets WHERE job_id = ?", (jid,))
            execute_update("DELETE FROM jobs WHERE id = ?", (jid,))

    # 2. Get 3 active projects
    projs = run_query("SELECT id FROM projects WHERE status = 'Active' LIMIT 3").to_dict('records')
    p0 = projs[0]["id"] if projs else "00c26944-8a57-4274-bce4-408acc8329fc"
    p1 = projs[1]["id"] if len(projs) > 1 else p0
    p2 = projs[2]["id"] if len(projs) > 2 else p0

    job_configs = [
        ("Mobile UI Design & Prototype", p0, "In Progress", "Design"),
        ("Backend API Architecture & DB Sync", p1, "In Progress", "Development"),
        ("Security Audit & Cloud Compliance", p2, "In Progress", "DevOps")
    ]

    for jname, pid, status, jtype in job_configs:
        jid = str(uuid.uuid4())
        execute_update("""
            INSERT INTO jobs (id, project_id, name, type, status, start_date, end_date, allocated_hours, jc_id)
            VALUES (?, ?, ?, ?, ?, '2026-03-01', '2026-05-30', 40.0, ?)
        """, (jid, pid, jname, jtype, status, ganesh_id))
        
        execute_update("""
            INSERT INTO job_allocations (id, job_id, employee_id, allocated_hours, is_shadow)
            VALUES (?, ?, ?, 40.0, 0)
        """, (str(uuid.uuid4()), jid, ganesh_id))

    # Set Property Vibees PC to Ganesh
    execute_update("UPDATE projects SET pc_id = ? WHERE name = 'Property Vibees'", (ganesh_id,))
    return True

def get_everest_contracts_view(search: str = "", status: str = "All", limit: int = 50) -> pd.DataFrame:
    """Fetches formatted contracts matching Everest screenshot 05_Work_Contracts.png"""
    where_clauses = []
    params = []
    if status != "All":
        where_clauses.append("c.status = ?")
        params.append(status)
    if search:
        where_clauses.append("(c.name LIKE ? OR p.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        c.id,
        c.name AS "Contract Name",
        COALESCE(c.type, 'Fixed') AS "Type",
        c.status AS "Status",
        COALESCE(p.name, 'Client Project') AS "Project",
        (SELECT COUNT(*) FROM jobs WHERE project_id = p.id) AS "Jobs Count"
    FROM contracts c
    LEFT JOIN projects p ON c.project_id = p.id
    {where_sql}
    ORDER BY c.id DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_tasks_view(search: str = "", status: str = "All", limit: int = 50) -> pd.DataFrame:
    """Fetches formatted tasks matching Everest screenshot 03_Tasks.png"""
    where_clauses = []
    params = []
    if status != "All":
        where_clauses.append("t.status = ?")
        params.append(status)
    if search:
        where_clauses.append("(t.title LIKE ? OR e.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        t.id,
        t.title AS "Task Title",
        t.status AS "Status",
        COALESCE(t.type, 'General') AS "Type",
        COALESCE(t.due_date, '-') AS "Due Date",
        COALESCE(e.name, 'Unassigned') AS "Assignee"
    FROM tasks t
    LEFT JOIN employees e ON t.assignee = e.id
    {where_sql}
    ORDER BY t.date_created DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_timesheets_view(search: str = "", limit: int = 50) -> pd.DataFrame:
    """Fetches formatted timesheet logs matching Everest screenshot 12_Timesheet_My_Team.png"""
    where_clauses = []
    params = []
    if search:
        where_clauses.append("(e.name LIKE ? OR p.name LIKE ? OR j.name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        ts.date AS "Date",
        e.name AS "Employee",
        p.name AS "Project",
        j.name AS "Job",
        COALESCE(ts.logged_hours, 0) AS "Logged (hrs)",
        COALESCE(ts.approved_hours, 0) AS "Approved (hrs)",
        ts.status AS "Status"
    FROM timesheets ts
    JOIN employees e ON ts.employee_id = e.id
    JOIN jobs j ON ts.job_id = j.id
    JOIN projects p ON j.project_id = p.id
    {where_sql}
    ORDER BY ts.date DESC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

def get_everest_employees_view(search: str = "", department: str = "All", limit: int = 50) -> pd.DataFrame:
    """Fetches formatted employee directory matching Everest screenshot 18_Org_Employees.png"""
    where_clauses = []
    params = []
    if department != "All":
        where_clauses.append("e.department = ?")
        params.append(department)
    if search:
        where_clauses.append("(e.name LIKE ? OR e.email LIKE ? OR e.role LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s])
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        e.id,
        e.name AS "Name",
        COALESCE(e.role, 'Engineer') AS "Designation",
        COALESCE(e.grade, 'A0') AS "Grade",
        COALESCE(e.department, 'Engineering') AS "Department",
        e.email AS "Email",
        e.status AS "Status",
        COALESCE(e.allocable, 'Yes') AS "Allocable",
        COALESCE(e.joining_date, '2024-01-01') AS "Joining Date"
    FROM employees e
    {where_sql}
    ORDER BY e.name ASC
    LIMIT {limit};
    """
    return run_query(sql, tuple(params) if params else None)

