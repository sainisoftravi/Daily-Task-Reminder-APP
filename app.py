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
from typing import List, Dict, Any
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Import database module and reminder engine
import database
import daily_reminder

app = Flask(__name__, template_folder="templates")

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
        return jsonify({"success": True, "config": config})
    
    elif request.method == "POST":
        data = request.json or {}
        database.save_system_settings(data)
        log_event("Updated system SMTP configuration in SQLite.")
        return jsonify({"success": True, "config": data})

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
        database.record_reminder_history(emp_name, "test@company.com", force_time, "TEST_SENT", datetime.datetime.now().strftime("%d-%b-%y"))
        log_event(f"Manual Test completed successfully for '{emp_name}'.")
        return jsonify({"success": True, "message": f"Test executed for {emp_name}"})
    except Exception as err:
        log_event(f"Error executing test: {err}", "ERROR")
        return jsonify({"success": False, "error": str(err)})

@app.route("/api/logs")
def get_logs():
    logs = database.get_db_logs(200)
    return jsonify({"success": True, "logs": logs})

@app.route("/api/history")
def get_history():
    history = database.get_reminder_history(100)
    return jsonify({"success": True, "history": history})

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

    log_event("Starting Multi-Page Flask Web Application on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
