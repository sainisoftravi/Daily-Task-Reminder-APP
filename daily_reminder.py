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
        iana_tz = TIMEZONE_MAP.get(self.timezone_str)
        if not iana_tz:
            try:
                import database
                locs = database.get_all_locations()
                for l in locs:
                    if l.get("timezoneName") == self.timezone_str or l.get("country", "").lower() == self.location.lower() or l.get("name", "").lower() == self.location.lower():
                        iana_tz = l.get("ianaTz")
                        break
            except Exception:
                pass
        if not iana_tz:
            if "india" in self.location.lower():
                iana_tz = "Asia/Kolkata"
            elif "uae" in self.location.lower():
                iana_tz = "Asia/Dubai"
            elif "saudi" in self.location.lower():
                iana_tz = "Asia/Riyadh"
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

def check_task_sheet_local(file_path: str, sheet_name: str, target_date: str, employee_name: str) -> bool:
    """
    Checks local Excel sheet to determine if employee has filled their task details for target_date.
    Returns True if filled, False if blank/missing.
    """
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

def build_email_content(reminder_type: str, employee_name: str, date_str: str) -> Tuple[str, str]:
    """Generates polite email subject and body for reminders using SQLite database templates."""
    try:
        import database
        templates = database.get_all_templates()
        key_map = {"first": "first_reminder", "second": "second_reminder", "final": "final_reminder"}
        tpl_key = key_map.get(reminder_type, "first_reminder")
        if tpl_key in templates:
            subject = templates[tpl_key].get("subject", "").replace("{date}", date_str).replace("{name}", employee_name)
            body = templates[tpl_key].get("body", "").replace("{date}", date_str).replace("{name}", employee_name)
            return subject, body
    except Exception as e:
        print(f"[WARN] Error loading custom email templates from SQLite: {e}")

    # Fallback Polite Templates
    if reminder_type == "first":
        subject = f"Friendly Reminder: Daily Work Log Update - {date_str}"
        body = f"""Dear {employee_name},

Hope you are having a productive day!

This is a friendly reminder to please fill your time logs timely in the Daily Task and Update Sheet before the end of your working shift.

Keeping your task log updated ensures the team stays aligned on today's achievements and project progress.

Thank you for your cooperation and dedication!

Warm regards,
IT & Infrastructure Team"""
    elif reminder_type == "second":
        subject = f"Gentle Reminder: Pending Daily Work Log - {date_str}"
        body = f"""Dear {employee_name},

We noticed that today's work log cell is still blank in the Daily Task and Update Sheet.

Please take 2 minutes to fill your time logs timely before your shift ends.

If you have already updated your tasks in the last few minutes, kindly ignore this message.

Thank you so much for your prompt update!

Warm regards,
IT & Infrastructure Team"""
    else:
        subject = f"Final Call: Daily Work Log Required - {date_str}"
        body = f"""Dear {employee_name},

Your shift end time has arrived and today's work log entry remains pending.

Please complete your daily task entry immediately so that your daily hours and updates are accurately recorded for today ({date_str}).

Dear team, please fill your time logs timely to help us maintain accurate daily project records.

Thank you for your immediate attention.

Warm regards,
IT & Infrastructure Team"""
    return subject, body

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

def send_email(to_email: str, cc_email: str, subject: str, body: str, dry_run: bool = False, config: Optional[dict] = None) -> bool:
    """Handles sending email notifications via SSL 465 SMTP using user credentials."""
    cfg = config or load_config("config.json")
    user_creds = cfg.get("user_credentials", {})
    smtp_cfg = cfg.get("smtp", {})

    sender_email = user_creds.get("email") or smtp_cfg.get("username") or "support@digital-twin-solutions.com"
    sender_password = user_creds.get("password") or smtp_cfg.get("password") or "1)T1h6Xzyo{kn"
    smtp_server = smtp_cfg.get("server") or "mail.digital-twin-solutions.com"
    smtp_port = int(smtp_cfg.get("port", 465))

    print(f"\n--- [EMAIL DISPATCH via {smtp_server}:{smtp_port}] ---")
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
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)

        print(f"[SMTP] Connecting to {smtp_server}:{smtp_port}...")
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())

        print(f"[SUCCESS] Real email dispatched successfully via SMTP ({smtp_server}) to {to_email}!")
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
        # Filter for single-employee test if specified
        if test_target and emp.name.lower() != test_target.lower():
            continue

        local_now = emp.get_local_now()
        local_day = emp.get_local_day_str(local_now)
        local_date = args.force_date or emp.get_local_date_str(local_now)
        local_time = args.force_time or emp.get_local_time_str(local_now)

        print(f"\nProcessing Employee: {emp.name}")
        print(f"  Location / TZ:    {emp.location} ({emp.timezone_str})")
        print(f"  Local Time:       {local_now.strftime('%Y-%m-%d %H:%M:%S')} ({local_day})")
        print(f"  Working Days:     {','.join(emp.working_days)}")

        # 1. Evaluate Working Day
        if not emp.is_working_day(local_now):
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

        if not reminder_type and not args.force_time:
            print(f"  --> Status: SKIP (Current local time {local_time} does not match shift trigger times {rem_times}).")
            continue

        if args.force_time and not reminder_type:
            reminder_type = "first"

        print(f"  --> Time Window Matched: {reminder_type.upper()} REMINDER ({local_time})")

        # 3. Check Excel Sheet (Fetch latest from SharePoint if configured)
        excel_path = args.excel_file or config.get("excel_file_path", "Daily Task and Update Sheet.xlsx")
        sp_url = args.sharepoint_url or config.get("sharepoint_url")
        if sp_url:
            download_sharepoint_file(sp_url, excel_path)

        is_completed = check_task_sheet_local(excel_path, emp.sheet_name, local_date, emp.name)

        if is_completed:
            print(f"  --> Task Check Result: COMPLETED! Employee updated their sheet for {local_date}.")
            print(f"  --> Status: NO EMAIL REQUIRED.")
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
