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
import time
import secrets
import string
import threading
from typing import List, Dict, Any, Optional
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash

def generate_random_password(length: int = 12) -> str:
    """Generates a secure 12-character random password containing uppercase, lowercase, and numeric characters."""
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    
    pwd = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits)
    ]
    all_chars = uppercase + lowercase + digits
    pwd += [secrets.choice(all_chars) for _ in range(length - 3)]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)

def hash_password(password_raw: str) -> str:
    """Hashes a plaintext password using werkzeug pbkdf2/scrypt algorithm."""
    if not password_raw:
        return ""
    if password_raw.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return password_raw
    return generate_password_hash(password_raw)

def verify_password(stored_password: str, password_raw: str) -> bool:
    """Verifies a password against stored password (handles hashed or legacy plaintext)."""
    if not stored_password or not password_raw:
        return False
    if stored_password.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return check_password_hash(stored_password, password_raw.strip())
    return stored_password == password_raw.strip()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_FILE = os.path.join(DATA_DIR, "app_database.db")

os.makedirs(DATA_DIR, exist_ok=True)

# --- Dual Database Support (SQLite Local Default + Supabase PostgreSQL Cloud) ---
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


DB_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
if DB_URL and DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DB_URL and PSYCOPG2_AVAILABLE)

class DictRow(dict):
    """Dictionary wrapper for DB rows supporting integer indexing, key lookup, and dict casting."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

def _adapt_sql_for_pg(sql: str) -> str:
    """Adapts SQLite SQL dialect to PostgreSQL / Supabase dialect on the fly."""
    # Convert INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    
    # Convert INSERT OR IGNORE INTO -> INSERT INTO ... ON CONFLICT DO NOTHING
    if "INSERT OR IGNORE INTO" in sql:
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
        if "ON CONFLICT" not in sql.upper():
            sql = sql + " ON CONFLICT DO NOTHING"

    # Add IF NOT EXISTS to ADD COLUMN for PostgreSQL
    if "ADD COLUMN" in sql.upper() and "IF NOT EXISTS" not in sql.upper():
        sql = sql.replace("ADD COLUMN", "ADD COLUMN IF NOT EXISTS").replace("add column", "ADD COLUMN IF NOT EXISTS")
            
    # Convert positional parameter ? to %s
    sql = sql.replace("?", "%s")
    
    # Convert case-sensitive LIKE to case-insensitive ILIKE for PostgreSQL
    sql = sql.replace(" LIKE ", " ILIKE ")
    
    return sql

class PgCursorWrapper:
    def __init__(self, pg_cursor, pg_conn):
        self._cursor = pg_cursor
        self._conn = pg_conn
        
    @property
    def rowcount(self):
        return self._cursor.rowcount

    def execute(self, sql: str, params=()):
        sql_pg = _adapt_sql_for_pg(sql)
        try:
            self._cursor.execute(sql_pg, params)
        except Exception as e:
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise e
        return self

    def executemany(self, sql: str, seq_of_parameters=()):
        sql_pg = _adapt_sql_for_pg(sql)
        try:
            self._cursor.executemany(sql_pg, seq_of_parameters)
        except Exception as e:
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise e
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return DictRow(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [DictRow(r) for r in rows]

class PgConnectionWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PgCursorWrapper(cursor, self._conn)

    def execute(self, sql: str, params=()):
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

_PG_POOL = None

def get_pg_pool():
    global _PG_POOL
    if not USE_POSTGRES:
        return None
    if _PG_POOL is None or getattr(_PG_POOL, "closed", True):
        try:
            _PG_POOL = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DB_URL,
                connect_timeout=10
            )
        except Exception:
            _PG_POOL = None
            return None
    return _PG_POOL

class PgPooledConnectionWrapper(PgConnectionWrapper):
    """Wrapper around a pooled PostgreSQL connection that returns it to the pool on close()."""
    def __init__(self, pg_conn, pool_ref):
        super().__init__(pg_conn)
        self._pool_ref = pool_ref
        self._is_returned = False

    def close(self):
        if not self._is_returned:
            self._is_returned = True
            if self._pool_ref and not getattr(self._pool_ref, "closed", True):
                try:
                    if hasattr(self._conn, "closed") and self._conn.closed == 0:
                        self._conn.rollback()
                    self._pool_ref.putconn(self._conn)
                    return
                except Exception:
                    pass
            try:
                self._conn.close()
            except Exception:
                pass

def get_db_connection():
    if USE_POSTGRES:
        # 1. Attempt to acquire a warm, persistent connection from the connection pool
        p = get_pg_pool()
        if p:
            try:
                raw_conn = p.getconn()
                if raw_conn and hasattr(raw_conn, "closed") and raw_conn.closed == 0:
                    return PgPooledConnectionWrapper(raw_conn, p)
                else:
                    if raw_conn:
                        p.putconn(raw_conn, close=True)
            except Exception:
                pass

        # 2. Fallback to direct connection if connection pool is unavailable

        try:
            pg_conn = psycopg2.connect(DB_URL, connect_timeout=15)
            return PgConnectionWrapper(pg_conn)
        except Exception as e:
            if "supabase.co" in DB_URL or "5432" in DB_URL:
                print("\n" + "="*80)
                print("[DATABASE CONNECTION ERROR] Unable to connect to PostgreSQL host.")
                print("If you are using Supabase on Render, direct host 'db.xxx.supabase.co:5432' relies on IPv6 (Network Unreachable on Render).")
                print("Please switch DATABASE_URL on Render to your Supabase POOLER connection string (port 6543 or 5432):")
                print("Example: postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres")
                print("="*80 + "\n")
            raise e
    else:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """Initializes Database schema (SQLite or PostgreSQL) and seeds initial data if empty."""
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
            team_id TEXT,
            team_name TEXT
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
            role TEXT DEFAULT 'employee',
            location_id TEXT,
            must_change_password INTEGER DEFAULT 0,
            pwd_expires_at TEXT
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
            updated_at TEXT NOT NULL,
            is_leave INTEGER DEFAULT 0,
            work_status TEXT DEFAULT 'Present'
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
            created_at TEXT,
            must_change_password INTEGER DEFAULT 0,
            pwd_expires_at TEXT
        )
    """)

    conn.commit()

    # Legacy schema column migrations (safe with ADD COLUMN IF NOT EXISTS)
    for alter_cmd in [
        "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN pwd_expires_at TEXT",
        "ALTER TABLE employees ADD COLUMN must_change_password INTEGER DEFAULT 0",
        "ALTER TABLE employees ADD COLUMN pwd_expires_at TEXT",
        "ALTER TABLE employees ADD COLUMN role TEXT DEFAULT 'employee'",
        "ALTER TABLE employees ADD COLUMN location_id TEXT",
        "ALTER TABLE managers ADD COLUMN team_name TEXT",
        "ALTER TABLE templates ADD COLUMN ignore_note TEXT",
        "ALTER TABLE task_logs ADD COLUMN is_leave INTEGER DEFAULT 0",
        "ALTER TABLE task_logs ADD COLUMN work_status TEXT DEFAULT 'Present'"
    ]:
        try:
            cursor.execute(alter_cmd)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # Create indexes for users, employees, and task_logs for ultra-fast query responses
    for idx_cmd in [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_leave ON task_logs(is_leave, work_status)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_email ON task_logs(email)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_date ON task_logs(date_str)",
        "CREATE INDEX IF NOT EXISTS idx_task_logs_emp ON task_logs(employee_name)"
    ]:
        try:
            cursor.execute(idx_cmd)
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

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
    json_file = os.path.join(DATA_DIR, "templates.json")
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                tpls = json.load(f)
                for k, v in tpls.items():
                    cursor.execute(
                        "INSERT INTO templates (key, name, subject, body, ignore_note) VALUES (?, ?, ?, ?, ?) ON CONFLICT(key) DO NOTHING",
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
    _migrate_plaintext_passwords(conn)
    _clean_legacy_task_logs(conn)
    conn.commit()

def _clean_legacy_task_logs(conn):
    """Automatically cleans employee_name in task_logs that may contain trailing team names in parentheses."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_name FROM task_logs WHERE employee_name LIKE '% (%'")
        rows = cursor.fetchall()
        for r in rows:
            u_dict = dict(r)
            l_id = u_dict.get("id")
            raw_n = u_dict.get("employee_name") or ""
            if "(" in raw_n:
                clean_n = raw_n.split(" (")[0].strip()
                cursor.execute("UPDATE task_logs SET employee_name = ? WHERE id = ?", (clean_n, l_id))
        conn.commit()
    except Exception as e:
        print(f"[DB CLEANUP WARNING] Failed cleaning legacy task logs: {e}")

def _migrate_plaintext_passwords(conn):
    """Automatically upgrades any plain text passwords in the users table to salted Werkzeug password hashes."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users")
        rows = cursor.fetchall()
        for r in rows:
            u_dict = dict(r)
            u_id = u_dict.get("id")
            pwd = u_dict.get("password") or ""
            if pwd and not pwd.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                hashed = hash_password(pwd)
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, u_id))
        conn.commit()
    except Exception as e:
        print(f"[DB MIGRATION WARNING] Failed migrating plain text passwords: {e}")

def _seed_users(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Default Admin Account
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("u_admin", "System Administrator", "admin@company.com", hash_password("admin123"), "admin", now_str))
        # Default Manager Account
        cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                       ("u_mgr_1", "Ravi Saini", "Ravi@d2backoffice.onmicrosoft.com", hash_password("manager123"), "manager", now_str))

        # Seed Employee Accounts from employee roster
        cursor.execute("SELECT name, email, team_id FROM employees")
        emps = cursor.fetchall()
        for idx, emp in enumerate(emps):
            e_dict = dict(emp)
            u_id = f"u_emp_{idx+1}"
            cursor.execute("INSERT OR IGNORE INTO users (id, name, email, password, role, team_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (u_id, e_dict.get("name"), e_dict.get("email"), hash_password("emp123"), "employee", e_dict.get("team_id", ""), now_str))

# --- User Authentication & Management Helpers ---

def authenticate_user(email: str, password_raw: str) -> Dict[str, Any]:
    conn = get_db_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": "Invalid email or password. Please check your credentials."}
    
    user_dict = dict(row)
    stored_pwd = user_dict.get("password") or ""
    if verify_password(stored_pwd, password_raw):
        # Auto-upgrade legacy plain text password to Werkzeug hash upon successful login
        if not stored_pwd.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            try:
                up_conn = get_db_connection()
                up_conn.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password_raw.strip()), user_dict["id"]))
                up_conn.commit()
                up_conn.close()
            except Exception:
                pass

        must_change = bool(user_dict.get("must_change_password"))
        expires_at = user_dict.get("pwd_expires_at")
        
        if must_change and expires_at:
            try:
                exp_dt = datetime.datetime.fromisoformat(expires_at)
                if datetime.datetime.now() > exp_dt:
                    return {
                        "success": False,
                        "expired": True,
                        "error": "Your temporary password has expired (valid for 4 hours). Please use 'Forgot password?' below to request a new password."
                    }
            except Exception:
                pass

        user_dict.pop("password", None)
        return {
            "success": True,
            "user": user_dict,
            "mustChangePassword": must_change
        }
    
    return {"success": False, "error": "Invalid email or password. Please check your credentials."}

def reset_user_password_with_expiry(email: str, hours: int = 4) -> Dict[str, Any]:
    """Resets user password to a 12-char random string valid for specified hours (default 4h) requiring change on login."""
    conn = get_db_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "No account found registered with this email address."}
    
    user = dict(row)
    new_pass = generate_random_password(12)
    hashed_pass = hash_password(new_pass)
    expires_dt = datetime.datetime.now() + datetime.timedelta(hours=hours)
    expires_str = expires_dt.isoformat()
    
    conn.execute("""
        UPDATE users
        SET password = ?, must_change_password = 1, pwd_expires_at = ?
        WHERE LOWER(email) = ?
    """, (hashed_pass, expires_str, email_clean))
    
    try:
        conn.execute("""
            UPDATE employees
            SET must_change_password = 1, pwd_expires_at = ?
            WHERE LOWER(email) = ?
        """, (expires_str, email_clean))
    except Exception:
        pass
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "user": user,
        "new_password": new_pass,
        "expires_at": expires_str
    }

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

# Employees Cache
_EMPLOYEES_CACHE = None
_EMPLOYEES_CACHE_TIME = 0.0

def invalidate_employees_cache():
    global _EMPLOYEES_CACHE, _EMPLOYEES_CACHE_TIME
    _EMPLOYEES_CACHE = None
    _EMPLOYEES_CACHE_TIME = 0.0

def get_all_employees(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _EMPLOYEES_CACHE, _EMPLOYEES_CACHE_TIME
    now = time.time()
    if not force_refresh and _EMPLOYEES_CACHE is not None and (now - _EMPLOYEES_CACHE_TIME) < 15.0:
        return _EMPLOYEES_CACHE

    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees ORDER BY name ASC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("working_days"):
            raw_w = str(d["working_days"]).replace("[", "").replace("]", "").replace('"', "").replace("'", "")
            d["workingDays"] = [w.strip() for w in raw_w.split(",") if w.strip()]
        else:
            d["workingDays"] = []
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

    _EMPLOYEES_CACHE = result
    _EMPLOYEES_CACHE_TIME = now
    return result

def save_employee_record(emp_data: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    emp_id = emp_data.get("id") or f"emp_{int(datetime.datetime.now().timestamp() * 1000)}"
    raw_w = emp_data.get("workingDays") or emp_data.get("working_days") or []
    if isinstance(raw_w, list):
        clean_items = [str(x).replace("[", "").replace("]", "").replace('"', "").replace("'", "").strip() for x in raw_w]
        w_days = ",".join([x for x in clean_items if x])
    else:
        w_days = str(raw_w).replace("[", "").replace("]", "").replace('"', "").replace("'", "").strip()
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
        exp_4h = (datetime.datetime.now() + datetime.timedelta(hours=4)).isoformat()

        if existing_user:
            if custom_pwd:
                cursor.execute("""
                    UPDATE users 
                    SET name = ?, role = ?, team_id = ?, password = ?, must_change_password = 1, pwd_expires_at = ? 
                    WHERE LOWER(email) = ?
                """, (name_val, role, team_id_val, hash_password(custom_pwd), exp_4h, email_clean))
                emp_data["generated_password"] = custom_pwd
            else:
                cursor.execute("UPDATE users SET name = ?, role = ?, team_id = ? WHERE LOWER(email) = ?",
                               (name_val, role, team_id_val, email_clean))
        else:
            final_pwd = custom_pwd if custom_pwd else generate_random_password(12)
            u_id = f"u_{emp_id}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (id, name, email, password, role, team_id, created_at, must_change_password, pwd_expires_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (u_id, name_val, email_clean, hash_password(final_pwd), role, team_id_val, now_str, exp_4h))
            emp_data["generated_password"] = final_pwd

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
    invalidate_employees_cache()
    return True

def update_user_password(email: str, old_password: str, new_password: str, is_forced: bool = False) -> Dict[str, Any]:
    conn = get_db_connection()
    email_clean = email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)).fetchone()
    if not row:
        conn.close()
        return {"success": False, "error": "User account not found."}
    
    user_dict = dict(row)
    stored_pwd = user_dict.get("password") or ""
    if not is_forced and old_password and not verify_password(stored_pwd, old_password):
        conn.close()
        return {"success": False, "error": "Current password is incorrect."}
    
    hashed_new = hash_password(new_password.strip())
    conn.execute("""
        UPDATE users 
        SET password = ?, must_change_password = 0, pwd_expires_at = NULL 
        WHERE LOWER(email) = ?
    """, (hashed_new, email_clean))

    try:
        conn.execute("""
            UPDATE employees 
            SET must_change_password = 0, pwd_expires_at = NULL 
            WHERE LOWER(email) = ?
        """, (email_clean,))
    except Exception:
        pass

    conn.commit()
    conn.close()
    return {"success": True, "message": "Password updated successfully!"}


def delete_employee_record(emp_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    invalidate_employees_cache()
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
    result = []
    seen_emails = set()

    try:
        emp_rows = conn.execute("SELECT * FROM employees WHERE LOWER(role) = 'manager'").fetchall()
        for r in emp_rows:
            d = dict(r)
            email = (d.get("email") or "").strip().lower()
            if email and email not in seen_emails:
                seen_emails.add(email)
                result.append({
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "email": d.get("email"),
                    "teamId": d.get("team_id") or d.get("teamId", ""),
                    "teamName": d.get("team_name") or d.get("teamName", "")
                })
    except Exception:
        pass

    try:
        user_rows = conn.execute("SELECT * FROM users WHERE LOWER(role) = 'manager'").fetchall()
        for r in user_rows:
            d = dict(r)
            email = (d.get("email") or "").strip().lower()
            if email and email not in seen_emails:
                seen_emails.add(email)
                result.append({
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "email": d.get("email"),
                    "teamId": "",
                    "teamName": ""
                })
    except Exception:
        pass

    if not result:
        try:
            rows = conn.execute("SELECT * FROM managers").fetchall()
            for r in rows:
                d = dict(r)
                d["teamId"] = d.get("team_id")
                d["teamName"] = d.get("team_name")
                email = (d.get("email") or "").strip().lower()
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    result.append(d)
        except Exception:
            pass

    conn.close()
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

import base64
import hashlib

SECRET_KEY_FILE = os.path.join(DATA_DIR, "app_secret.key")

def get_or_create_fernet_key() -> bytes:
    """Returns a deterministic, persistent Fernet key derived from SECRET_KEY environment variable."""
    secret = os.environ.get("SECRET_KEY", "ticktask-master-fernet-secret-key-2026")
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)


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
    def _write_async():
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)", (timestamp, level, msg))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[LOG DB ERROR] {e}")
    threading.Thread(target=_write_async, daemon=True).start()

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
    raw_name = data.get("employeeName") or data.get("employee_name", "Unknown")
    emp_name = raw_name.split(" (")[0].strip() if raw_name else "Unknown"
    email = data.get("email", "").strip()
    if not email and emp_name and emp_name != "Unknown":
        emps = get_all_employees()
        e_match = next((e for e in emps if (e.get("name") or "").split(" (")[0].strip().lower() == emp_name.lower()), None)
        if e_match:
            email = (e_match.get("email") or "").strip()

    team_name = data.get("teamName") or data.get("team_name", "Infra Team")
    team_id = data.get("teamId") or data.get("team_id", "")
    date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
    task_details = (data.get("taskDetails") or data.get("task_details") or "").strip()
    
    is_leave_val = data.get("isLeave") or data.get("is_leave")
    work_status_val = str(data.get("workStatus") or data.get("work_status") or "").strip()
    
    if work_status_val.lower() in ("week off", "weekoff") or "week off" in task_details.lower() or "weekoff" in task_details.lower():
        is_leave = 0
        work_status = "Week Off"
        if not task_details:
            task_details = "WEEK OFF"
    elif is_leave_val or work_status_val.lower() in ("leave", "on leave") or "on leave" in task_details.lower():
        is_leave = 1
        work_status = "Leave"
        if not task_details:
            task_details = "ON LEAVE"
    else:
        is_leave = 0
        work_status = "Present"

    emp_id = data.get("employeeId") or data.get("employee_id", "")
    log_id = data.get("id") or f"log_{emp_name.lower().replace(' ', '_')}_{date_str}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO task_logs (id, employee_id, employee_name, email, team_id, team_name, date_str, task_details, updated_at, is_leave, work_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            employee_name=excluded.employee_name,
            email=excluded.email,
            team_id=excluded.team_id,
            team_name=excluded.team_name,
            date_str=excluded.date_str,
            task_details=excluded.task_details,
            updated_at=excluded.updated_at,
            is_leave=excluded.is_leave,
            work_status=excluded.work_status
    """, (log_id, emp_id, emp_name, email, team_id, team_name, date_str, task_details, now_str, is_leave, work_status))
    conn.commit()
    conn.close()
    return True


def save_task_logs_batch(payload_list: List[Dict[str, Any]]) -> bool:
    """Inserts or updates multiple task logs in a single batch database transaction."""
    if not payload_list:
        return True
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    emps = get_all_employees()
    rows_to_insert = []
    for data in payload_list:
        raw_name = data.get("employeeName") or data.get("employee_name", "Unknown")
        emp_name = raw_name.split(" (")[0].strip() if raw_name else "Unknown"
        email = data.get("email", "").strip()
        if not email and emp_name and emp_name != "Unknown":
            e_match = next((e for e in emps if (e.get("name") or "").split(" (")[0].strip().lower() == emp_name.lower()), None)
            if e_match:
                email = (e_match.get("email") or "").strip()

        team_name = data.get("teamName") or data.get("team_name", "Infra Team")
        team_id = data.get("teamId") or data.get("team_id", "")
        date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
        task_details = (data.get("taskDetails") or data.get("task_details") or "").strip()
        
        is_leave_val = data.get("isLeave") or data.get("is_leave")
        work_status_val = str(data.get("workStatus") or data.get("work_status") or "").strip()
        
        if work_status_val.lower() in ("week off", "weekoff") or "week off" in task_details.lower() or "weekoff" in task_details.lower():
            is_leave = 0
            work_status = "Week Off"
            if not task_details:
                task_details = "WEEK OFF"
        elif is_leave_val or work_status_val.lower() in ("leave", "on leave") or "on leave" in task_details.lower():
            is_leave = 1
            work_status = "Leave"
            if not task_details:
                task_details = "ON LEAVE"
        else:
            is_leave = 0
            work_status = "Present"

        emp_id = data.get("employeeId") or data.get("employee_id", "")
        log_id = data.get("id") or f"log_{emp_name.lower().replace(' ', '_')}_{date_str}"

        rows_to_insert.append((log_id, emp_id, emp_name, email, team_id, team_name, date_str, task_details, now_str, is_leave, work_status))

    cursor.executemany("""
        INSERT INTO task_logs (id, employee_id, employee_name, email, team_id, team_name, date_str, task_details, updated_at, is_leave, work_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            employee_name=excluded.employee_name,
            email=excluded.email,
            team_id=excluded.team_id,
            team_name=excluded.team_name,
            date_str=excluded.date_str,
            task_details=excluded.task_details,
            updated_at=excluded.updated_at,
            is_leave=excluded.is_leave,
            work_status=excluded.work_status
    """, rows_to_insert)
    conn.commit()
    conn.close()
    invalidate_leave_cache()
    return True



def get_employee_working_days(employee_name_or_email: str) -> List[str]:
    """Returns working days list for employee (e.g. ['Mon', 'Tue', ...]). Defaults to Mon-Sat."""
    if not employee_name_or_email:
        return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    clean_val = employee_name_or_email.split(" (")[0].strip().lower()
    conn = get_db_connection()
    val_like = f"%{clean_val}%"
    row = conn.execute(
        "SELECT working_days FROM employees WHERE LOWER(email) = ? OR LOWER(name) = ? OR LOWER(name) LIKE ? OR id = ? LIMIT 1",
        (clean_val, clean_val, val_like, employee_name_or_email)
    ).fetchone()
    conn.close()
    if row and row["working_days"]:
        raw_str = str(row["working_days"]).replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        days = [w.strip() for w in raw_str.split(",") if w.strip()]
        if days:
            return days
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def is_date_week_off(dt_input: Any, working_days: List[str]) -> bool:
    """Checks if a datetime date object or ISO string is a week off based on working_days list."""
    if not dt_input:
        return False
    if isinstance(dt_input, str):
        try:
            dt = datetime.datetime.strptime(dt_input[:10], "%Y-%m-%d")
        except ValueError:
            return False
    elif isinstance(dt_input, (datetime.date, datetime.datetime)):
        dt = dt_input
    else:
        return False

    day_short = dt.strftime("%a")
    day_full = dt.strftime("%A")
    wd_lower = [w.lower() for w in working_days]
    for wd in wd_lower:
        if wd == day_short.lower() or wd == day_full.lower() or wd[:3] == day_short.lower():
            return False
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

_LEAVE_CACHE = {}
_LEAVE_CACHE_TTL = 5.0

def invalidate_leave_cache():
    global _LEAVE_CACHE
    _LEAVE_CACHE = {}

def get_leave_logs(email: Optional[str] = None, employee_name: Optional[str] = None, team_name: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    """Ultra-fast indexed database lookup for Leave & Week Off records with comprehensive alias matching and TTL caching."""
    cache_key = f"{email}:{employee_name}:{team_name}:{limit}"
    now = time.time()
    if cache_key in _LEAVE_CACHE:
        c_time, c_data = _LEAVE_CACHE[cache_key]
        if now - c_time < _LEAVE_CACHE_TTL:
            return c_data

    conn = get_db_connection()
    query = """
        SELECT * FROM task_logs 
        WHERE (CAST(is_leave AS VARCHAR) IN ('1', 'true', 'True', 'TRUE') OR LOWER(work_status) IN ('leave', 'week off', 'on leave') OR LOWER(task_details) LIKE '%on leave%' OR LOWER(task_details) LIKE '%week off%' OR LOWER(task_details) LIKE '%weekoff%')

    """
    params = []
    
    target_emails = set()
    target_names = set()

    if email and email.strip():
        e_clean = email.strip().lower()
        target_emails.add(e_clean)
        if "@" in e_clean:
            prefix = e_clean.split("@")[0].strip()
            if prefix:
                target_names.add(prefix)

    if employee_name and employee_name.strip():
        n_clean = employee_name.split(" (")[0].strip().lower()
        if n_clean:
            target_names.add(n_clean)

    if target_emails or target_names:
        # Cross-reference with employee roster to include linked emails & names
        try:
            emps = get_all_employees()
            for emp in emps:
                emp_e = (emp.get("email") or "").strip().lower()
                emp_n = (emp.get("name") or "").split(" (")[0].strip().lower()
                if (emp_e and emp_e in target_emails) or (emp_n and emp_n in target_names):
                    if emp_e:
                        target_emails.add(emp_e)
                    if emp_n:
                        target_names.add(emp_n)
        except Exception:
            pass

    if target_emails or target_names:
        conds = []
        for e in target_emails:
            conds.append("LOWER(email) = ?")
            params.append(e)
            conds.append("LOWER(email) LIKE ?")
            params.append(f"%{e}%")
        for n in target_names:
            conds.append("LOWER(employee_name) LIKE ?")
            params.append(f"%{n}%")
        if conds:
            query += " AND (" + " OR ".join(conds) + ")"

    if team_name and team_name != "ALL":
        query += " AND (LOWER(team_name) LIKE ? OR LOWER(team_id) LIKE ?)"
        params.append(f"%{team_name.lower()}%")
        params.append(f"%{team_name.lower()}%")

    query += " ORDER BY date_str DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    res = [dict(r) for r in rows]
    _LEAVE_CACHE[cache_key] = (now, res)
    return res



def is_employee_week_off(employee_name_or_email: str, date_input: Any) -> bool:
    """
    Checks if a given date is a Week Off for an employee based on their configured working_days.
    emp_identifier can be employee's email, name, or employee ID.
    date_input can be a string 'YYYY-MM-DD', datetime.date, or datetime.datetime object.
    Returns True if the date is a Week Off (non-working day), False if it is a working day.
    """
    if not date_input:
        return False
    if isinstance(date_input, str):
        try:
            dt = datetime.datetime.strptime(date_input[:10], "%Y-%m-%d")
        except ValueError:
            return False
    elif isinstance(date_input, (datetime.date, datetime.datetime)):
        dt = date_input
    else:
        return False

    day_short = dt.strftime("%a") # e.g. 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'
    day_full = dt.strftime("%A")  # e.g. 'Monday', 'Tuesday'

    raw_days = None
    if employee_name_or_email:
        conn = get_db_connection()
        val = employee_name_or_email.strip().lower()
        val_like = f"%{val}%"
        row = conn.execute(
            "SELECT working_days FROM employees WHERE LOWER(email) = ? OR LOWER(name) = ? OR LOWER(name) LIKE ? OR id = ? LIMIT 1",
            (val, val, val_like, employee_name_or_email)
        ).fetchone()
        conn.close()
        if row and row["working_days"]:
            raw_str = str(row["working_days"]).replace("[", "").replace("]", "").replace('"', "").replace("'", "")
            raw_days = [w.strip() for w in raw_str.split(",") if w.strip()]

    if not raw_days:
        # Default standard working days: Mon, Tue, Wed, Thu, Fri, Sat (Sunday week off)
        raw_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    working_days_lower = [w.lower() for w in raw_days]
    is_working = False
    for wd in working_days_lower:
        if wd == day_short.lower() or wd == day_full.lower() or wd[:3] == day_short.lower():
            is_working = True
            break

    return not is_working

def is_employee_on_leave(employee_name_or_email: str, date_str: str) -> bool:
    """Checks if an employee is marked as On Leave for the specified date."""
    conn = get_db_connection()
    val = employee_name_or_email.strip().lower()
    
    row = conn.execute("""
        SELECT is_leave, work_status, task_details FROM task_logs 
        WHERE (LOWER(employee_name) LIKE ? OR LOWER(email) LIKE ?) 
        AND (date_str = ? OR date_str LIKE ?)
    """, (f"%{val}%", f"%{val}%", date_str, f"%{date_str}%")).fetchone()
    
    conn.close()
    if row:
        d_row = dict(row)
        if d_row.get("is_leave") == 1 or str(d_row.get("work_status")).lower() in ("leave", "on leave"):
            return True
        details = str(d_row.get("task_details") or "").lower().strip()
        if "on leave" in details or details == "leave":
            return True
    return False

def is_employee_task_filled(employee_name_or_email: str, date_str: str) -> bool:
    """Checks if an employee has submitted a task log, marked On Leave, or is on Week Off for the specified date."""
    if is_employee_week_off(employee_name_or_email, date_str):
        return True

    conn = get_db_connection()
    val = employee_name_or_email.strip().lower()
    
    row = conn.execute("""
        SELECT task_details, is_leave, work_status FROM task_logs 
        WHERE (LOWER(employee_name) LIKE ? OR LOWER(email) LIKE ?) 
        AND (date_str = ? OR date_str LIKE ?)
    """, (f"%{val}%", f"%{val}%", date_str, f"%{date_str}%")).fetchone()
    
    conn.close()
    if row:
        d_row = dict(row)
        w_status = str(d_row.get("work_status")).lower()
        if d_row.get("is_leave") == 1 or w_status in ("leave", "on leave", "week off", "weekoff"):
            return True
        details = str(d_row.get("task_details") or "").strip()
        if details and (len(details) > 3 or "on leave" in details.lower() or "week off" in details.lower()):
            return True
    return False

def get_task_log_by_id(log_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM task_logs WHERE id = ?", (log_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_task_log(log_id: str) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM task_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    invalidate_leave_cache()
    return True

def delete_task_logs_batch(log_ids: List[str]) -> int:
    if not log_ids:
        return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(log_ids))
    cursor.execute(f"DELETE FROM task_logs WHERE id IN ({placeholders})", tuple(log_ids))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    invalidate_leave_cache()
    return deleted_count


def get_employee_manager_cc(identifier: str) -> str:
    """Returns the manager CC email address for a given employee name or email."""
    if not identifier:
        return "Ravi@d2backoffice.onmicrosoft.com"
    clean_id = identifier.split(" (")[0].strip().lower()
    conn = get_db_connection()
    row = conn.execute(
        "SELECT manager_cc FROM employees WHERE LOWER(email) = ? OR LOWER(name) = ?",
        (clean_id, clean_id)
    ).fetchone()
    conn.close()
    if row and row["manager_cc"]:
        return row["manager_cc"]
    return "Ravi@d2backoffice.onmicrosoft.com"

_DB_INITIALIZED = False

def ensure_db_initialized():
    """Guarantees automatic schema migration and provisioning for any new tables, columns, or indexes in Supabase PostgreSQL & SQLite."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    try:
        init_db()
    except Exception as e:
        print(f"[DB AUTO-SCHEMA MIGRATION WARN] {e}")
    _DB_INITIALIZED = True

ensure_db_initialized()


