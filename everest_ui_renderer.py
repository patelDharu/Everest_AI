# -*- coding: utf-8 -*-
"""
Everest UI Renderer - Generates pixel-perfect HTML/CSS tables and cards
matching 7Span Everest ERP (everest.7span.work)
"""
import re
import html

AVATAR_PALETTE = [
    ("#0284c7", "#ffffff"), # Sky Blue
    ("#7c3aed", "#ffffff"), # Violet
    ("#db2777", "#ffffff"), # Pink
    ("#059669", "#ffffff"), # Emerald
    ("#d97706", "#ffffff"), # Amber
    ("#0891b2", "#ffffff"), # Cyan
    ("#4f46e5", "#ffffff"), # Indigo
    ("#dc2626", "#ffffff"), # Red
    ("#475569", "#ffffff"), # Slate
]

def get_avatar_color(name: str):
    if not name or name in ("Unassigned", "-", "None"):
        return "#94a3b8", "#ffffff"
    h = sum(ord(c) for c in name) % len(AVATAR_PALETTE)
    return AVATAR_PALETTE[h]

def get_initials(name: str):
    if not name or name in ("Unassigned", "-", "None"):
        return "--"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()

def render_avatar_circle(name: str, size: int = 28, show_tooltip: bool = True):
    if not name or name in ("Unassigned", "-", "None"):
        return f'<span style="color:#94a3b8; font-size:0.8rem;">--</span>'
    bg, fg = get_avatar_color(name)
    inits = get_initials(name)
    escaped_name = html.escape(name)
    tooltip_attr = f'title="{escaped_name}"' if show_tooltip else ''
    return f"""<div {tooltip_attr} style="width:{size}px; height:{size}px; border-radius:50%; background-color:{bg}; color:{fg}; display:inline-flex; align-items:center; justify-content:center; font-size:{int(size*0.42)}px; font-weight:700; flex-shrink:0; cursor:default; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">{inits}</div>"""

def render_avatar_with_name(name: str, size: int = 28):
    if not name or name in ("Unassigned", "-", "None"):
        return '<span style="color:#94a3b8; font-size:0.85rem; font-style:italic;">Unassigned</span>'
    avatar_html = render_avatar_circle(name, size=size, show_tooltip=False)
    escaped_name = html.escape(name)
    return f"""<div style="display:flex; align-items:center; gap:8px;">
        {avatar_html}
        <span style="font-size:0.86rem; color:#1e293b; font-weight:500;">{escaped_name}</span>
    </div>"""

def render_status_pill(status: str):
    s = (status or "").strip().lower()
    if "in progress" in s:
        bg, fg = "#fef9c3", "#854d0e" # Amber/Yellow
    elif s in ("active", "completed", "collected"):
        bg, fg = "#def7ec", "#03543f" # Emerald Green
    elif s in ("billed", "in review"):
        bg, fg = "#e0f2fe", "#0369a1" # Sky Blue
    elif s in ("contracted", "cancelled", "overdue"):
        bg, fg = "#fee2e2", "#991b1b" # Rose/Red
    else:
        bg, fg = "#f1f5f9", "#475569" # Slate Gray

    return f"""<span style="background-color:{bg}; color:{fg}; padding:3px 10px; border-radius:9999px; font-size:0.75rem; font-weight:600; display:inline-block; text-align:center;">{html.escape(status or '-')}</span>"""

def render_jobs_table(df, limit: int = 25):
    """Renders pixel-perfect Everest Jobs directory matching media_1789708516090.png"""
    if df is None or df.empty:
        return """<div style="padding:24px; text-align:center; color:#64748b; background:#fff; border-radius:8px; border:1px solid #e2e8f0;">No active jobs found.</div>"""
    
    rows_html = []
    display_df = df.head(limit)
    demo_jobs = ('Mobile UI Design & Prototype', 'Backend API Architecture & DB Sync', 'Security Audit & Cloud Compliance')
    
    for idx, r in display_df.iterrows():
        job_name = str(r.get("Job Name", ""))
        is_demo = job_name in demo_jobs
        jc_name = str(r.get("JC (Job Coordinator)", "Unassigned"))
        proj_name = str(r.get("Project", ""))
        status = str(r.get("Status", "In Progress"))
        start_date = str(r.get("Start Date", "-"))
        end_date = str(r.get("End Date", "-"))
        
        if is_demo:
            row_bg = "background-color: #fffbeb;" 
            demo_badge = '<span style="background:#fef08a; color:#854d0e; font-size:0.68rem; padding:1px 6px; border-radius:4px; margin-left:6px; font-weight:700;">HANDOVER DEMO</span>'
        else:
            row_bg = "background-color: #ffffff;"
            demo_badge = ""
            
        type_icon = "⇄" if "Support" in job_name or "AMC" in job_name or "Marketing" in job_name else ("$" if "Fixed" in job_name or is_demo else "⏱")
        
        row_html = f"""
        <tr style="{row_bg} border-bottom: 1px solid #f1f5f9; height: 46px;">
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; width: 40px;">{idx + 1}</td>
            <td style="padding: 8px 14px; font-weight: 600; color: #0f172a; font-size: 0.86rem;">
                {html.escape(job_name)} {demo_badge}
            </td>
            <td style="padding: 8px 14px; text-align: center; color: #64748b; font-size: 0.9rem; width: 50px;">{type_icon}</td>
            <td style="padding: 8px 14px; color: #334155; font-size: 0.85rem; font-weight: 500;">{html.escape(proj_name)}</td>
            <td style="padding: 8px 14px; width: 110px;">{render_status_pill(status)}</td>
            <td style="padding: 8px 14px;">{render_avatar_with_name(jc_name)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; white-space: nowrap;">{html.escape(start_date)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; white-space: nowrap;">{html.escape(end_date)}</td>
        </tr>
        """
        rows_html.append(row_html)
        
    table_content = "".join(rows_html)
    total_count = len(df)
    
    return f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', sans-serif;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; height: 38px;">
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">#</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Name</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Type</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Project</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Status</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">JC</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Start Date ˇ</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">End Date</th>
                    </tr>
                </thead>
                <tbody>
                    {table_content}
                </tbody>
            </table>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background-color: #ffffff; border-top: 1px solid #f1f5f9; font-size: 0.8rem; color: #64748b;">
            <div>Showing 1 to {len(display_df)} of {total_count} entries</div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; color: #94a3b8; cursor: not-allowed;">‹ Previous</span>
                <span style="padding: 3px 8px; background-color: #dc2626; color: white; border-radius: 4px; font-weight: 600;">1</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">2</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">3</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">Next ›</span>
            </div>
        </div>
    </div>
    """

def render_projects_table(df, limit: int = 25):
    """Renders pixel-perfect Everest Projects directory matching media_1789708497100.png"""
    if df is None or df.empty:
        return """<div style="padding:24px; text-align:center; color:#64748b; background:#fff; border-radius:8px; border:1px solid #e2e8f0;">No active projects found.</div>"""
        
    rows_html = []
    display_df = df.head(limit)
    
    for idx, r in display_df.iterrows():
        pname = str(r.get("Project Name", ""))
        client = str(r.get("Client", ""))
        pc = str(r.get("PC", "-"))
        am = str(r.get("AM", "-"))
        sc = str(r.get("SC", "-"))
        status = str(r.get("Status", "Active"))
        p_jobs = str(r.get("Pending Jobs", "0"))
        p_bills = str(r.get("Pending Billables", "0"))
        
        proj_badge = f'<div style="width:26px; height:26px; border-radius:6px; background-color:#fee2e2; color:#dc2626; display:inline-flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:700; flex-shrink:0;">{pname[:2].upper()}</div>'
        
        row_html = f"""
        <tr style="background-color: #ffffff; border-bottom: 1px solid #f1f5f9; height: 46px;">
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; width: 40px;">{idx + 1}</td>
            <td style="padding: 8px 14px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    {proj_badge}
                    <div>
                        <div style="font-weight: 600; color: #0f172a; font-size: 0.86rem;">{html.escape(pname)}</div>
                        <div style="font-size: 0.74rem; color: #64748b;">{html.escape(client or '7Span Client')}</div>
                    </div>
                </div>
            </td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(pc, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(am, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(sc, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_status_pill(status)}</td>
            <td style="padding: 8px 14px; text-align: center; color: #0f172a; font-weight: 600; font-size: 0.84rem;">{p_jobs}</td>
            <td style="padding: 8px 14px; text-align: center; color: #0f172a; font-weight: 600; font-size: 0.84rem;">{p_bills}</td>
        </tr>
        """
        rows_html.append(row_html)
        
    table_content = "".join(rows_html)
    return f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', sans-serif;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; height: 38px;">
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">#</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Name</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">PC</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">AM</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">SC</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Status</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Pending Jobs</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Pending Billables</th>
                    </tr>
                </thead>
                <tbody>
                    {table_content}
                </tbody>
            </table>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background-color: #ffffff; border-top: 1px solid #f1f5f9; font-size: 0.8rem; color: #64748b;">
            <div>Showing 1 to {len(display_df)} of {len(df)} entries</div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; color: #94a3b8; cursor: not-allowed;">‹ Previous</span>
                <span style="padding: 3px 8px; background-color: #dc2626; color: white; border-radius: 4px; font-weight: 600;">1</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">Next ›</span>
            </div>
        </div>
    </div>
    """

def render_billables_table(df, limit: int = 25):
    """Renders pixel-perfect Everest Billables directory matching media_1789708516099.png"""
    if df is None or df.empty:
        return """<div style="padding:24px; text-align:center; color:#64748b; background:#fff; border-radius:8px; border:1px solid #e2e8f0;">No billables found.</div>"""
        
    rows_html = []
    display_df = df.head(limit)
    
    for idx, r in display_df.iterrows():
        bname = str(r.get("Billable Item", ""))
        status = str(r.get("Status", "Contracted"))
        amt = r.get("Amount (USD)", 0)
        try:
            amt_fmt = f"${float(amt):,.0f}" if float(amt) > 0 else "$0"
        except:
            amt_fmt = str(amt)
            
        proj = str(r.get("Project", ""))
        job = str(r.get("Job", "-"))
        b_date = str(r.get("Billing Date", "-"))
        due = str(r.get("Due Date", "-"))
        jc = str(r.get("JC", "-"))
        am = str(r.get("AM", "-"))
        sc = str(r.get("SC", "-"))
        
        row_html = f"""
        <tr style="background-color: #ffffff; border-bottom: 1px solid #f1f5f9; height: 46px;">
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; width: 35px;">{idx + 1}</td>
            <td style="padding: 8px 14px; font-weight: 600; color: #0f172a; font-size: 0.85rem; max-width: 220px;">{html.escape(bname)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_status_pill(status)}</td>
            <td style="padding: 8px 14px; text-align: center; color: #64748b;">$</td>
            <td style="padding: 8px 14px; font-weight: 600; color: #0f172a; font-size: 0.85rem; white-space: nowrap;">{amt_fmt}</td>
            <td style="padding: 8px 14px; color: #334155; font-size: 0.84rem;">{html.escape(proj)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem;">{html.escape(job)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; white-space: nowrap;">{html.escape(b_date)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; white-space: nowrap;">{html.escape(due)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(jc, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(am, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(sc, size=26)}</td>
        </tr>
        """
        rows_html.append(row_html)
        
    table_content = "".join(rows_html)
    return f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', sans-serif;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; height: 38px;">
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">#</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Name</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Status</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Type</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Amount</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Project</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Job</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Billing Date</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Due By</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">JC</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">AM</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">SC</th>
                    </tr>
                </thead>
                <tbody>
                    {table_content}
                </tbody>
            </table>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background-color: #ffffff; border-top: 1px solid #f1f5f9; font-size: 0.8rem; color: #64748b;">
            <div>Showing 1 to {len(display_df)} of {len(df)} entries</div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; color: #94a3b8; cursor: not-allowed;">‹ Previous</span>
                <span style="padding: 3px 8px; background-color: #dc2626; color: white; border-radius: 4px; font-weight: 600;">1</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">Next ›</span>
            </div>
        </div>
    </div>
    """

def render_overdue_table(df, limit: int = 25):
    """Renders pixel-perfect Everest Overdue & Extensions table matching media_1789708547862.png"""
    if df is None or df.empty:
        return """<div style="padding:24px; text-align:center; color:#64748b; background:#fff; border-radius:8px; border:1px solid #e2e8f0;">No overdue or extended billables found.</div>"""
        
    rows_html = []
    display_df = df.head(limit)
    
    for idx, r in display_df.iterrows():
        bname = str(r.get("Billable Item", ""))
        proj = str(r.get("Project", ""))
        job = str(r.get("Job", "-"))
        amt = r.get("Amount (USD)", 0)
        try:
            amt_fmt = f"${float(amt):,.0f}" if float(amt) > 0 else "$0"
        except:
            amt_fmt = str(amt)
        status = str(r.get("Status", "Billed"))
        orig_date = str(r.get("Original Date", "-"))
        ext_date = str(r.get("Extended Date", "-"))
        reason = str(r.get("Extension Reason", "Extended by client request"))
        jc = str(r.get("JC", "-"))
        pc = str(r.get("PC", "-"))
        
        row_html = f"""
        <tr style="background-color: #ffffff; border-bottom: 1px solid #f1f5f9; height: 52px;">
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; width: 35px;">{idx + 1}</td>
            <td style="padding: 8px 14px;">
                <div style="font-weight: 600; color: #0f172a; font-size: 0.85rem;">{html.escape(bname)}</div>
                <div style="color: #dc2626; font-size: 0.74rem; font-weight: 500; margin-top: 2px;">⚠️ {html.escape(reason)}</div>
            </td>
            <td style="padding: 8px 14px; color: #334155; font-size: 0.84rem; font-weight: 500;">{html.escape(proj)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem;">{html.escape(job)}</td>
            <td style="padding: 8px 14px; font-weight: 600; color: #0f172a; font-size: 0.85rem;">{amt_fmt}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_status_pill(status)}</td>
            <td style="padding: 8px 14px; color: #64748b; font-size: 0.82rem; white-space: nowrap;">{html.escape(orig_date)}</td>
            <td style="padding: 8px 14px; color: #dc2626; font-size: 0.82rem; font-weight: 600; white-space: nowrap;">{html.escape(ext_date)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(jc, size=26)}</td>
            <td style="padding: 8px 14px; text-align: center;">{render_avatar_circle(pc, size=26)}</td>
        </tr>
        """
        rows_html.append(row_html)
        
    table_content = "".join(rows_html)
    return f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', sans-serif;">
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 1px solid #e2e8f0; height: 38px;">
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">#</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Billable</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Project</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Job</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Amount</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">Status</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Original Date</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600;">Extended Date</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">JC</th>
                        <th style="padding: 6px 14px; color: #475569; font-size: 0.76rem; font-weight: 600; text-align: center;">PC</th>
                    </tr>
                </thead>
                <tbody>
                    {table_content}
                </tbody>
            </table>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background-color: #ffffff; border-top: 1px solid #f1f5f9; font-size: 0.8rem; color: #64748b;">
            <div>Showing 1 to {len(display_df)} of {len(df)} overdue extensions</div>
            <div style="display: flex; gap: 4px; align-items: center;">
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; color: #94a3b8; cursor: not-allowed;">‹ Previous</span>
                <span style="padding: 3px 8px; background-color: #dc2626; color: white; border-radius: 4px; font-weight: 600;">1</span>
                <span style="padding: 3px 8px; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer;">Next ›</span>
            </div>
        </div>
    </div>
    """

def render_quick_links_grid():
    """Renders pixel-perfect 4-column quick links grid matching media_1789708497073.png"""
    links = [
        ("What's New", "Check latest updates", "#fee2e2", "#dc2626", "📢"),
        ("Documentation", "Quick help", "#fee2e2", "#dc2626", "📚"),
        ("Case Study Finder", "Search case studies", "#fee2e2", "#dc2626", "🔍"),
        ("Feedback & Support Form", "Submit anonymous response", "#fee2e2", "#dc2626", "✍️"),
        ("Manpower Requisition Form", "Resource planning", "#fee2e2", "#dc2626", "📋"),
        ("Company Policies", "Company policy & SOPs", "#fee2e2", "#dc2626", "🛡️"),
        ("Pacific", "Find company info", "#fee2e2", "#dc2626", "🌊"),
        ("Sahara", "Project management tool", "#fee2e2", "#dc2626", "🏜️"),
        ("Discord", "Team chat and calls", "#ede9fe", "#7c3aed", "💬"),
        ("Draw.io", "Create diagrams easily", "#ffedd5", "#ea580c", "📐"),
        ("GitHub", "Collaborate on code", "#f1f5f9", "#0f172a", "🐙"),
        ("Gmail", "Access work emails", "#fee2e2", "#ea4335", "✉️"),
        ("Instagram", "View company posts", "#fce7f3", "#db2777", "📸"),
        ("Keka", "Track hours and payroll", "#dbeafe", "#2563eb", "⏰"),
        ("LinkedIn", "Build your network", "#e0f2fe", "#0284c7", "💼"),
        ("Passbolt", "Get shared passwords", "#fee2e2", "#dc2626", "🔑"),
        ("X", "Follow updates and news", "#f1f5f9", "#000000", "𝕏"),
    ]
    
    cards_html = []
    for title, sub, bg, icon_col, icon in links:
        card = f"""
        <div style="background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px; display: flex; align-items: center; gap: 14px; transition: all 0.15s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.03); cursor: pointer;">
            <div style="width: 42px; height: 42px; border-radius: 10px; background-color: {bg}; color: {icon_col}; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; flex-shrink: 0;">
                {icon}
            </div>
            <div style="min-width: 0;">
                <div style="font-weight: 600; font-size: 0.92rem; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{title}</div>
                <div style="font-size: 0.76rem; color: #6b7280; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{sub}</div>
            </div>
        </div>
        """
        cards_html.append(card)
        
    grid_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; margin-top: 14px;">
        {''.join(cards_html)}
    </div>
    """
    return grid_html

def render_inbox_table(notifications, active_tab: str = "Pending", active_category: str = "All"):
    """
    Renders pixel-perfect Everest Inbox view matching user screenshot media_1789739354640.png
    """
    filtered = []
    for n in notifications:
        if active_tab != "All" and n.get("status") != active_tab:
            continue
        if active_category != "All" and n.get("category") != active_category:
            continue
        filtered.append(n)
        
    rows_html = []
    for n in filtered:
        title = html.escape(str(n.get("title", "")))
        desc = html.escape(str(n.get("message", "")))
        time_str = html.escape(str(n.get("time", "")))
        icon = n.get("icon", "💼")
        
        row_html = f"""
        <div style="display: flex; align-items: flex-start; gap: 14px; padding: 14px 18px; border-bottom: 1px solid #f1f5f9; background-color: #ffffff; transition: background 0.12s ease; cursor: pointer;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='#ffffff'">
            <div style="padding-top: 2px;">
                <input type="checkbox" style="cursor: pointer; width: 15px; height: 15px; accent-color: #dc2626; border-radius: 4px;" />
            </div>
            <div style="color: #64748b; font-size: 1.05rem; padding-top: 1px; flex-shrink: 0;">
                {icon}
            </div>
            <div style="min-width: 220px; max-width: 240px; flex-shrink: 0;">
                <div style="font-weight: 600; color: #0f172a; font-size: 0.88rem; line-height: 1.35;">
                    {title}
                </div>
            </div>
            <div style="flex-grow: 1; min-width: 0; padding: 0 10px;">
                <div style="color: #475569; font-size: 0.85rem; line-height: 1.45;">
                    {desc}
                </div>
            </div>
            <div style="white-space: nowrap; text-align: right; color: #64748b; font-size: 0.80rem; flex-shrink: 0; padding-top: 2px;">
                {time_str}
            </div>
        </div>
        """
        rows_html.append(row_html)
        
    if not rows_html:
        rows_html.append("""
        <div style="padding: 40px; text-align: center; color: #64748b; font-size: 0.9rem;">
            🎉 All caught up! No pending notifications in this category.
        </div>
        """)
        
    inbox_container = f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', sans-serif;">
        <!-- Top Action Bar matching media_1789739354640.png -->
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 18px; background-color: #ffffff; border-bottom: 1px solid #f1f5f9;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <input type="checkbox" style="cursor: pointer; width: 15px; height: 15px; accent-color: #dc2626;" title="Select all" />
                <span style="font-size: 0.95rem; color: #64748b; cursor: pointer;" title="Refresh">🔄</span>
            </div>
            <div style="font-size: 0.82rem; color: #64748b;">
                Showing <b>{len(filtered)}</b> notifications
            </div>
        </div>
        
        <!-- Notification list items -->
        <div>
            {''.join(rows_html)}
        </div>
    </div>
    """
    return inbox_container
