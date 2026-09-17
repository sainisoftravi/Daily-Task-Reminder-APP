#!/usr/bin/env python3
"""
System Settings & Master Configuration Blueprint
Handles Shifts, Teams, Locations, Email Templates, Motivational Quotes, SMTP Accounts,
Daemon Audit Logs, Reminder History, and Chart Analytics.
"""

import smtplib
import datetime
from flask import Blueprint, render_template, request, jsonify, session
import database
import daily_reminder

settings_bp = Blueprint('settings_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


# --- VIEW PAGES ---

@settings_bp.route("/shifts")
def shifts_page():
    return render_template("shifts.html", active_page="shifts")


@settings_bp.route("/teams")
def teams_page():
    return render_template("teams.html", active_page="teams")


@settings_bp.route("/locations")
def locations_page():
    return render_template("locations.html", active_page="locations")


@settings_bp.route("/quotes")
def quotes_page():
    return render_template("quotes.html", active_page="quotes")


@settings_bp.route("/templates")
def templates_page():
    return render_template("templates.html", active_page="templates")


@settings_bp.route("/settings")
def settings_page():
    return render_template("settings.html", active_page="settings")


@settings_bp.route("/logs")
def logs_page():
    return render_template("logs.html", active_page="logs")


# --- REST API ENDPOINTS ---

@settings_bp.route("/api/shifts", methods=["GET", "POST"])
def manage_shifts():
    if request.method == "GET":
        shifts = database.get_all_shifts()
        return jsonify({"success": True, "shifts": shifts})
    elif request.method == "POST":
        data = request.json or {}
        database.save_shift_record(data)
        log_event(f"Updated Shift: {data.get('name')}")
        shifts = database.get_all_shifts()
        return jsonify({"success": True, "shifts": shifts})


@settings_bp.route("/api/shifts/<shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    database.delete_shift_record(shift_id)
    log_event(f"Deleted Shift ID: {shift_id}")
    shifts = database.get_all_shifts()
    return jsonify({"success": True, "shifts": shifts})


@settings_bp.route("/api/teams", methods=["GET", "POST"])
def manage_teams():
    if request.method == "GET":
        teams = database.get_all_teams()
        return jsonify({"success": True, "teams": teams})
    elif request.method == "POST":
        data = request.json or {}
        database.save_team_record(data)
        log_event(f"Updated Team: {data.get('name')}")
        teams = database.get_all_teams()
        return jsonify({"success": True, "teams": teams})


@settings_bp.route("/api/teams/<team_id>", methods=["DELETE"])
def delete_team(team_id):
    database.delete_team_record(team_id)
    log_event(f"Deleted Team ID: {team_id}")
    teams = database.get_all_teams()
    return jsonify({"success": True, "teams": teams})


@settings_bp.route("/api/locations", methods=["GET", "POST"])
def manage_locations():
    if request.method == "GET":
        locations = database.get_all_locations()
        return jsonify({"success": True, "locations": locations})
    elif request.method == "POST":
        data = request.json or {}
        database.save_location_record(data)
        log_event(f"Updated Location: {data.get('name')}")
        locations = database.get_all_locations()
        return jsonify({"success": True, "locations": locations})


@settings_bp.route("/api/locations/<loc_id>", methods=["DELETE"])
def delete_location(loc_id):
    database.delete_location_record(loc_id)
    log_event(f"Deleted Location ID: {loc_id}")
    locations = database.get_all_locations()
    return jsonify({"success": True, "locations": locations})


@settings_bp.route("/api/quotes", methods=["GET", "POST"])
def manage_quotes():
    if request.method == "GET":
        quotes = database.get_all_quotes()
        return jsonify({"success": True, "quotes": quotes})
    elif request.method == "POST":
        data = request.json or {}
        database.save_quote_record(data)
        log_event(f"Updated Motivational Thought: {data.get('quote')[:30]}...")
        quotes = database.get_all_quotes()
        return jsonify({"success": True, "quotes": quotes})


@settings_bp.route("/api/quotes/<quote_id>", methods=["DELETE"])
def delete_quote_route(quote_id):
    database.delete_quote_record(quote_id)
    log_event(f"Deleted Motivational Thought ID: {quote_id}")
    quotes = database.get_all_quotes()
    return jsonify({"success": True, "quotes": quotes})


@settings_bp.route("/api/templates", methods=["GET", "POST"])
def manage_templates():
    if request.method == "GET":
        templates = database.get_all_templates()
        return jsonify({"success": True, "templates": templates})
    elif request.method == "POST":
        data = request.json or {}
        database.save_all_templates(data)
        log_event("Updated polite email templates.")
        return jsonify({"success": True, "templates": data})


@settings_bp.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    if request.method == "GET":
        config = database.get_system_settings()
        config["smtp_accounts"] = database.get_all_smtp_accounts(mask_passwords=True)
        return jsonify({"success": True, "config": config})
    elif request.method == "POST":
        data = request.json or {}
        database.save_system_settings(data)
        log_event("Updated system SMTP configuration.")
        return jsonify({"success": True, "config": data})


@settings_bp.route("/api/smtp-accounts", methods=["GET", "POST"])
def manage_smtp_accounts():
    if request.method == "GET":
        accounts = database.get_all_smtp_accounts(mask_passwords=True)
        return jsonify({"success": True, "accounts": accounts})
    elif request.method == "POST":
        data = request.json or {}
        database.save_smtp_account(data)
        accounts = database.get_all_smtp_accounts(mask_passwords=True)
        log_event(f"Saved SMTP Account '{data.get('name', 'SMTP')}'")
        return jsonify({"success": True, "accounts": accounts})


@settings_bp.route("/api/smtp-accounts/<acc_id>", methods=["DELETE"])
def delete_smtp_account_route(acc_id):
    database.delete_smtp_account(acc_id)
    accounts = database.get_all_smtp_accounts(mask_passwords=True)
    log_event(f"Deleted SMTP Account ID '{acc_id}'")
    return jsonify({"success": True, "accounts": accounts})


@settings_bp.route("/api/smtp-accounts/test", methods=["POST"])
def test_smtp_account_route():
    data = request.json or {}
    server_host = data.get("server", "").strip()
    port = int(data.get("port", 465))
    email_addr = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if password == "••••••••••••" or not password:
        all_unmasked = database.get_all_smtp_accounts(mask_passwords=False)
        found = next((a for a in all_unmasked if a.get("email") == email_addr or a.get("id") == data.get("id")), None)
        if found and found.get("password"):
            password = database.decrypt_password(found["password"])

    if not server_host or not email_addr or not password:
        return jsonify({"success": False, "error": "Server, Sender Email, and Password are required."})

    ports_to_try = [port]
    if port == 465 and 587 not in ports_to_try:
        ports_to_try.append(587)
    elif port == 587 and 465 not in ports_to_try:
        ports_to_try.append(465)

    last_err = None
    for attempt_port in ports_to_try:
        try:
            if attempt_port == 465:
                with smtplib.SMTP_SSL(server_host, attempt_port, timeout=15) as server:
                    server.login(email_addr, password)
            else:
                with smtplib.SMTP(server_host, attempt_port, timeout=15) as server:
                    server.starttls()
                    server.login(email_addr, password)

            return jsonify({"success": True, "message": f"Successfully authenticated SMTP account {email_addr} on {server_host}:{attempt_port}!"})
        except Exception as err:
            last_err = err

    return jsonify({"success": False, "error": f"SMTP Connection Failed on {server_host}: {str(last_err)}"})


@settings_bp.route("/api/trigger-test", methods=["POST"])
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


@settings_bp.route("/api/logs")
def get_logs():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = request.args.get("query")
    logs = database.get_db_logs(limit=300, start_date=start_date, end_date=end_date, query=query)
    return jsonify({"success": True, "logs": logs})


@settings_bp.route("/api/logs/delete", methods=["POST"])
def delete_logs():
    payload = request.json or {}
    period = payload.get("period", "all")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    deleted = database.clear_db_logs(period=period, start_date=start_date, end_date=end_date)
    log_event(f"Cleaned up {deleted} system daemon logs (period: {period}, start: {start_date}, end: {end_date}).")
    return jsonify({"success": True, "deleted": deleted})


@settings_bp.route("/api/history")
def get_history():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    query = request.args.get("query")
    history = database.get_reminder_history(limit=300, start_date=start_date, end_date=end_date, query=query)
    return jsonify({"success": True, "history": history})


@settings_bp.route("/api/history/delete", methods=["POST"])
def delete_history():
    payload = request.json or {}
    period = payload.get("period", "all")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    deleted = database.clear_reminder_history(period=period, start_date=start_date, end_date=end_date)
    log_event(f"Cleaned up {deleted} email reminder history entries (period: {period}, start: {start_date}, end: {end_date}).")
    return jsonify({"success": True, "deleted": deleted})


@settings_bp.route("/api/chart-data")
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
