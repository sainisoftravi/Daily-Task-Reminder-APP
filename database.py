#!/usr/bin/env python3
"""
Daily Task Log Reminder System - SQLite Database Layer
Author: Antigravity Assistant

Provides thread-safe SQLite persistence for Employees, Shifts, Teams, Managers,
Templates, System Settings, Daemon Logs, and Email Reminder History. Automatically
seeds from JSON files if database tables are empty on initialization.
"""

import os
import json
import sqlite3
import datetime
from typing import List, Dict, Any, Optional
from cryptography.fernet import Fernet

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_FILE = os.path.join(DATA_DIR, "app_database.db")

os.makedirs(DATA_DIR, exist_ok=True)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite schema and seeds initial data from JSON files if tables are empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Shifts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reminder1 TEXT,
            reminder2 TEXT,
            final_call TEXT,
            description TEXT
        )
    """)

    # 2. Teams Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            description TEXT
        )
    """)

    # 3. Managers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            team_id TEXT
        )
    """)

    # 4. Employees Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            location TEXT NOT NULL,
            timezone TEXT NOT NULL,
            working_days TEXT NOT NULL,
            shift_id TEXT,
            shift_name TEXT,
            reminders TEXT,
            team_id TEXT,
            team_name TEXT,
            sheet_name TEXT,
            manager_cc TEXT,
            role TEXT DEFAULT 'employee'
        )
    """)

    # 5. Email Templates Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            ignore_note TEXT
        )
    """)

    # 6. System Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # 7. Locations Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            name TEXT NOT NULL,
            timezone_name TEXT NOT NULL,
            iana_tz TEXT NOT NULL
        )
    """)

    # 8. Daemon Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)

    # 9. Email Reminder History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminder_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            email TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            status TEXT NOT NULL,
            date_str TEXT NOT NULL,
            details TEXT
        )
    """)

    # 10. Quotes Table (Thought of the Day)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id TEXT PRIMARY KEY,
            quote TEXT NOT NULL,
            category TEXT,
            created_at TEXT
        )
    """)

    # 11. Web Task Submission Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_logs (
            id TEXT PRIMARY KEY,
            employee_id TEXT,
            employee_name TEXT NOT NULL,
            email TEXT NOT NULL,
            team_id TEXT,
            team_name TEXT NOT NULL,
            date_str TEXT NOT NULL,
            task_details TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 12. Users Table (Multi-Role Authentication System)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            team_id TEXT,
            created_at TEXT
        )
    """)

    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN role TEXT DEFAULT 'employee'")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN location_id TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE managers ADD COLUMN team_name TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE templates ADD COLUMN ignore_note TEXT")
    except Exception:
        pass

    conn.commit()

    # --- SEED INITIAL DATA IF TABLES ARE EMPTY ---
    _seed_from_json(conn)
    conn.close()

def _seed_from_json(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Seed Shifts
    cursor.execute("SELECT COUNT(*) FROM shifts")
    if cursor.fetchone()[0] == 0:
        json_file = os.path.join(DATA_DIR, "shifts.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    shifts = json.load(f)
                    for s in shifts:
                        cursor.execute(
                            "INSERT INTO shifts (id, name, start_time, end_time, reminder1, reminder2, final_call, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (s.get("id"), s.get("name"), s.get("startTime", "10:00"), s.get("endTime", "19:00"), s.get("reminder1", "18:30"), s.get("reminder2", "18:45"), s.get("finalCall", "19:00"), s.get("description", ""))
                        )
            except Exception as e:
                print(f"[DB SEED WARN] Shifts seed error: {e}")

    # Seed Teams
    cursor.execute("SELECT COUNT(*) FROM teams")
    if cursor.fetchone()[0] == 0:
        json_file = os.path.join(DATA_DIR, "teams.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    teams = json.load(f)
                    for t in teams:
                        cursor.execute(
                            "INSERT INTO teams (id, name, sheet_name, description) VALUES (?, ?, ?, ?)",
                            (t.get("id"), t.get("name"), t.get("sheetName"), t.get("description", ""))
                        )
            except Exception as e:
                print(f"[DB SEED WARN] Teams seed error: {e}")

    # Seed Managers
    cursor.execute("SELECT COUNT(*) FROM managers")
    if cursor.fetchone()[0] == 0:
        json_file = os.path.join(DATA_DIR, "managers.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    managers = json.load(f)
                    for m in managers:
                        cursor.execute(
                            "INSERT INTO managers (id, name, email, team_id) VALUES (?, ?, ?, ?)",
                            (m.get("id"), m.get("name"), m.get("email"), m.get("teamId", ""))
                        )
            except Exception as e:
                print(f"[DB SEED WARN] Managers seed error: {e}")

    # Seed Employees
    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        json_file = os.path.join(DATA_DIR, "employees.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    employees = json.load(f)
                    for e in employees:
                        w_days = ",".join(e.get("workingDays", [])) if isinstance(e.get("workingDays"), list) else str(e.get("workingDays", "Mon,Tue,Wed,Thu,Fri,Sat"))
                        rems = ",".join(e.get("reminders", [])) if isinstance(e.get("reminders"), list) else "18:30,18:45,19:00"
                        cursor.execute(
                            """INSERT INTO employees 
                               (id, name, email, location, timezone, working_days, shift_id, shift_name, reminders, team_id, team_name, sheet_name, manager_cc)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (e.get("id"), e.get("name"), e.get("email"), e.get("location"), e.get("timezone"), w_days, e.get("shiftId", "shift_standard"), e.get("shiftName", "Standard Day Shift"), rems, e.get("teamId", "team_infra"), e.get("teamName", "Infra Team"), e.get("sheetName", "Technical Infra Team-Aug-2026"), e.get("managerCc", "Ravi@d2backoffice.onmicrosoft.com"))
                        )
            except Exception as e:
                print(f"[DB SEED WARN] Employees seed error: {e}")

    # Seed Templates
    cursor.execute("SELECT COUNT(*) FROM templates")
    if cursor.fetchone()[0] == 0:
        json_file = os.path.join(DATA_DIR, "templates.json")
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    tpls = json.load(f)
                    for k, v in tpls.items():
                        cursor.execute(
                            "INSERT INTO templates (key, name, subject, body, ignore_note) VALUES (?, ?, ?, ?, ?)",
                            (k, v.get("name", k), v.get("subject", ""), v.get("body", ""), v.get("ignore_note", ""))
                        )
            except Exception as e:
                print(f"[DB SEED WARN] Templates seed error: {e}")

    # Seed Settings & Ensure SMTP credentials
    default_cfg = {
        "excel_file_path": "Daily Task and Update Sheet.xlsx",
        "sharepoint_url": "https://d2backoffice-my.sharepoint.com/:x:/g/personal/ravi_d2backoffice_onmicrosoft.com/IQCybiwws57qSpGmQ9RdBx_RAaKEOarut68jb1ZFs7NK0PQ?e=1wwbfr",
        "auth_mode": "smtp",
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
    cursor.execute("INSERT INTO settings (key, value) VALUES ('config', ?) ON CONFLICT(key) DO NOTHING", (json.dumps(default_cfg),))

    # Seed Locations
    cursor.execute("SELECT COUNT(*) FROM locations")
    if cursor.fetchone()[0] == 0:
        default_locations = [
            ("loc_india", "India", "India (IST)", "India Standard Time", "Asia/Kolkata"),
            ("loc_uae", "UAE", "UAE (GST)", "Arabian Standard Time", "Asia/Dubai"),
            ("loc_saudi", "Saudi Arabia", "Saudi Arabia (AST)", "Arab Standard Time", "Asia/Riyadh"),
            ("loc_usa_east", "USA", "USA East (EST)", "Eastern Standard Time", "America/New_York"),
            ("loc_usa_west", "USA", "USA West (PST)", "Pacific Standard Time", "America/Los_Angeles"),
            ("loc_uk", "UK", "UK (GMT)", "GMT Standard Time", "Europe/London"),
            ("loc_singapore", "Singapore", "Singapore (SGT)", "Singapore Standard Time", "Asia/Singapore")
        ]
        for loc in default_locations:
            cursor.execute("INSERT INTO locations (id, country, name, timezone_name, iana_tz) VALUES (?, ?, ?, ?, ?)", loc)

    # Seed Motivational Quotes (Preserving older and user-added quotes)
    cursor.execute("SELECT COUNT(*) FROM quotes")
    if cursor.fetchone()[0] == 0:
        category_1 = "Focus, Progress & Consistency"
        category_2 = "Teamwork, Impact & Reliability"
        category_3 = "Recharge, Balance & Perspective"

        quotes_seed = [
            # Category 1 (Focus, Progress & Consistency)
            ("q_101", "Excellence is not an act, but a habit. What we build today lays the foundation for tomorrow.", category_1),
            ("q_102", "Focus on progress, not perfection. Every problem solved today strengthens the system for tomorrow.", category_1),
            ("q_103", "Big architectures are built one clean line of code at a time. Be proud of the ground you covered today.", category_1),
            ("q_104", "Quality is never an accident; it is always the result of intelligent effort and dedication.", category_1),
            ("q_105", "Continuous, deliberate improvement is what turns good engineering into great engineering.", category_1),
            ("q_106", "Small daily disciplines deliver massive, long-term impact.", category_1),
            ("q_107", "Consistent progress each day builds long-term success.", category_1),
            ("q_108", "Focus on being productive instead of busy.", category_1),

            # Category 2 (Teamwork, Impact & Reliability)
            ("q_201", "Individually we are one drop; together, we build a seamless system.", category_2),
            ("q_202", "A reliable handover today ensures an unstoppable team tomorrow.", category_2),
            ("q_203", "Great teams aren't built on heroic individual acts, but on consistent, shared responsibility.", category_2),
            ("q_204", "The strength of the team is each individual member. The strength of each member is the team.", category_2),
            ("q_205", "Clear communication and thorough documentation are the highest forms of team support.", category_2),
            ("q_206", "Pride in our work shows not just in what we build, but in how reliably we deliver it.", category_2),
            ("q_207", "Great things are done by a series of small things brought together.", category_2),
            ("q_208", "Order and organization simplify teamwork and accelerate progress.", category_2),

            # Category 3 (Recharge, Balance & Perspective)
            ("q_301", "Rest is not a reward for work completed; it is a prerequisite for tomorrow’s best performance.", category_3),
            ("q_302", "A sharp mind needs dedicated downtime. Disconnect with confidence and recharge fully.", category_3),
            ("q_303", "Sustainable excellence begins with balance. Log off knowing you made a difference today.", category_3),
            ("q_304", "True focus at work is made possible by true presence at home.", category_3),
            ("q_305", "Celebrate today’s wins, leave tomorrow’s challenges for tomorrow, and enjoy your evening.", category_3),
            ("q_306", "Step away from the screen, refresh your perspective, and return with renewed energy.", category_3),
            ("q_307", "Finish today strong so tomorrow starts with momentum.", category_3)
        ]
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for q in quotes_seed:
            cursor.execute("INSERT OR IGNORE INTO quotes (id, quote, category, created_at) VALUES (?, ?, ?, ?)", (q[0], q[1], q[2], now_str))

    # Seed Default User Accounts (Admin, Manager, Employees)
    _seed_users(conn)
    conn.commit()

def _seed_users(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Default Admin Account
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("u_admin", "System Administrator", "admin@company.com", "admin123", "admin", now_str))
        # Default Manager Account
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("u_mgr_1", "Ravi Saini", "Ravi@d2backoffice.onmicrosoft.com", "manager123", "manager", now_str))

        # Seed Employee Accounts from employee roster
        cursor.execute("SELECT name, email, team_id FROM employees")
        emps = cursor.fetchall()
        for idx, emp in enumerate(emps):
            e_dict = dict(emp)
            u_id = f"u_emp_{idx+1}"
            cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, team_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (u_id, e_dict.get("name"), e_dict.get("email"), "emp123", "employee", e_dict.get("team_id", ""), now_str))

# --- User Authentication & Management Helpers ---

def authenticate_user(email: str, password_raw: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    conn.close()

    if not row:
        return None
    
    user_dict = dict(row)
    # Check password match (plain text or encrypted fallback)
    if user_dict.get("password") == password_raw.strip():
        user_dict.pop("password", None)
        return user_dict
    return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),)).fetchone()
    conn.close()
    if row:
        u = dict(row)
        u.pop("password", None)
        return u
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        u = dict(row)
        u.pop("password", None)
        return u
    return None

# --- CRUD HELPER FUNCTIONS ---

# Quotes (Thought of the Day)
def get_all_quotes() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM quotes ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_quote_record(quote_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    q_id = quote_data.get("id") or f"q_{int(datetime.datetime.now().timestamp() * 1000)}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO quotes (id, quote, category, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            quote=excluded.quote,
            category=excluded.category
    """, (q_id, quote_data.get("quote", "").strip(), quote_data.get("category", "General").strip(), now_str))
    conn.commit()
    conn.close()
    return True

def delete_quote_record(quote_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()
    return True

# Employees
def get_all_employees() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees ORDER BY name ASC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["workingDays"] = [w.strip() for w in d["working_days"].split(",") if w.strip()] if d["working_days"] else []
        d["reminders"] = [rem.strip() for rem in d["reminders"].split(",") if rem.strip()] if d["reminders"] else ["18:30", "18:45", "19:00"]
        d["locationId"] = d.get("location_id")
        d["shiftId"] = d.get("shift_id")
        d["shiftName"] = d.get("shift_name")
        d["teamId"] = d.get("team_id")
        d["teamName"] = d.get("team_name")
        d["sheetName"] = d.get("sheet_name")
        d["managerCc"] = d.get("manager_cc")
        d["role"] = d.get("role") or "employee"
        result.append(d)
    return result

def save_employee_record(emp_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    emp_id = emp_data.get("id") or f"emp_{int(datetime.datetime.now().timestamp() * 1000)}"
    w_days = ",".join(emp_data.get("workingDays", [])) if isinstance(emp_data.get("workingDays"), list) else str(emp_data.get("workingDays", ""))
    rems = ",".join(emp_data.get("reminders", [])) if isinstance(emp_data.get("reminders"), list) else "18:30,18:45,19:00"
    role = (emp_data.get("role") or "employee").lower()

    cursor.execute("""
        INSERT INTO employees (id, name, email, location, location_id, timezone, working_days, shift_id, shift_name, reminders, team_id, team_name, sheet_name, manager_cc, role)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            location=excluded.location,
            location_id=excluded.location_id,
            timezone=excluded.timezone,
            working_days=excluded.working_days,
            shift_id=excluded.shift_id,
            shift_name=excluded.shift_name,
            reminders=excluded.reminders,
            team_id=excluded.team_id,
            team_name=excluded.team_name,
            sheet_name=excluded.sheet_name,
            manager_cc=excluded.manager_cc,
            role=excluded.role
    """, (
        emp_id, emp_data.get("name"), emp_data.get("email"), emp_data.get("location"), emp_data.get("locationId"), emp_data.get("timezone"),
        w_days, emp_data.get("shiftId"), emp_data.get("shiftName"), rems,
        emp_data.get("teamId"), emp_data.get("teamName"), emp_data.get("sheetName"), emp_data.get("managerCc"), role
    ))

    # Sync with users table for authentication
    email_clean = (emp_data.get("email") or "").strip().lower()
    name_val = (emp_data.get("name") or "").strip()
    team_id_val = emp_data.get("teamId", "")
    custom_pwd = (emp_data.get("password") or "").strip()

    if email_clean:
        existing_user = cursor.execute("SELECT id, password FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
        if existing_user:
            if custom_pwd:
                cursor.execute("UPDATE users SET name = ?, role = ?, team_id = ?, password = ? WHERE LOWER(email) = ?",
                               (name_val, role, team_id_val, custom_pwd, email_clean))
            else:
                cursor.execute("UPDATE users SET name = ?, role = ?, team_id = ? WHERE LOWER(email) = ?",
                               (name_val, role, team_id_val, email_clean))
        else:
            def_pass = custom_pwd if custom_pwd else ("admin123" if role == "admin" else ("mgr123" if role == "manager" else "emp123"))
            u_id = f"u_{emp_id}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO users (id, name, email, password, role, team_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (u_id, name_val, email_clean, def_pass, role, team_id_val, now_str))

    # If role is manager, sync with managers table
    if role == "manager" and email_clean:
        cursor.execute("""
            INSERT INTO managers (id, name, email, team_id, team_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                team_id=excluded.team_id,
                team_name=excluded.team_name
        """, (f"mgr_{emp_id}", name_val, email_clean, team_id_val, emp_data.get("teamName", "")))

    conn.commit()
    conn.close()
    return True

def update_user_password(email: str, old_password: str, new_password: str) -> Dict[str, Any]:
    conn = get_db_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "User account not found."}
    
    user_dict = dict(row)
    if user_dict.get("password") != old_password.strip():
        conn.close()
        return {"success": False, "error": "Current password is incorrect."}
    
    conn.execute("UPDATE users SET password = ? WHERE LOWER(email) = ?", (new_password.strip(), email_clean))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Password updated successfully!"}

def delete_employee_record(emp_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    return True

# Shifts
def get_all_shifts() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM shifts").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["startTime"] = d.get("start_time")
        d["endTime"] = d.get("end_time")
        d["reminder1"] = d.get("reminder1")
        d["reminder2"] = d.get("reminder2")
        d["finalCall"] = d.get("final_call")
        result.append(d)
    return result

def save_shift_record(shift_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    shift_id = shift_data.get("id") or f"shift_{int(datetime.datetime.now().timestamp() * 1000)}"

    # Calculate reminders if start/end times provided
    start_t = shift_data.get("startTime", "10:00")
    end_t = shift_data.get("endTime", "19:00")
    try:
        h, m = map(int, end_t.split(":"))
        end_dt = datetime.datetime(2026, 1, 1, h, m)
        rem1 = (end_dt - datetime.timedelta(minutes=30)).strftime("%H:%M")
        rem2 = (end_dt - datetime.timedelta(minutes=15)).strftime("%H:%M")
    except Exception:
        rem1, rem2 = "18:30", "18:45"

    cursor.execute("""
        INSERT INTO shifts (id, name, start_time, end_time, reminder1, reminder2, final_call, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            start_time=excluded.start_time,
            end_time=excluded.end_time,
            reminder1=excluded.reminder1,
            reminder2=excluded.reminder2,
            final_call=excluded.final_call,
            description=excluded.description
    """, (
        shift_id, shift_data.get("name"), start_t, end_t,
        shift_data.get("reminder1", rem1), shift_data.get("reminder2", rem2), shift_data.get("finalCall", end_t),
        shift_data.get("description", "")
    ))
    conn.commit()
    conn.close()
    return True

def delete_shift_record(shift_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    conn.commit()
    conn.close()
    return True

# Teams
def get_all_teams() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM teams").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["sheetName"] = d.get("sheet_name")
        result.append(d)
    return result

def save_team_record(team_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    team_id = team_data.get("id") or f"team_{int(datetime.datetime.now().timestamp() * 1000)}"
    conn.execute("""
        INSERT INTO teams (id, name, sheet_name, description)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            sheet_name=excluded.sheet_name,
            description=excluded.description
    """, (team_id, team_data.get("name"), team_data.get("sheetName"), team_data.get("description", "")))
    conn.commit()
    conn.close()
    return True

def delete_team_record(team_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    conn.commit()
    conn.close()
    return True

# Managers
def get_all_managers() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM managers").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["teamId"] = d.get("team_id")
        d["teamName"] = d.get("team_name")
        result.append(d)
    return result

def save_manager_record(mgr_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    mgr_id = mgr_data.get("id") or f"mgr_{int(datetime.datetime.now().timestamp() * 1000)}"
    conn.execute("""
        INSERT INTO managers (id, name, email, team_id, team_name)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            team_id=excluded.team_id,
            team_name=excluded.team_name
    """, (mgr_id, mgr_data.get("name"), mgr_data.get("email"), mgr_data.get("teamId", ""), mgr_data.get("teamName", "")))
    conn.commit()
    conn.close()
    return True

def delete_manager_record(mgr_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM managers WHERE id = ?", (mgr_id,))
    conn.commit()
    conn.close()
    return True

# Templates
def get_all_templates() -> Dict[str, Dict[str, str]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM templates").fetchall()
    conn.close()
    result = {}
    for r in rows:
        d = dict(r)
        result[d["key"]] = {
            "name": d.get("name", d["key"]),
            "subject": d.get("subject", ""),
            "body": d.get("body", ""),
            "ignore_note": d.get("ignore_note", "")
        }
    return result

def save_all_templates(templates_dict: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE templates ADD COLUMN ignore_note TEXT")
        conn.commit()
    except Exception:
        pass

    for k, v in templates_dict.items():
        cursor.execute("""
            INSERT INTO templates (key, name, subject, body, ignore_note)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                name=excluded.name,
                subject=excluded.subject,
                body=excluded.body,
                ignore_note=excluded.ignore_note
        """, (k, v.get("name", k), v.get("subject", ""), v.get("body", ""), v.get("ignore_note", "")))
    conn.commit()
    conn.close()
    return True

# System Settings
def get_system_settings() -> Dict[str, Any]:
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = 'config'").fetchone()
    conn.close()
    if row and row["value"]:
        try:
            return json.loads(row["value"])
        except Exception:
            pass
    return {}

def save_system_settings(config_dict: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO settings (key, value)
        VALUES ('config', ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (json.dumps(config_dict),))
    conn.commit()
    conn.close()
    return True

# --- Multi-SMTP Accounts Encryption & Management Functions ---

SECRET_KEY_FILE = os.path.join(DATA_DIR, "app_secret.key")

def get_or_create_fernet_key() -> bytes:
    if os.path.exists(SECRET_KEY_FILE):
        try:
            with open(SECRET_KEY_FILE, "rb") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception as e:
            print(f"[KEY READ ERROR] {e}")
    
    key = Fernet.generate_key()
    try:
        with open(SECRET_KEY_FILE, "wb") as f:
            f.write(key)
    except Exception as e:
        print(f"[KEY WRITE ERROR] {e}")
    return key

def encrypt_password(plaintext: str) -> str:
    if not plaintext or plaintext.startswith("gAAAAA") or plaintext == "••••••••••••":
        return plaintext
    try:
        f = Fernet(get_or_create_fernet_key())
        return f.encrypt(plaintext.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"[ENCRYPT ERROR] {e}")
        return plaintext

def decrypt_password(ciphertext: str) -> str:
    if not ciphertext or not ciphertext.startswith("gAAAAA"):
        return ciphertext
    try:
        f = Fernet(get_or_create_fernet_key())
        return f.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"[DECRYPT ERROR] {e}")
        return ciphertext

def get_all_smtp_accounts(mask_passwords: bool = False) -> List[Dict[str, Any]]:
    config = get_system_settings()
    smtp_accounts = config.get("smtp_accounts", [])
    
    if not smtp_accounts:
        user_creds = config.get("user_credentials", {})
        smtp_cfg = config.get("smtp", {})
        raw_pwd = user_creds.get("password") or smtp_cfg.get("password") or "1)T1h6Xzyo{kn"
        enc_pwd = encrypt_password(raw_pwd)
        default_acc = {
            "id": "smtp_default",
            "name": "Default Support System SMTP",
            "manager_email": "default",
            "server": smtp_cfg.get("server") or "mail.digital-twin-solutions.com",
            "port": int(smtp_cfg.get("port", 465)),
            "email": user_creds.get("email") or "support@digital-twin-solutions.com",
            "password": enc_pwd,
            "is_default": True
        }
        smtp_accounts = [default_acc]
        config["smtp_accounts"] = smtp_accounts
        save_system_settings(config)

    result = []
    for a in smtp_accounts:
        copy_a = dict(a)
        if mask_passwords:
            copy_a["password"] = "••••••••••••"
        result.append(copy_a)

    return result

def save_smtp_account(acc_data: Dict[str, Any]) -> bool:
    config = get_system_settings()
    smtp_accounts = config.get("smtp_accounts") or get_all_smtp_accounts(mask_passwords=False)
    
    acc_id = acc_data.get("id") or f"smtp_{int(datetime.datetime.now().timestamp() * 1000)}"
    acc_data["id"] = acc_id
    
    existing_acc = next((a for a in smtp_accounts if a.get("id") == acc_id), None)
    
    pwd_input = acc_data.get("password", "")
    if pwd_input == "••••••••••••" or not pwd_input:
        if existing_acc and existing_acc.get("password"):
            acc_data["password"] = existing_acc["password"]
    else:
        acc_data["password"] = encrypt_password(pwd_input)

    if acc_data.get("is_default"):
        for a in smtp_accounts:
            a["is_default"] = False

    existing_index = next((i for i, a in enumerate(smtp_accounts) if a.get("id") == acc_id), -1)
    if existing_index >= 0:
        smtp_accounts[existing_index] = acc_data
    else:
        smtp_accounts.append(acc_data)

    config["smtp_accounts"] = smtp_accounts
    
    if acc_data.get("is_default"):
        config["smtp"] = {
            "enabled": True,
            "server": acc_data.get("server"),
            "port": int(acc_data.get("port", 465))
        }
        config["user_credentials"] = {
            "email": acc_data.get("email"),
            "password": acc_data.get("password")
        }

    return save_system_settings(config)

def delete_smtp_account(acc_id: str) -> bool:
    config = get_system_settings()
    smtp_accounts = config.get("smtp_accounts") or get_all_smtp_accounts(mask_passwords=False)
    
    smtp_accounts = [a for a in smtp_accounts if a.get("id") != acc_id]
    config["smtp_accounts"] = smtp_accounts
    return save_system_settings(config)

def get_smtp_account_for_manager(manager_email: str) -> Dict[str, Any]:
    accounts = get_all_smtp_accounts(mask_passwords=False)
    matched = None

    if manager_email:
        clean_mgr = manager_email.strip().lower()
        for acc in accounts:
            acc_mgr = (acc.get("manager_email") or "").strip().lower()
            if acc_mgr and acc_mgr != "default" and (acc_mgr in clean_mgr or clean_mgr in acc_mgr):
                matched = dict(acc)
                break
                
    if not matched:
        for acc in accounts:
            if acc.get("is_default"):
                matched = dict(acc)
                break
            
    if not matched and accounts:
        matched = dict(accounts[0])

    if matched and matched.get("password"):
        matched["password"] = decrypt_password(matched["password"])

    return matched or {}

# Daemon Logs
def log_to_db(msg: str, level: str = "INFO"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", (timestamp, level, msg))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG DB ERROR] {e}")

def get_db_logs(limit: int = 200, start_date: str = None, end_date: str = None, query: str = None) -> List[str]:
    conn = get_db_connection()
    sql = "SELECT timestamp, level, message FROM logs"
    conditions = []
    params = []

    if start_date:
        conditions.append("timestamp >= ?")
        params.append(f"{start_date} 00:00:00")
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(f"{end_date} 23:59:59")
    if query:
        conditions.append("(message LIKE ? OR level LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return [f"[{r['timestamp']}] {r['message']}" for r in reversed(rows)]

# Email Reminder History
def record_reminder_history(emp_name: str, email: str, rem_type: str, status: str, date_str: str, details: str = ""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO reminder_history (timestamp, employee_name, email, reminder_type, status, date_str, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, emp_name, email, rem_type, status, date_str, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[HISTORY DB ERROR] {e}")

def get_reminder_history(limit: int = 200, start_date: str = None, end_date: str = None, query: str = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    sql = "SELECT * FROM reminder_history"
    conditions = []
    params = []

    if start_date:
        conditions.append("timestamp >= ?")
        params.append(f"{start_date} 00:00:00")
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(f"{end_date} 23:59:59")
    if query:
        conditions.append("(employee_name LIKE ? OR email LIKE ? OR reminder_type LIKE ? OR status LIKE ? OR date_str LIKE ? OR details LIKE ?)")
        params.extend([f"%{query}%"] * 6)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_db_logs(period: str = "all", start_date: str = None, end_date: str = None) -> int:
    """Deletes older daemon logs based on period ('day', 'week', 'month', 'year', 'all', 'range')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()

    if (period == "range" or start_date or end_date) and period not in ("day", "week", "month", "year", "all"):
        conditions = []
        params = []
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")
        if conditions:
            sql = "DELETE FROM logs WHERE " + " AND ".join(conditions)
            cursor.execute(sql, tuple(params))
        else:
            cursor.execute("DELETE FROM logs")
    elif period == "day":
        cutoff = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    elif period == "week":
        cutoff = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    elif period == "month":
        cutoff = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    elif period == "year":
        cutoff = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
    else:
        cursor.execute("DELETE FROM logs")

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def clear_reminder_history(period: str = "all", start_date: str = None, end_date: str = None) -> int:
    """Deletes older reminder history entries based on period ('day', 'week', 'month', 'year', 'all', 'range')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()

    if (period == "range" or start_date or end_date) and period not in ("day", "week", "month", "year", "all"):
        conditions = []
        params = []
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(f"{start_date} 00:00:00")
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(f"{end_date} 23:59:59")
        if conditions:
            sql = "DELETE FROM reminder_history WHERE " + " AND ".join(conditions)
            cursor.execute(sql, tuple(params))
        else:
            cursor.execute("DELETE FROM reminder_history")
    elif period == "day":
        cutoff = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM reminder_history WHERE timestamp < ?", (cutoff,))
    elif period == "week":
        cutoff = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM reminder_history WHERE timestamp < ?", (cutoff,))
    elif period == "month":
        cutoff = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM reminder_history WHERE timestamp < ?", (cutoff,))
    elif period == "year":
        cutoff = (now - datetime.timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM reminder_history WHERE timestamp < ?", (cutoff,))
    else:
        cursor.execute("DELETE FROM reminder_history")

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

# Locations
def get_all_locations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM locations ORDER BY country ASC, name ASC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["timezoneName"] = d.get("timezone_name")
        d["ianaTz"] = d.get("iana_tz")
        result.append(d)
    return result

def save_location_record(loc_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    loc_id = loc_data.get("id") or f"loc_{int(datetime.datetime.now().timestamp() * 1000)}"
    conn.execute("""
        INSERT INTO locations (id, country, name, timezone_name, iana_tz)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            country=excluded.country,
            name=excluded.name,
            timezone_name=excluded.timezone_name,
            iana_tz=excluded.iana_tz
    """, (
        loc_id,
        loc_data.get("country", "India"),
        loc_data.get("name", loc_data.get("country")),
        loc_data.get("timezoneName", "India Standard Time"),
        loc_data.get("ianaTz", "Asia/Kolkata")
    ))
    conn.commit()
    conn.close()
    return True

def delete_location_record(loc_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    conn.commit()
    conn.close()
    return True

# --- Daily Task Submission Logs Helpers ---

def save_task_log(data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    emp_name = data.get("employeeName") or data.get("employee_name", "Unknown")
    email = data.get("email", "")
    team_name = data.get("teamName") or data.get("team_name", "Infra Team")
    team_id = data.get("teamId") or data.get("team_id", "")
    date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
    task_details = data.get("taskDetails") or data.get("task_details", "")
    emp_id = data.get("employeeId") or data.get("employee_id", "")
    log_id = data.get("id") or f"log_{emp_name.lower().replace(' ', '_')}_{date_str}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO task_logs (id, employee_id, employee_name, email, team_id, team_name, date_str, task_details, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            employee_name=excluded.employee_name,
            email=excluded.email,
            team_id=excluded.team_id,
            team_name=excluded.team_name,
            date_str=excluded.date_str,
            task_details=excluded.task_details,
            updated_at=excluded.updated_at
    """, (log_id, emp_id, emp_name, email, team_id, team_name, date_str, task_details, now_str))
    conn.commit()
    conn.close()
    return True

def get_task_logs(team_id: Optional[str] = None, team_name: Optional[str] = None, date_str: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    query = "SELECT * FROM task_logs WHERE 1=1"
    params = []

    if team_id and team_id != "ALL":
        query += " AND (team_id = ? OR LOWER(team_name) LIKE ?)"
        params.append(team_id)
        params.append(f"%{team_id.lower()}%")
    elif team_name and team_name != "ALL":
        query += " AND LOWER(team_name) LIKE ?"
        params.append(f"%{team_name.lower()}%")

    if date_str:
        query += " AND date_str = ?"
        params.append(date_str)
    if start_date:
        query += " AND date_str >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date_str <= ?"
        params.append(end_date)

    query += " ORDER BY date_str DESC, employee_name ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def is_employee_task_filled(employee_name_or_email: str, date_str: str) -> bool:
    """Checks if an employee has submitted a task log for the specified date."""
    conn = get_db_connection()
    val = employee_name_or_email.strip().lower()
    
    # Try exact YYYY-MM-DD match or alternate date representations
    row = conn.execute("""
        SELECT task_details FROM task_logs 
        WHERE (LOWER(employee_name) LIKE ? OR LOWER(email) LIKE ?) 
        AND (date_str = ? OR date_str LIKE ?)
    """, (f"%{val}%", f"%{val}%", date_str, f"%{date_str}%")).fetchone()
    
    conn.close()
    if row and row["task_details"] and len(row["task_details"].strip()) > 5:
        return True
    return False

def delete_task_log(log_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM task_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True

# Initialize database schema immediately on import
init_db()
