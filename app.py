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
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Import database module and reminder engine
import database
import daily_reminder

app = Flask(__name__, template_folder="templates")

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

# --- PAGE ROUTING ENDPOINTS ---

@app.route("/")
@app.route("/dashboard")
def dashboard_page():
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

# --- REST API ENDPOINTS (SQLITE BACKED) ---

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
        database.save_employee_record(data)
        log_event(f"Updated Employee in SQLite: {data.get('name')}")
        employees = database.get_all_employees()
        return jsonify({"success": True, "employees": employees})

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
