#!/usr/bin/env python3
"""
Daily Task Log Reminder System - Flask Web Application & Dashboard
Author: Antigravity Assistant

Serves a multi-page Glassmorphism dashboard with SQLite database persistence
(data/app_database.db), supporting Employee Rosters, Custom Work Shifts, Multi-Team
Management, Managers Directory, Polite Email Templates, System Settings, and Background
Reminder Daemon.
"""

import os
import sys
import json
import time
import datetime
import threading
import smtplib
from typing import List, Dict, Any
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response

# Import database module, reminder engine, and report generator
import database
import daily_reminder
import report_generator

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "daily_task_reminder_system_secret_key_2026")

# --- Authentication Middleware ---
EXEMPT_ROUTES = {'/login', '/api/login', '/api/logout', '/api/me', '/static'}

@app.before_request
def check_authentication():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return

    path = request.path
    if path in EXEMPT_ROUTES or path.startswith('/static'):
        return

    # Check session
    user = session.get("user")
    if not user:
        if path.startswith('/api/'):
            return jsonify({"success": False, "error": "Authentication required", "redirect": "/login"}), 401
        return redirect(url_for("login_page"))

@app.context_processor
def inject_user_context():
    user = session.get("user") or {}
    return dict(current_user=user, current_role=user.get("role", "employee"))

# --- CORS (Cross-Origin Resource Sharing) Middleware ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Access-Control-Request-Method, Access-Control-Request-Headers'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options_preflight(path):
    return '', 204

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)

# --- AUTHENTICATION & LOGIN ROUTES ---

@app.route("/login")
def login_page():
    if session.get("user"):
        role = session["user"].get("role", "employee")
        if role == "employee":
            return redirect(url_for("task_entry_page"))
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    user = database.authenticate_user(email, password)
    if not user:
        return jsonify({"success": False, "error": "Invalid email or password. Please check your credentials."}), 401

    session["user"] = user
    log_event(f"User '{user.get('name')}' ({user.get('email')}) logged in successfully as role '{user.get('role')}'.")
    return jsonify({"success": True, "user": user})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    user = session.get("user")
    if user:
        log_event(f"User '{user.get('name')}' logged out.")
    session.clear()
    return jsonify({"success": True, "redirect": "/login"})

@app.route("/api/me")
def api_me():
    user = session.get("user")
    if user:
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "user": None})

# --- PAGE ROUTING ENDPOINTS ---

@app.route("/")
@app.route("/dashboard")
def dashboard_page():
    user = session.get("user", {})
    if user.get("role") == "employee":
        return redirect(url_for("task_entry_page"))
    employees = database.get_all_employees()
    shifts = database.get_all_shifts()
    teams = database.get_all_teams()
    history = database.get_reminder_history(20)
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        employees=employees,
        shifts=shifts,
        teams=teams,
        history=history
    )

@app.route("/employees")
def employees_page():
    return render_template("employees.html", active_page="employees")

@app.route("/shifts")
def shifts_page():
    return render_template("shifts.html", active_page="shifts")

@app.route("/teams")
def teams_page():
    return render_template("teams.html", active_page="teams")

@app.route("/locations")
def locations_page():
    return render_template("locations.html", active_page="locations")

@app.route("/managers")
def managers_page():
    return render_template("managers.html", active_page="managers")

@app.route("/quotes")
def quotes_page():
    return render_template("quotes.html", active_page="quotes")

@app.route("/templates")
def templates_page():
    return render_template("templates.html", active_page="templates")

@app.route("/settings")
def settings_page():
    return render_template("settings.html", active_page="settings")

@app.route("/logs")
def logs_page():
    return render_template("logs.html", active_page="logs")

@app.route("/task-entry")
def task_entry_page():
    return render_template("task_entry.html", active_page="task_entry")

# --- REST API ENDPOINTS (SQLITE BACKED) ---

@app.route("/api/task-logs", methods=["GET", "POST"])
def manage_task_logs():
    if request.method == "GET":
        team_id = request.args.get("team_id")
        team_name = request.args.get("team_name")
        date_str = request.args.get("date_str")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        logs = database.get_task_logs(team_id=team_id, team_name=team_name, date_str=date_str, start_date=start_date, end_date=end_date)
        return jsonify({"success": True, "logs": logs})

    elif request.method == "POST":
        data = request.json or {}
        database.save_task_log(data)
        emp_name = data.get("employeeName") or data.get("employee_name", "Employee")
        date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
        log_event(f"Submitted Daily Task Log for '{emp_name}' on date '{date_str}'.")
        return jsonify({"success": True, "message": f"Task log submitted for {emp_name}"})

@app.route("/api/task-logs/<log_id>", methods=["DELETE"])
def delete_task_log_route(log_id):
    database.delete_task_log(log_id)
    log_event(f"Deleted Task Log ID: {log_id}")
    return jsonify({"success": True})

@app.route("/api/export/task-report", methods=["GET"])
def export_task_report():
    fmt = (request.args.get("format") or "xlsx").lower()
    team_id = request.args.get("team_id")
    req_team_name = request.args.get("team_name")
    period = request.args.get("period") or "month"
    custom_start = request.args.get("start_date")
    custom_end = request.args.get("end_date")
    emp_name_filter = request.args.get("employee_name")

    all_teams = database.get_all_teams()
    all_employees = database.get_all_employees()

    # Determine team name and filtered employees
    team_name = "All Teams"
    filtered_employees = all_employees

    if req_team_name and req_team_name != "ALL":
        team_name = req_team_name
        filtered_employees = [e for e in all_employees if (e.get("teamName") or "").lower() == req_team_name.lower() or (e.get("teamId") or "").lower() == req_team_name.lower()]
    elif team_id and team_id != "ALL":
        target_team = next((t for t in all_teams if t.get("id") == team_id or t.get("name").lower() == team_id.lower()), None)
        if target_team:
            team_name = target_team.get("name")
            filtered_employees = [e for e in all_employees if (e.get("teamId") == team_id or (e.get("teamName") or "").lower() == target_team.get("name").lower())]
        else:
            team_name = team_id
            filtered_employees = [e for e in all_employees if (e.get("teamId") == team_id or (e.get("teamName") or "").lower() == team_id.lower())]

    if emp_name_filter:
        emp_match = next((e for e in all_employees if e.get("name", "").lower() == emp_name_filter.lower()), None)
        if emp_match:
            filtered_employees = [emp_match]
            if emp_match.get("teamName") and (team_name == "All Teams" or not team_name):
                team_name = emp_match.get("teamName")
        else:
            filtered_employees = [{"name": emp_name_filter, "location": "India"}]

    if not filtered_employees:
        filtered_employees = all_employees

    # If all filtered employees belong to the same team, auto-set team_name
    unique_teams = list(dict.fromkeys([e.get("teamName", "").strip() for e in filtered_employees if e.get("teamName")]))
    if len(unique_teams) == 1 and (team_name == "All Teams" or not team_name):
        team_name = unique_teams[0]

    # Determine unique team locations
    locs = list(dict.fromkeys([e.get("location", "Global").strip() for e in filtered_employees if e.get("location")]))
    locations_str = ", ".join(locs) if locs else "Global"

    # Date range calculations
    now = datetime.datetime.now()
    dates_list = []
    period_label = ""

    if custom_start and custom_end:
        try:
            d_start = datetime.datetime.strptime(custom_start, "%Y-%m-%d")
            d_end = datetime.datetime.strptime(custom_end, "%Y-%m-%d")
            curr = d_start
            while curr <= d_end:
                dates_list.append(curr.strftime("%Y-%m-%d"))
                curr += datetime.timedelta(days=1)
            period_label = f"{custom_start} to {custom_end}"
        except Exception:
            dates_list = [now.strftime("%Y-%m-%d")]
            period_label = custom_start
    elif period == "day":
        today_str = now.strftime("%Y-%m-%d")
        dates_list = [today_str]
        period_label = now.strftime("%d %b %Y")
    elif period == "week":
        for i in range(6, -1, -1):
            d = now - datetime.timedelta(days=i)
            dates_list.append(d.strftime("%Y-%m-%d"))
        period_label = f"Week of {dates_list[0]} - {dates_list[-1]}"
    elif period == "year":
        start_year = datetime.datetime(now.year, 1, 1)
        curr = start_year
        while curr <= now:
            dates_list.append(curr.strftime("%Y-%m-%d"))
            curr += datetime.timedelta(days=1)
        period_label = now.strftime("Year %Y")
    else: # month (default)
        start_month = datetime.datetime(now.year, now.month, 1)
        curr = start_month
        while curr.month == now.month and curr <= now:
            dates_list.append(curr.strftime("%Y-%m-%d"))
            curr += datetime.timedelta(days=1)
        period_label = now.strftime("%b %Y")

    # Fetch task logs for the calculated date range
    start_date = dates_list[0] if dates_list else None
    end_date = dates_list[-1] if dates_list else None
    logs = database.get_task_logs(start_date=start_date, end_date=end_date)

    logs_map = {}
    for l in logs:
        d_str = l.get("date_str") or l.get("dateStr")
        e_name = (l.get("employee_name") or l.get("employeeName") or "").strip().lower()
        if d_str and e_name:
            logs_map[(d_str, e_name)] = l.get("task_details", "")

    # Extract logged-in user full name
    user = session.get("user") or {}
    downloaded_by = user.get("name") or user.get("email") or "System User"

    # Generate output format
    safe_team_name = team_name.replace(" ", "_")
    safe_period_label = period_label.replace(" ", "_").replace(",", "")

    if fmt == "pdf":
        file_data = report_generator.generate_pdf_report(team_name, period_label, locations_str, dates_list, filtered_employees, logs_map, downloaded_by=downloaded_by)
        filename = f"Task_Report_{safe_team_name}_{safe_period_label}.pdf"
        mimetype = "application/pdf"
    else:
        file_data = report_generator.generate_xlsx_report(team_name, period_label, locations_str, dates_list, filtered_employees, logs_map, downloaded_by=downloaded_by)
        filename = f"Task_Report_{safe_team_name}_{safe_period_label}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(
        file_data,
        mimetype=mimetype,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.route("/api/quotes", methods=["GET", "POST"])
def manage_quotes():
    if request.method == "GET":
        quotes = database.get_all_quotes()
        return jsonify({"success": True, "quotes": quotes})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_quote_record(data)
        log_event(f"Updated Motivational Thought in SQLite: {data.get('quote')[:30]}...")
        quotes = database.get_all_quotes()
        return jsonify({"success": True, "quotes": quotes})

@app.route("/api/quotes/<quote_id>", methods=["DELETE"])
def delete_quote(quote_id):
    database.delete_quote_record(quote_id)
    log_event(f"Deleted Motivational Thought ID: {quote_id}")
    quotes = database.get_all_quotes()
    return jsonify({"success": True, "quotes": quotes})

@app.route("/api/employees", methods=["GET", "POST"])
def manage_employees():
    if request.method == "GET":
        employees = database.get_all_employees()
        return jsonify({"success": True, "employees": employees})
    
    elif request.method == "POST":
        data = request.json or {}
        emp_id = data.get("id")
        is_new = not emp_id or emp_id == ""

        database.save_employee_record(data)
        log_event(f"Saved Member Record in SQLite: {data.get('name')}")

        # Send Welcome Email upon creation or if requested
        emp_email = (data.get("email") or "").strip()
        pwd_raw = (data.get("password") or "").strip()
        role_str = (data.get("role") or "employee").lower()
        pwd = pwd_raw if pwd_raw else ("admin123" if role_str == "admin" else ("mgr123" if role_str == "manager" else "emp123"))

        # Determine Manager Email (from form managerCc or logged-in user)
        mgr_email = (data.get("managerCc") or "").strip()
        if not mgr_email and session.get("user") and session["user"].get("email"):
            mgr_email = session["user"].get("email").strip()

        if emp_email and (is_new or data.get("sendWelcomeEmail")):
            try:
                portal_url = request.host_url.rstrip('/') + '/login'
                role_label = role_str.capitalize()
                subject = f"Welcome to Daily Task Reminder System - Your Login Credentials"
                body = f"""Hello {data.get('name')},

Welcome to the Daily Task Reminder & Multi-Role Task Management System!

Your employee account has been created by your Manager ({mgr_email if mgr_email else 'System Administrator'}). Below are your official login details:

- Portal Login URL: {portal_url}
- Assigned Role: {role_label}
- Username (Email): {emp_email}
- Password: {pwd}

Please log in to the portal using your Username ({emp_email}) and Password to submit your daily tasks and track your work logs.

Best regards,
Daily Task Reminder System Team
"""
                daily_reminder.send_email(emp_email, mgr_email, subject, body)
                log_event(f"Dispatched Welcome Email to '{emp_email}' from Manager '{mgr_email}'.")
            except Exception as err:
                log_event(f"[WARN] Welcome Email dispatch error for '{emp_email}': {err}")

        employees = database.get_all_employees()
        return jsonify({"success": True, "employees": employees})

@app.route("/api/change-password", methods=["POST"])
def change_password():
    user = session.get("user")
    if not user:
        return jsonify({"success": False, "error": "Not authenticated."}), 401
    
    data = request.json or {}
    curr_pass = data.get("currentPassword", "")
    new_pass = data.get("newPassword", "")

    if not curr_pass or not new_pass:
        return jsonify({"success": False, "error": "Current password and new password are required."})

    res = database.update_user_password(user["email"], curr_pass, new_pass)
    if res.get("success"):
        log_event(f"User '{user['email']}' successfully changed their account password.")
        session["user"]["password"] = new_pass
        session.modified = True
    return jsonify(res)

@app.route("/api/employees/<emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    database.delete_employee_record(emp_id)
    log_event(f"Deleted Employee ID: {emp_id}")
    employees = database.get_all_employees()
    return jsonify({"success": True, "employees": employees})

@app.route("/api/shifts", methods=["GET", "POST"])
def manage_shifts():
    if request.method == "GET":
        shifts = database.get_all_shifts()
        return jsonify({"success": True, "shifts": shifts})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_shift_record(data)
        log_event(f"Updated Shift in SQLite: {data.get('name')}")
        shifts = database.get_all_shifts()
        return jsonify({"success": True, "shifts": shifts})

@app.route("/api/shifts/<shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    database.delete_shift_record(shift_id)
    log_event(f"Deleted Shift ID: {shift_id}")
    shifts = database.get_all_shifts()
    return jsonify({"success": True, "shifts": shifts})

@app.route("/api/teams", methods=["GET", "POST"])
def manage_teams():
    if request.method == "GET":
        teams = database.get_all_teams()
        return jsonify({"success": True, "teams": teams})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_team_record(data)
        log_event(f"Updated Team in SQLite: {data.get('name')}")
        teams = database.get_all_teams()
        return jsonify({"success": True, "teams": teams})

@app.route("/api/teams/<team_id>", methods=["DELETE"])
def delete_team(team_id):
    database.delete_team_record(team_id)
    log_event(f"Deleted Team ID: {team_id}")
    teams = database.get_all_teams()
    return jsonify({"success": True, "teams": teams})

@app.route("/api/locations", methods=["GET", "POST"])
def manage_locations():
    if request.method == "GET":
        locations = database.get_all_locations()
        return jsonify({"success": True, "locations": locations})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_location_record(data)
        log_event(f"Updated Location in SQLite: {data.get('name')}")
        locations = database.get_all_locations()
        return jsonify({"success": True, "locations": locations})

@app.route("/api/locations/<loc_id>", methods=["DELETE"])
def delete_location(loc_id):
    database.delete_location_record(loc_id)
    log_event(f"Deleted Location ID: {loc_id}")
    locations = database.get_all_locations()
    return jsonify({"success": True, "locations": locations})

@app.route("/api/managers", methods=["GET", "POST"])
def manage_managers():
    if request.method == "GET":
        managers = database.get_all_managers()
        return jsonify({"success": True, "managers": managers})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_manager_record(data)
        log_event(f"Updated Manager in SQLite: {data.get('name')}")
        managers = database.get_all_managers()
        return jsonify({"success": True, "managers": managers})

@app.route("/api/managers/<mgr_id>", methods=["DELETE"])
def delete_manager(mgr_id):
    database.delete_manager_record(mgr_id)
    log_event(f"Deleted Manager ID: {mgr_id}")
    managers = database.get_all_managers()
    return jsonify({"success": True, "managers": managers})

@app.route("/api/templates", methods=["GET", "POST"])
def manage_templates():
    if request.method == "GET":
        templates = database.get_all_templates()
        return jsonify({"success": True, "templates": templates})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_all_templates(data)
        log_event("Updated polite email templates in SQLite.")
        return jsonify({"success": True, "templates": data})

@app.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    if request.method == "GET":
        config = database.get_system_settings()
        config["smtp_accounts"] = database.get_all_smtp_accounts(mask_passwords=True)
        return jsonify({"success": True, "config": config})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_system_settings(data)
        log_event("Updated system SMTP configuration in SQLite.")
        return jsonify({"success": True, "config": data})

@app.route("/api/smtp-accounts", methods=["GET", "POST"])
def manage_smtp_accounts():
    if request.method == "GET":
        accounts = database.get_all_smtp_accounts(mask_passwords=True)
        return jsonify({"success": True, "accounts": accounts})
    elif request.method == "POST":
        data = request.json or {}
        database.save_smtp_account(data)
        accounts = database.get_all_smtp_accounts(mask_passwords=True)
        log_event(f"Saved SMTP Account '{data.get('name', 'SMTP')}' in SQLite.")
        return jsonify({"success": True, "accounts": accounts})

@app.route("/api/smtp-accounts/<acc_id>", methods=["DELETE"])
def delete_smtp_account_route(acc_id):
    database.delete_smtp_account(acc_id)
    accounts = database.get_all_smtp_accounts(mask_passwords=True)
    log_event(f"Deleted SMTP Account ID '{acc_id}' from SQLite.")
    return jsonify({"success": True, "accounts": accounts})

@app.route("/api/smtp-accounts/test", methods=["POST"])
def test_smtp_account_route():
    data = request.json or {}
    server_host = data.get("server", "").strip()
    port = int(data.get("port", 465))
    email_addr = data.get("email", "").strip()
    password = data.get("password", "").strip()

    # If password is masked, decrypt stored password
    if password == "••••••••••••" or not password:
        all_unmasked = database.get_all_smtp_accounts(mask_passwords=False)
        found = next((a for a in all_unmasked if a.get("email") == email_addr or a.get("id") == data.get("id")), None)
        if found and found.get("password"):
            password = database.decrypt_password(found["password"])

    if not server_host or not email_addr or not password:
        return jsonify({"success": False, "error": "Server, Sender Email, and Password are required."})

    try:
        if port == 465:
            with smtplib.SMTP_SSL(server_host, port, timeout=15) as server:
                server.login(email_addr, password)
        else:
            with smtplib.SMTP(server_host, port, timeout=15) as server:
                server.starttls()
                server.login(email_addr, password)

        return jsonify({"success": True, "message": f"Successfully authenticated SMTP account {email_addr} on {server_host}:{port}!"})
    except Exception as err:
        return jsonify({"success": False, "error": f"SMTP Connection Failed: {str(err)}"})

@app.route("/api/trigger-test", methods=["POST"])
def trigger_test():
    payload = request.json or {}
    emp_name = payload.get("employeeName")
    force_time = payload.get("forceTime", "18:30")
    
    log_event(f"Manual Test Trigger requested for '{emp_name}' at forced time '{force_time}'...")

    config = database.get_system_settings()
    employees_raw = database.get_all_employees()

    emp_objects = []
    for e in employees_raw:
        emp_objects.append(daily_reminder.Employee(
            name=e["name"],
            email=e["email"],
            location=e["location"],
            timezone_str=e["timezone"],
            working_days=",".join(e.get("workingDays", [])),
            sheet_name=e.get("sheetName", "Technical Infra Team-Aug-2026"),
            manager_cc=e.get("managerCc", "Ravi@d2backoffice.onmicrosoft.com"),
            reminders=e.get("reminders")
        ))

    class Args:
        pass
    args = Args()
    args.config = database.DB_FILE
    args.test_employee = emp_name
    args.dry_run = payload.get("dryRun", False)
    args.force_time = force_time
    args.force_date = payload.get("forceDate")
    args.excel_file = config.get("excel_file_path", "Daily Task and Update Sheet.xlsx")
    args.sharepoint_url = config.get("sharepoint_url")

    try:
        daily_reminder.run_reminder_cycle(args, emp_objects)
        log_event(f"Manual Test completed successfully for '{emp_name}'.")
        return jsonify({"success": True, "message": f"Test executed for {emp_name}"})
    except Exception as err:
        log_event(f"Error executing test: {err}", "ERROR")
        return jsonify({"success": False, "error": str(err)})

@app.route("/api/logs")
def get_logs():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = request.args.get("query")
    logs = database.get_db_logs(limit=300, start_date=start_date, end_date=end_date, query=query)
    return jsonify({"success": True, "logs": logs})

@app.route("/api/logs/delete", methods=["POST"])
def delete_logs():
    payload = request.json or {}
    period = payload.get("period", "all")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    deleted = database.clear_db_logs(period=period, start_date=start_date, end_date=end_date)
    log_event(f"Cleaned up {deleted} system daemon logs (period: {period}, start: {start_date}, end: {end_date}).")
    return jsonify({"success": True, "deleted": deleted})

@app.route("/api/history")
def get_history():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = request.args.get("query")
    history = database.get_reminder_history(limit=300, start_date=start_date, end_date=end_date, query=query)
    return jsonify({"success": True, "history": history})

@app.route("/api/history/delete", methods=["POST"])
def delete_history():
    payload = request.json or {}
    period = payload.get("period", "all")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    deleted = database.clear_reminder_history(period=period, start_date=start_date, end_date=end_date)
    log_event(f"Cleaned up {deleted} email reminder history entries (period: {period}, start: {start_date}, end: {end_date}).")
    return jsonify({"success": True, "deleted": deleted})

@app.route("/api/chart-data")
def get_chart_data():
    period = request.args.get("period", "all")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    now = datetime.datetime.now()
    if period == "day":
        start_date = now.strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
    elif period == "week":
        start_date = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
    elif period == "month":
        start_date = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

    history = database.get_reminder_history(limit=1000, start_date=start_date, end_date=end_date)
    employees = database.get_all_employees()
    teams = database.get_all_teams()

    user_counts = {}
    for emp in employees:
        user_counts[emp["name"]] = 0

    team_counts = {}
    for team in teams:
        team_counts[team["name"]] = 0
    if "Technical Infra Team" not in team_counts:
        team_counts["Technical Infra Team"] = 0

    time_counts = {"18:30 (Reminder 1)": 0, "18:45 (Reminder 2)": 0, "19:00 (Reminder 3)": 0, "Other": 0}

    for item in history:
        emp_name = item.get("employee_name", "Unknown")
        user_counts[emp_name] = user_counts.get(emp_name, 0) + 1

        rem_type = item.get("reminder_type", "")
        if "18:30" in rem_type or "first" in rem_type.lower():
            time_counts["18:30 (Reminder 1)"] += 1
        elif "18:45" in rem_type or "second" in rem_type.lower():
            time_counts["18:45 (Reminder 2)"] += 1
        elif "19:00" in rem_type or "final" in rem_type.lower():
            time_counts["19:00 (Reminder 3)"] += 1
        else:
            time_counts["Other"] += 1

        matched_team = "Technical Infra Team"
        for emp in employees:
            if emp["name"].lower() in emp_name.lower() or emp_name.lower() in emp["name"].lower():
                matched_team = emp.get("teamName") or "Technical Infra Team"
                break
        team_counts[matched_team] = team_counts.get(matched_team, 0) + 1

    return jsonify({
        "success": True,
        "userStats": user_counts,
        "teamStats": team_counts,
        "timeStats": time_counts
    })

def background_reminder_daemon():
    """Runs reminder evaluation cycle every 15 minutes continuously using SQLite DB."""
    log_event("Background Reminder Daemon started (SQLite persistent DB active).")
    while True:
        try:
            config = database.get_system_settings()
            employees_raw = database.get_all_employees()

            if employees_raw:
                emp_objects = []
                for e in employees_raw:
                    emp_objects.append(daily_reminder.Employee(
                        name=e["name"],
                        email=e["email"],
                        location=e["location"],
                        timezone_str=e["timezone"],
                        working_days=",".join(e.get("workingDays", [])),
                        sheet_name=e.get("sheetName", "Technical Infra Team-Aug-2026"),
                        manager_cc=e.get("managerCc", "Ravi@d2backoffice.onmicrosoft.com"),
                        reminders=e.get("reminders")
                    ))

                class Args:
                    pass
                args = Args()
                args.config = database.DB_FILE
                args.test_employee = None
                args.dry_run = config.get("dry_run", False)
                args.force_time = None
                args.force_date = None
                args.excel_file = config.get("excel_file_path", "Daily Task and Update Sheet.xlsx")
                args.sharepoint_url = config.get("sharepoint_url")

                log_event("Evaluating 15-minute daily reminder cycle across SQLite staff roster...")
                daily_reminder.run_reminder_cycle(args, emp_objects)
        except Exception as e:
            log_event(f"Daemon Error: {e}", "ERROR")

        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    # Start background daemon in separate thread
    t = threading.Thread(target=background_reminder_daemon, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    log_event(f"Starting Multi-Page Flask Web Application on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
