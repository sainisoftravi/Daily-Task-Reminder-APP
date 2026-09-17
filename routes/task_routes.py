#!/usr/bin/env python3
"""
Task Entry, Work Log & Leave Operations Blueprint
Handles daily task submissions, leave requests, bulk leave, and dashboard views.
"""

import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import database

task_bp = Blueprint('task_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


@task_bp.route("/")
@task_bp.route("/dashboard")
def dashboard_page():
    user = session.get("user", {})
    if user.get("role") == "employee":
        return redirect(url_for("task_bp.task_entry_page"))
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


@task_bp.route("/task-entry")
def task_entry_page():
    return render_template("task_entry.html", active_page="task_entry")


@task_bp.route("/leave")
def leave_page():
    return render_template("leave.html", active_page="leave")


@task_bp.route("/api/task-logs", methods=["GET", "POST"])
def manage_task_logs():
    current_user = session.get("user") or {}
    user_role = current_user.get("role", "employee")
    user_name = current_user.get("name", "")
    user_email = current_user.get("email", "")

    if request.method == "GET":
        team_id = request.args.get("team_id")
        team_name = request.args.get("team_name")
        date_str = request.args.get("date_str")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        logs = database.get_task_logs(team_id=team_id, team_name=team_name, date_str=date_str, start_date=start_date, end_date=end_date)

        # Security enforcement for Employee & Manager roles:
        if user_role == "employee" and user_name:
            clean_user_name = user_name.split(" (")[0].strip().lower()
            logs = [
                l for l in logs 
                if (l.get("employee_name", "").split(" (")[0].strip().lower() == clean_user_name or 
                    (l.get("email") and l.get("email", "").strip().lower() == user_email.strip().lower()))
            ]
        elif user_role == "manager":
            mgr_team = current_user.get("teamName") or current_user.get("team_name")
            if not mgr_team:
                all_emps = database.get_all_employees()
                e_match = next((e for e in all_emps if (e.get("email") or "").strip().lower() == user_email.strip().lower() or (e.get("name") or "").strip().lower() == user_name.strip().lower()), None)
                if e_match:
                    mgr_team = e_match.get("teamName")
            if mgr_team:
                mgr_teams = [t.strip().lower() for t in mgr_team.split(",") if t.strip()]
                all_emps = database.get_all_employees()
                
                def emp_matches_mgr_teams(e):
                    e_teams = [t.strip().lower() for t in (e.get("teamName") or "").split(",") if t.strip()]
                    return any(mt in e_teams for mt in mgr_teams)

                team_emp_names = set((e.get("name") or "").split(" (")[0].strip().lower() for e in all_emps if emp_matches_mgr_teams(e))
                team_emp_emails = set((e.get("email") or "").strip().lower() for e in all_emps if emp_matches_mgr_teams(e))
                team_emp_names.add(user_name.split(" (")[0].strip().lower())
                team_emp_emails.add(user_email.strip().lower())

                def log_matches_mgr_teams(l):
                    l_teams = [t.strip().lower() for t in (l.get("team_name") or l.get("teamId") or "").split(",") if t.strip()]
                    if any(mt in l_teams for mt in mgr_teams):
                        return True
                    if (l.get("employee_name") or "").split(" (")[0].strip().lower() in team_emp_names:
                        return True
                    if (l.get("email") or "").strip().lower() in team_emp_emails:
                        return True
                    return False

                logs = [l for l in logs if log_matches_mgr_teams(l)]

        return jsonify({"success": True, "logs": logs})

    elif request.method == "POST":
        data = request.json or {}

        # Security enforcement for Employee role: Employees can only fill/update their own task logs
        if user_role == "employee":
            req_emp_name = (data.get("employeeName") or data.get("employee_name") or "").split(" (")[0].strip().lower()
            req_email = (data.get("email") or "").strip().lower()
            clean_user_name = user_name.split(" (")[0].strip().lower()

            if req_emp_name and req_emp_name != clean_user_name and req_email and req_email != user_email.strip().lower():
                return jsonify({"success": False, "error": "Forbidden: Employees are only permitted to submit or edit their own daily task logs."}), 403

            # Enforce back-date logging window restriction policy
            sys_config = database.get_system_settings()
            max_backdate = int(sys_config.get("max_backdate_days", 7))
            task_date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
            cutoff_date_str = (datetime.datetime.now() - datetime.timedelta(days=max_backdate)).strftime("%Y-%m-%d")

            if task_date_str < cutoff_date_str:
                return jsonify({"success": False, "error": f"Forbidden: Submitting or editing task logs older than {max_backdate} days ({cutoff_date_str}) is restricted by administrator policy."}), 403

            # Override/lock employee details to logged-in user
            data["employeeName"] = user_name.split(" (")[0].strip()
            data["email"] = user_email

        database.save_task_log(data)
        emp_name = (data.get("employeeName") or data.get("employee_name") or "Employee").split(" (")[0].strip()
        date_str = data.get("dateStr") or data.get("date_str") or datetime.datetime.now().strftime("%Y-%m-%d")
        log_event(f"Submitted Daily Task Log for '{emp_name}' on date '{date_str}'.")
        return jsonify({"success": True, "message": f"Task log submitted for {emp_name}"})


@task_bp.route("/api/task-logs/bulk-leave", methods=["POST"])
def api_bulk_leave():
    current_user = session.get("user") or {}
    user_role = current_user.get("role", "employee")
    user_name = current_user.get("name", "")
    user_email = current_user.get("email", "")

    data = request.json or {}
    raw_emp_name = (data.get("employeeName") or data.get("employee_name") or user_name).strip()
    emp_name = raw_emp_name.split(" (")[0].strip()
    email = (data.get("email") or user_email).strip()
    team_name = data.get("teamName") or data.get("team_name", "Infra Team")
    team_id = data.get("teamId") or data.get("team_id", "")
    leave_note = (data.get("leaveNote") or data.get("taskDetails") or "ON LEAVE").strip()
    start_date_str = data.get("startDate") or data.get("start_date")
    end_date_str = data.get("endDate") or data.get("end_date")
    skip_weekends = bool(data.get("skipWeekends", True))

    if user_role == "employee":
        clean_user_name = user_name.split(" (")[0].strip()
        if emp_name.lower() != clean_user_name.lower() and email.lower() != user_email.lower():
            return jsonify({"success": False, "error": "Forbidden: Employees are only permitted to submit leave for themselves."}), 403
        emp_name = clean_user_name
        email = user_email

    if not start_date_str or not end_date_str:
        return jsonify({"success": False, "error": "Please provide both Start Date and End Date for bulk leave."}), 400

    try:
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format. Expected YYYY-MM-DD."}), 400

    if start_dt > end_dt:
        return jsonify({"success": False, "error": "Start Date cannot be after End Date."}), 400

    # Fetch employee working days ONCE before loop for high performance
    working_days = database.get_employee_working_days(email or emp_name)

    payloads = []
    count_leave = 0
    count_weekoff = 0
    curr_dt = start_dt

    while curr_dt <= end_dt:
        dt_str = curr_dt.strftime("%Y-%m-%d")
        is_wo = database.is_date_week_off(curr_dt, working_days) if skip_weekends else False

        if is_wo:
            payloads.append({
                "employeeName": emp_name,
                "email": email,
                "teamName": team_name,
                "teamId": team_id,
                "dateStr": dt_str,
                "taskDetails": "WEEK OFF",
                "isLeave": False,
                "workStatus": "Week Off"
            })
            count_weekoff += 1
        else:
            payloads.append({
                "employeeName": emp_name,
                "email": email,
                "teamName": team_name,
                "teamId": team_id,
                "dateStr": dt_str,
                "taskDetails": leave_note if leave_note else "ON LEAVE",
                "isLeave": True,
                "workStatus": "Leave"
            })
            count_leave += 1
        curr_dt += datetime.timedelta(days=1)

    # Perform single batch DB insert/update
    database.save_task_logs_batch(payloads)

    total_processed = count_leave + count_weekoff
    log_event(f"Bulk Leave applied for '{emp_name}' across {total_processed} days ({count_leave} Leave, {count_weekoff} Week Off) from {start_date_str} to {end_date_str}.")
    return jsonify({
        "success": True,
        "count": count_leave,
        "count_weekoff": count_weekoff,
        "message": f"Successfully processed {count_leave} Leave day(s) and {count_weekoff} Week Off day(s) for {emp_name} ({start_date_str} to {end_date_str})."
    })


@task_bp.route("/api/task-logs/<log_id>", methods=["DELETE"])
def delete_task_log_route(log_id):
    current_user = session.get("user") or {}
    user_role = current_user.get("role", "employee")
    user_name = current_user.get("name", "")
    user_email = current_user.get("email", "")

    if user_role == "employee":
        log = database.get_task_log_by_id(log_id)
        if log:
            log_emp = (log.get("employee_name") or "").strip().lower()
            log_email = (log.get("email") or "").strip().lower()
            if log_emp != user_name.strip().lower() and log_email != user_email.strip().lower():
                return jsonify({"success": False, "error": "Forbidden: You cannot delete task logs belonging to other employees."}), 403

    database.delete_task_log(log_id)
    log_event(f"Deleted Task Log ID: {log_id}")
    return jsonify({"success": True})
