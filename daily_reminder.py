#!/usr/bin/env python3
"""
Automated Daily Task/Work Log Reminder System
Author: Antigravity Assistant

This Python application automates daily task update checking and email reminders
for team members operating across different timezones (India, UAE, Saudi Arabia).

Features:
- Dynamically loads Employee Config from Excel / MS Graph API or local file.
- Evaluates individual employee local time & working day schedule.
- Checks daily task completion at 18:30 (First Reminder) and 18:45 (Final Reminder).
- Re-checks Excel sheet before 18:45 reminder to avoid duplicate emails.
- Sends custom HTML/text email notifications via MS Graph API or SMTP.
- Built-in dry-run and single-employee test modes.
"""

import os
import sys
import json
import argparse
import datetime
from typing import Dict, List, Optional, Tuple

# Third-party dependencies
try:
    import pytz
except ImportError:
    print("[ERROR] Missing required package 'pytz'. Install via: pip install pytz")
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    openpyxl = None  # Handled gracefully if using MS Graph API or mock data

TIMEZONE_MAP = {
    "India Standard Time": "Asia/Kolkata",
    "Arabian Standard Time": "Asia/Dubai",
    "Arab Standard Time": "Asia/Riyadh"
}

DAY_NAME_MAP = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun"
}

DEFAULT_CONFIG = {
    "excel_file_path": "Daily Task and Update Sheet.xlsx",
    "employee_config_sheet": "EmployeeConfig",
    "table_name": "EmployeeConfig",
    "test_employee": None,
    "dry_run": False,
    "smtp": {
        "enabled": False,
        "server": "smtp.office365.com",
        "port": 587,
        "username": "",
        "password": ""
    },
    "graph_api": {
        "enabled": False,
        "tenant_id": "",
        "client_id": "",
        "client_secret": "",
        "user_email": "Ravi@d2backoffice.onmicrosoft.com"
    }
}

class Employee:
    def __init__(self, name: str, email: str, location: str, timezone_str: str, working_days: str, sheet_name: str, manager_cc: str, reminders: Optional[List[str]] = None):
        self.name = name.strip()
        self.email = email.strip()
        self.location = location.strip()
        self.timezone_str = timezone_str.strip()
        self.working_days = [d.strip() for d in working_days.split(",") if d.strip()]
        self.sheet_name = sheet_name.strip()
        self.manager_cc = manager_cc.strip()
        self.reminders = reminders or ["18:30", "18:45", "19:00"]

    def get_local_now(self) -> datetime.datetime:
        iana_tz = None
        # 1. Direct IANA check (e.g. Asia/Kolkata, Asia/Dubai, Asia/Riyadh, America/New_York)
        if self.timezone_str:
            try:
                pytz.timezone(self.timezone_str)
                iana_tz = self.timezone_str
            except Exception:
                pass

        # 2. Map lookup
        if not iana_tz:
            iana_tz = TIMEZONE_MAP.get(self.timezone_str)

        # 3. Database Locations lookup
        if not iana_tz:
            try:
                import database
                locs = database.get_all_locations()
                for l in locs:
                    if l.get("ianaTz") and (l.get("timezoneName") == self.timezone_str or l.get("country", "").lower() == self.location.lower() or l.get("name", "").lower() == self.location.lower() or l.get("id") == self.location):
                        iana_tz = l.get("ianaTz")
                        break
            except Exception:
                pass

        # 4. Keyword Fallback
        if not iana_tz:
            loc_lower = self.location.lower()
            tz_lower = self.timezone_str.lower()
            if "india" in loc_lower or "ist" in tz_lower:
                iana_tz = "Asia/Kolkata"
            elif "uae" in loc_lower or "dubai" in loc_lower or "gst" in tz_lower:
                iana_tz = "Asia/Dubai"
            elif "saudi" in loc_lower or "riyadh" in loc_lower or "ast" in tz_lower:
                iana_tz = "Asia/Riyadh"
            elif "usa" in loc_lower or "est" in tz_lower or "new_york" in tz_lower:
                iana_tz = "America/New_York"
            elif "uk" in loc_lower or "gmt" in tz_lower or "london" in tz_lower:
                iana_tz = "Europe/London"
            else:
                iana_tz = "UTC"

        tz = pytz.timezone(iana_tz)
        return datetime.datetime.now(pytz.utc).astimezone(tz)

    def get_local_date_str(self, dt: Optional[datetime.datetime] = None) -> str:
        local_dt = dt or self.get_local_now()
        # Format matching Excel cell: e.g. 15-Sep-26
        return local_dt.strftime("%d-%b-%y")

    def get_local_day_str(self, dt: Optional[datetime.datetime] = None) -> str:
        local_dt = dt or self.get_local_now()
        return DAY_NAME_MAP[local_dt.weekday()]

    def is_working_day(self, dt: Optional[datetime.datetime] = None) -> bool:
        current_day = self.get_local_day_str(dt)
        return current_day in self.working_days

    def get_local_time_str(self, dt: Optional[datetime.datetime] = None) -> str:
        local_dt = dt or self.get_local_now()
        return local_dt.strftime("%H:%M")

import urllib.request
import urllib.parse

def parse_args():
    parser = argparse.ArgumentParser(description="Daily Task Log Reminder System")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--test-employee", help="Run reminder check for a single employee only (e.g. 'Sachin' or 'Naseef')")
    parser.add_argument("--dry-run", action="store_true", help="Perform checks without sending actual emails")
    parser.add_argument("--force-time", help="Force local time for testing (e.g. '18:30' or '18:45')")
    parser.add_argument("--force-date", help="Force date string for testing (e.g. '15-Sep-26')")
    parser.add_argument("--excel-file", help="Path to local Excel workbook file")
    parser.add_argument("--sharepoint-url", help="SharePoint direct sharing URL for Excel file")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop (ideal for Docker daemon)")
    parser.add_argument("--interval", type=int, default=900, help="Loop interval in seconds (default: 900s / 15 minutes)")
    return parser.parse_args()

def download_sharepoint_file(url: str, dest_path: str) -> bool:
    """Downloads Excel file from SharePoint sharing URL."""
    if not url:
        return False
    try:
        download_url = url
        if "download=1" not in download_url:
            separator = "&" if "?" in download_url else "?"
            download_url += f"{separator}download=1"

        print(f"[SHAREPOINT] Fetching latest Excel file from SharePoint URL...")
        req = urllib.request.Request(download_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            if len(content) > 1000:  # Valid file response
                with open(dest_path, "wb") as f:
                    f.write(content)
                print(f"[SUCCESS] Downloaded latest Excel file to '{dest_path}' ({len(content)} bytes).")
                return True
            else:
                print(f"[WARN] Received small or unexpected response from SharePoint link.")
    except Exception as e:
        print(f"[WARN] Could not auto-download from SharePoint URL: {e}")
    return False

def check_task_sheet_local(file_path: str, sheet_name: str, target_date: str, employee_name: str, ignore_checks: bool = False) -> bool:
    """
    Checks local Excel sheet & SQLite Web Task Submissions database to determine if employee has filled their task details.
    Returns True if filled (reminder suppressed), False if blank/missing.
    """
    if ignore_checks:
        print(f"[TEST TRIGGER] Force testing enabled for employee '{employee_name}'. Bypassing leave/weekoff/completed task suppression checks.")
    else:
        # 1. First check Web Form SQLite Task Submissions & On Leave status
        try:
            today_iso = datetime.datetime.now().strftime("%Y-%m-%d")
            if database.is_employee_week_off(employee_name, target_date) or database.is_employee_week_off(employee_name, today_iso):
                print(f"[WEEK OFF] Employee '{employee_name}' is on WEEK OFF for '{target_date}'. Suppressing reminder email.")
                return True
            if database.is_employee_on_leave(employee_name, target_date) or database.is_employee_on_leave(employee_name, today_iso):
                print(f"[ON LEAVE] Employee '{employee_name}' is ON LEAVE for '{target_date}'. Suppressing reminder email.")
                return True
            if database.is_employee_task_filled(employee_name, target_date) or database.is_employee_task_filled(employee_name, today_iso):
                print(f"[SQLITE TASK SUBMISSION] Employee '{employee_name}' has submitted daily task log via Web Form for '{target_date}'. Suppressing reminder email.")
                return True
        except Exception as e:
            print(f"[WARN] Could not check SQLite task_logs: {e}")

    # 2. Check local Excel file if openpyxl available
    if not openpyxl:
        print("[WARN] openpyxl not installed. Assuming cell is blank for testing.")
        return False

    if not os.path.exists(file_path):
        print(f"[WARN] Excel file '{file_path}' not found. Returning blank for '{employee_name}'.")
        return False

    wb = openpyxl.load_workbook(file_path, data_only=True)
    if sheet_name not in wb.sheetnames:
        print(f"[ERROR] Sheet '{sheet_name}' not found in workbook.")
        return False

    ws = wb[sheet_name]
    
    # Row 2 contains employee names starting from column B (col 2)
    emp_col_idx = -1
    for col in range(2, ws.max_column + 1):
        cell_val = ws.cell(row=2, column=col).value
        if cell_val and str(cell_val).strip().lower() == employee_name.lower():
            emp_col_idx = col
            break

    if emp_col_idx == -1:
        print(f"[WARN] Employee '{employee_name}' not found in Row 2 of sheet '{sheet_name}'.")
        return False

    # Find row in Column A matching target_date
    target_row = -1
    for row in range(3, ws.max_row + 1):
        cell_val = ws.cell(row=row, column=1).value
        if cell_val is None:
            continue

        cell_str = str(cell_val).strip()
        if isinstance(cell_val, (datetime.datetime, datetime.date)):
            cell_str = cell_val.strftime("%d-%b-%y")

        if cell_str.lower() == target_date.lower() or target_date.lower() in cell_str.lower():
            target_row = row
            break

    if target_row == -1:
        print(f"[WARN] Date '{target_date}' not found in Column A of sheet '{sheet_name}'.")
        return False

    task_cell_val = ws.cell(row=target_row, column=emp_col_idx).value
    if task_cell_val and str(task_cell_val).strip():
        return True  # Completed
    return False     # Missing

MOTIVATIONAL_QUOTES = [
    "Consistent progress each day builds long-term success.",
    "A well-organized finish ensures a productive start tomorrow.",
    "Rest and balance are essential for sustained excellence.",
    "Small daily improvements over time lead to stunning results.",
    "Excellence is not an act, but a habit.",
    "Focus on being productive instead of busy.",
    "Success is the sum of small efforts repeated day in and day out.",
    "The secret of getting ahead is getting started and finishing strong.",
    "Great things are done by a series of small things brought together.",
    "Efficiency is doing better what is already being done.",
    "Order and organization simplify teamwork and accelerate progress.",
    "Finish today strong so tomorrow starts with momentum.",
    "Clarity and communication are the pillars of great engineering.",
    "Dedication today empowers innovation tomorrow."
]

import random

STAGE_CATEGORY_MAP = {
    "first": "Focus, Progress & Consistency",
    "second": "Teamwork, Impact & Reliability",
    "final": "Recharge, Balance & Perspective",
    "ignore_filled": "Focus, Progress & Consistency"
}

def get_daily_quote(reminder_stage: str = "first", date_str: str = "") -> str:
    """Returns a dynamic, randomly selected motivational quote matching stage category day-wise and time-wise."""
    target_category = STAGE_CATEGORY_MAP.get(reminder_stage, "Focus, Progress & Consistency")
    stage_quotes = []
    all_quotes = []

    try:
        import database
        db_quotes = database.get_all_quotes()
        if db_quotes:
            for q in db_quotes:
                text = q.get("quote", "").strip()
                cat = q.get("category", "").strip()
                if text:
                    all_quotes.append(text)
                    if cat.lower() == target_category.lower():
                        stage_quotes.append(text)
    except Exception:
        pass

    if stage_quotes:
        return random.choice(stage_quotes)
    elif all_quotes:
        return random.choice(all_quotes)
    return random.choice(MOTIVATIONAL_QUOTES)

def build_email_content(reminder_type: str, employee_name: str, date_str: str) -> Tuple[str, str]:
    """Generates polite email subject and body for reminders using SQLite database templates."""
    raw_quote = get_daily_quote(reminder_type, date_str).strip(' "\'')
    quote = f"💡 THOUGHT OF THE DAY:\n\"{raw_quote}\""
    
    try:
        import database
        templates = database.get_all_templates()
        key_map = {
            "first": "first_reminder",
            "second": "second_reminder",
            "final": "final_reminder",
            "ignore": "ignore_filled",
            "ignore_filled": "ignore_filled"
        }
        tpl_key = key_map.get(reminder_type, reminder_type if reminder_type in templates else "first_reminder")
        if tpl_key in templates:
            tpl = templates[tpl_key]
            subject = tpl.get("subject", "").replace("{date}", date_str).replace("{name}", employee_name).replace("{quote}", quote)
            body = tpl.get("body", "").replace("{date}", date_str).replace("{name}", employee_name).replace("{quote}", quote)
            ignore_note = tpl.get("ignore_note", "").replace("{date}", date_str).replace("{name}", employee_name).replace("{quote}", quote)
            
            # Clean up any stray quotes around quote placeholder
            body = body.replace('""💡', '💡').replace('""', '"')

            # If ignore_note exists and is not already part of the body, append it politely
            if ignore_note and ignore_note.lower() not in body.lower():
                if not ignore_note.startswith("Note:"):
                    ignore_note = f"Note: {ignore_note}"
                body += f"\n\n{ignore_note}"
            return subject, body
    except Exception as e:
        print(f"[WARN] Error loading custom email templates from SQLite: {e}")

    # Fallback Templates matching specific 3-reminder stages
    if reminder_type == "first":
        subject = f"Friendly Reminder: End-of-Day Transition & Task Log - {date_str}"
        body = f"""{quote}

Hi {employee_name},

As our shift approaches the final 30 minutes, please begin winding down your current tasks:

• Commit your code changes and update assigned board tickets.
• Fill out your daily work logs and project status updates.
• Note any pending blockers for tomorrow's standup.

Note: If you have already submitted your daily updates, please disregard this notice.

Warm regards,
IT & Infrastructure Team"""

    elif reminder_type == "second":
        subject = f"Gentle Reminder: Wrap-Up & Documentation - {date_str}"
        body = f"""{quote}

Hi {employee_name},

We are 15 minutes away from the end of the shift:

• Please ensure your daily task reports and timesheets are submitted.
• Hand over any critical alerts, ongoing deployments, or notes to shift leads.
• Safely close non-essential sessions and test instances.

Note: Kindly ignore this reminder if your documentation and status are already submitted.

Warm regards,
IT & Infrastructure Team"""

    elif reminder_type in ("ignore", "ignore_filled"):
        subject = f"Status Confirmation: Daily Log Hours Recorded - {date_str}"
        body = f"""{quote}

Dear {employee_name},

Thank you for updating your daily work log hours for today ({date_str}).

Your daily time logs have been verified as filled in the Daily Task and Update Sheet. You may safely ignore any reminder notifications sent for today.

Thank you for keeping your daily project records up to date!

Warm regards,
IT & Infrastructure Team"""

    else:  # Final / 3rd reminder at shift close
        subject = f"Final Call: Shift Close & Daily Log Submission - {date_str}"
        body = f"""{quote}

Good evening {employee_name},

The shift has concluded for the day:

• Thank you for your hard work and commitment today.
• Please ensure all systems are securely logged out and take time to disconnect and recharge.

Note: If your daily reports are already submitted, please ignore this message. Have a great evening!

Warm regards,
IT & Infrastructure Team"""

    return subject, body

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_logo_b64() -> str:
    """Reads website logo image and encodes to base64 for embedding directly into HTML emails."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "static", "images", "app_logo.png")
        if os.path.exists(logo_path):
            import base64
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"[WARN] Error reading app logo for email header: {e}")
    return ""

def generate_html_email(body_text: str) -> str:
    """Converts email body string into rich HTML formatted email matching sample layout with header logo."""
    lines = body_text.split("\n")
    html_parts = []
    in_bullets = False

    logo_b64 = get_logo_b64()
    logo_header = ""
    if logo_b64:
        logo_header = f'''<div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #e2e8f0; text-align: left;">
    <img src="data:image/png;base64,{logo_b64}" alt="TickTask Logo" style="max-height: 48px; max-width: 220px; height: auto; width: auto; display: block;" />
</div>'''

    for line in lines:
        stripped = line.strip()

        # 1. Thought of the Day Header with Yellow Highlight
        if "THOUGHT OF THE DAY:" in line or "Thought of the Day:" in line:
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append('<div style="margin-bottom: 8px;"><span style="background-color: #ffff00; color: #000000; font-weight: bold; padding: 2px 6px; font-family: Arial, sans-serif; font-size: 13px;">💡 THOUGHT OF THE DAY:</span></div>')

        # 2. Quote string in bold
        elif stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 5:
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append(f'<div style="font-weight: bold; font-size: 15px; color: #0f172a; margin-bottom: 20px; font-family: Arial, sans-serif;">{stripped}</div>')

        # 3. Note / Disclaimer line in bold
        elif stripped.startswith("Note:") or stripped.startswith("If you have already") or stripped.startswith("Kindly ignore"):
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append(f'<p style="margin-top: 18px; margin-bottom: 16px; font-family: Arial, sans-serif; font-size: 14px;"><strong>{stripped}</strong></p>')

        # 4. Bullet points
        elif stripped.startswith("•") or stripped.startswith("-") or stripped.startswith("* "):
            if not in_bullets:
                html_parts.append('<ul style="margin-top: 8px; margin-bottom: 16px; padding-left: 20px; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">')
                in_bullets = True
            bullet_text = stripped.lstrip("•-* ").strip()
            html_parts.append(f'<li style="margin-bottom: 4px;">{bullet_text}</li>')

        elif stripped == "":
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append('<br>')

        else:
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append(f'<p style="margin: 6px 0; font-family: Arial, sans-serif; font-size: 14px; color: #1e293b;">{line}</p>')

    if in_bullets:
        html_parts.append("</ul>")

    html_content = "".join(html_parts)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #1e293b; line-height: 1.6; padding: 16px; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
{logo_header}
{html_content}
</body>
</html>"""

def load_config(config_path: str) -> dict:
    """Loads settings from SQLite database or fallback config."""
    try:
        import database
        cfg = database.get_system_settings()
        if cfg and cfg.get("user_credentials", {}).get("password"):
            return cfg
    except Exception as e:
        print(f"[WARN] Error loading settings from SQLite: {e}")

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "excel_file_path": "Daily Task and Update Sheet.xlsx",
        "sharepoint_url": "https://d2backoffice-my.sharepoint.com/:x:/g/personal/ravi_d2backoffice_onmicrosoft.com/IQCybiwws57qSpGmQ9RdBx_RAaKEOarut68jb1ZFs7NK0PQ?e=1wwbfr",
        "user_credentials": {
            "email": "support@digital-twin-solutions.com",
            "password": "1)T1h6Xzyo{kn"
        },
        "smtp": {
            "enabled": True,
            "server": "mail.digital-twin-solutions.com",
            "port": 465,
            "username": "support@digital-twin-solutions.com",
            "password": "1)T1h6Xzyo{kn"
        }
    }

def send_email(to_email: str, cc_email: str, subject: str, body: str, dry_run: bool = False, config: Optional[dict] = None, html_body: Optional[str] = None) -> bool:
    """Handles sending email notifications via SSL 465 / TLS 587 SMTP using manager or default credentials."""
    import database

    # Look up manager-specific SMTP account by CC email (manager's email)
    manager_smtp = database.get_smtp_account_for_manager(cc_email)
    
    if manager_smtp and manager_smtp.get("email") and manager_smtp.get("server"):
        sender_email = manager_smtp.get("email")
        sender_password = manager_smtp.get("password")
        smtp_server = manager_smtp.get("server")
        smtp_port = int(manager_smtp.get("port", 465))
        smtp_account_name = manager_smtp.get("name") or sender_email
    else:
        cfg = config or database.get_system_settings()
        user_creds = cfg.get("user_credentials", {})
        smtp_cfg = cfg.get("smtp", {})
        sender_email = user_creds.get("email") or smtp_cfg.get("username") or "support@digital-twin-solutions.com"
        sender_password = user_creds.get("password") or smtp_cfg.get("password") or "1)T1h6Xzyo{kn"
        smtp_server = smtp_cfg.get("server") or "mail.digital-twin-solutions.com"
        smtp_port = int(smtp_cfg.get("port", 465))
        smtp_account_name = "Default System SMTP"

    # Always ensure sender_password is decrypted plaintext
    if sender_password:
        sender_password = database.decrypt_password(sender_password)

    print(f"\n--- [EMAIL DISPATCH via {smtp_account_name} ({smtp_server}:{smtp_port})] ---")
    print(f"FROM:    {sender_email}")
    print(f"TO:      {to_email}")
    print(f"CC:      {cc_email}")
    print(f"SUBJECT: {subject}")
    print(f"BODY:\n{body}")
    print("------------------------")

    if dry_run:
        print("[DRY-RUN MODE] Email simulated successfully (no real email sent).")
        try:
            import database
            database.record_reminder_history(to_email.split('@')[0], to_email, "SIMULATED", "DRY_RUN", datetime.datetime.now().strftime("%d-%b-%y"))
        except Exception:
            pass
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg['From'] = sender_email
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
            msg['Reply-To'] = cc_email
        msg['Subject'] = subject

        # Attach Plain Text Fallback & Rich HTML Version
        final_html = html_body if html_body else generate_html_email(body)
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(final_html, 'html'))

        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)

        print(f"[SMTP] Connecting to {smtp_server}:{smtp_port}...")
        sent = False
        last_err = None

        ports_to_try = [smtp_port]
        if smtp_port == 465 and 587 not in ports_to_try:
            ports_to_try.append(587)
        elif smtp_port == 587 and 465 not in ports_to_try:
            ports_to_try.append(465)

        for attempt_port in ports_to_try:
            try:
                print(f"[SMTP] Attempting connection to {smtp_server}:{attempt_port}...")
                if attempt_port == 465:
                    with smtplib.SMTP_SSL(smtp_server, attempt_port, timeout=15) as server:
                        server.login(sender_email, sender_password)
                        server.sendmail(sender_email, recipients, msg.as_string())
                        sent = True
                        smtp_port = attempt_port
                        break
                else:
                    with smtplib.SMTP(smtp_server, attempt_port, timeout=15) as server:
                        server.starttls()
                        server.login(sender_email, sender_password)
                        server.sendmail(sender_email, recipients, msg.as_string())
                        sent = True
                        smtp_port = attempt_port
                        break
            except Exception as err:
                last_err = err
                print(f"[SMTP WARN] Connection to {smtp_server}:{attempt_port} failed: {err}")

        if not sent:
            raise last_err or Exception("All SMTP connection attempts failed.")

        print(f"[SUCCESS] Real email dispatched successfully via SMTP ({smtp_server}:{smtp_port}) to {to_email}!")

        try:
            import database
            database.record_reminder_history(to_email.split('@')[0], to_email, "REMINDER", "SENT_SUCCESS", datetime.datetime.now().strftime("%d-%b-%y"), f"Sent via {smtp_server}:{smtp_port}")
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email via SMTP ({smtp_server}): {e}")
        try:
            import database
            database.record_reminder_history(to_email.split('@')[0], to_email, "REMINDER", "FAILED", datetime.datetime.now().strftime("%d-%b-%y"), str(e))
        except Exception:
            pass
        return False

def run_reminder_cycle(args, sample_employees):
    config = load_config(args.config)
    test_target = args.test_employee or config.get("test_employee")
    dry_run_mode = args.dry_run or config.get("dry_run", False)

    if test_target:
        print(f"[TEST MODE] Filtering execution for employee: '{test_target}'")
    if dry_run_mode:
        print("[DRY-RUN MODE] Active. No emails will be sent.")

    for emp in sample_employees:
        # Filter for single-employee test if specified (with flexible name matching)
        clean_emp_name = emp.name.split(" (")[0].strip().lower()
        clean_test_target = test_target.split(" (")[0].strip().lower() if test_target else ""
        if test_target and clean_emp_name != clean_test_target and clean_test_target not in clean_emp_name and clean_emp_name not in clean_test_target:
            continue

        local_now = emp.get_local_now()
        local_day = emp.get_local_day_str(local_now)
        local_date = args.force_date or emp.get_local_date_str(local_now)
        local_time = args.force_time or emp.get_local_time_str(local_now)

        print(f"\nProcessing Employee: {emp.name}")
        print(f"  Location / TZ:    {emp.location} ({emp.timezone_str})")
        print(f"  Local Time:       {local_now.strftime('%Y-%m-%d %H:%M:%S')} ({local_day})")
        print(f"  Working Days:     {','.join(emp.working_days)}")

        # 1. Evaluate Working Day (bypass when manually triggering a test)
        if not emp.is_working_day(local_now) and not test_target:
            print(f"  --> Status: SKIP ({local_day} is an OFF DAY for {emp.name}).")
            continue

        # 2. Evaluate Dynamic Shift Time Window
        rem_times = getattr(emp, 'reminders', None) or ["18:30", "18:45", "19:00"]
        reminder_type = None

        if len(rem_times) >= 1 and local_time == rem_times[0]:
            reminder_type = "first"
        elif len(rem_times) >= 2 and local_time == rem_times[1]:
            reminder_type = "second"
        elif len(rem_times) >= 3 and local_time == rem_times[2]:
            reminder_type = "final"

        if not reminder_type and not args.force_time and not test_target:
            print(f"  --> Status: SKIP (Current local time {local_time} does not match shift trigger times {rem_times}).")
            continue

        if (args.force_time or test_target) and not reminder_type:
            reminder_type = "first"

        print(f"  --> Time Window Matched: {reminder_type.upper()} REMINDER ({local_time})")

        # 3. Check Excel Sheet (Fetch latest from SharePoint if configured)
        excel_path = args.excel_file or config.get("excel_file_path", "Daily Task and Update Sheet.xlsx")
        sp_url = args.sharepoint_url or config.get("sharepoint_url")
        if sp_url:
            download_sharepoint_file(sp_url, excel_path)

        is_completed = check_task_sheet_local(excel_path, emp.sheet_name, local_date, emp.name, ignore_checks=bool(test_target))

        if is_completed and not test_target:
            print(f"  --> Task Check Result: COMPLETED! Employee updated their sheet for {local_date}.")
            print(f"  --> Status: NO EMAIL REQUIRED.")
        else:
            if test_target:
                print(f"  --> [TEST TRIGGER FORCE SEND] Sending test reminder email to {emp.email} (CC: {emp.manager_cc}).")
            else:
                print(f"  --> Task Check Result: BLANK / MISSING for {local_date}.")
            subject, body = build_email_content(reminder_type, emp.name, local_date)
            send_email(emp.email, emp.manager_cc, subject, body, dry_run=dry_run_mode, config=config)

def main():
    import time
    args = parse_args()
    
    # Employee Configuration matching Excel image table
    sample_employees = [
        Employee("Sachin", "sachin@d2backoffice.onmicrosoft.com", "India", "India Standard Time", "Mon,Tue,Wed,Thu,Fri,Sat", "Technical Infra Team-Aug-2026", "Ravi@d2backoffice.onmicrosoft.com"),
        Employee("Ganesh", "ganesh@d2backoffice.onmicrosoft.com", "India", "India Standard Time", "Mon,Tue,Wed,Thu,Fri,Sat", "Technical Infra Team-Aug-2026", "Ravi@d2backoffice.onmicrosoft.com"),
        Employee("Amin", "amin@d2backoffice.onmicrosoft.com", "Saudi", "Arab Standard Time", "Sun,Mon,Tue,Wed,Thu", "Technical Infra Team-Aug-2026", "Ravi@d2backoffice.onmicrosoft.com"),
        Employee("Naseef", "naseef@d2backoffice.onmicrosoft.com", "UAE", "Arabian Standard Time", "Mon,Tue,Wed,Thu,Fri,Sat", "Technical Infra Team-Aug-2026", "Ravi@d2backoffice.onmicrosoft.com"),
        Employee("Senthil", "senthil@d2backoffice.onmicrosoft.com", "India", "India Standard Time", "Mon,Tue,Wed,Thu,Fri,Sat", "Technical Infra Team-Aug-2026", "Ravi@d2backoffice.onmicrosoft.com"),
    ]

    if args.loop:
        print(f"[DAEMON MODE] Running continuously every {args.interval} seconds...")
        while True:
            print(f"\n==================================================")
            print(f" AUTOMATED DAILY TASK REMINDER ENGINE (CYCLE: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}) ")
            print(f"==================================================")
            run_reminder_cycle(args, sample_employees)
            print(f"\nSleeping for {args.interval} seconds...")
            time.sleep(args.interval)
    else:
        print("==================================================")
        print(" AUTOMATED DAILY TASK REMINDER ENGINE ")
        print("==================================================")
        run_reminder_cycle(args, sample_employees)
        print("\n==================================================")
        print(" REMINDER PROCESSING COMPLETE ")
        print("==================================================")

if __name__ == "__main__":
    main()
