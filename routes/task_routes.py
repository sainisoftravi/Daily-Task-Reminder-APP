#!/usr/bin/env python3
"""
Task Entry, Work Log & Leave Operations Blueprint
Handles daily task submissions, leave requests, bulk leave, and dashboard views.
"""

import datetime
import threading
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, current_app
import database

task_bp = Blueprint('task_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


def format_date_with_day(date_str: str) -> str:
    """Formats YYYY-MM-DD or DD-Mon-YYYY into DayName, DD-Mon-YYYY (e.g. Wednesday, 14-Oct-2026)."""
    if not date_str:
        return ""
    try:
        if "-" in date_str and len(date_str.split("-")[0]) == 4:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt = datetime.datetime.strptime(date_str, "%d-%b-%Y")
        return dt.strftime("%A, %d-%b-%Y")
    except Exception:
        return date_str


def get_detailed_date_range(start_date_str: str, end_date_str: str, working_days: list, skip_weekends: bool = True):
    """Generates detailed list of dates with day names and work status."""
    try:
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        curr = start_dt
        result = []
        while curr <= end_dt:
            is_wo = database.is_date_week_off(curr, working_days) if skip_weekends else False
            result.append({
                "date": curr.strftime("%Y-%m-%d"),
                "day_name": curr.strftime("%A"),
                "formatted": curr.strftime("%a, %d-%b-%Y"),
                "status": "Week Off" if is_wo else "Leave"
            })
            curr += datetime.timedelta(days=1)
        return result
    except Exception:
        return []


def send_leave_acknowledgement(
    emp_name: str,
    emp_email: str,
    manager_cc: str,
    dates_summary: str,
    leave_note: str,
    team_name: str,
    leave_type: str = "single",
    start_date: str = "",
    end_date: str = "",
    count_leave: int = 1,
    count_weekoff: int = 0,
    detailed_dates: list = None
):
    """Sends asynchronous template-based email acknowledgement to employee and manager CC when leave is applied."""
    app = current_app._get_current_object()

    def _send():
        with app.test_request_context():
            try:
                from daily_reminder import send_email, get_logo_b64

                clean_name = emp_name.split(" (")[0].strip()
                to_addr = (emp_email or "").strip()
                cc_addr = (manager_cc or "").strip()

                if not to_addr:
                    print(f"[LEAVE ACK WARN] No email for employee '{clean_name}', skipping leave acknowledgement email.")
                    return

                single_date_formatted = format_date_with_day(start_date or dates_summary)
                start_date_formatted = format_date_with_day(start_date or dates_summary)
                end_date_formatted = format_date_with_day(end_date or dates_summary)

                dates_text = single_date_formatted if leave_type == 'single' else f"{start_date_formatted} to {end_date_formatted}"
                logo_b64 = get_logo_b64()

                template_vars = {
                    "emp_name": clean_name,
                    "emp_email": to_addr,
                    "manager_cc": cc_addr or "N/A",
                    "team_name": team_name or "Infra Team",
                    "leave_type": leave_type,
                    "single_date_formatted": single_date_formatted,
                    "start_date_formatted": start_date_formatted,
                    "end_date_formatted": end_date_formatted,
                    "count_leave": count_leave,
                    "count_weekoff": count_weekoff,
                    "leave_note": leave_note or "ON LEAVE",
                    "detailed_dates": detailed_dates or [],
                    "logo_b64": logo_b64
                }

                # Load custom templates configured via Web UI (/templates)
                db_tpls = database.get_all_templates()
                emp_tpl = db_tpls.get("leave_ack_employee", {})
                mgr_tpl = db_tpls.get("leave_notif_manager", {})

                def _replace(text: str) -> str:
                    if not text:
                        return ""
                    return (
                        text.replace("{name}", clean_name)
                            .replace("{email}", to_addr)
                            .replace("{team}", team_name or "Infra Team")
                            .replace("{dates}", dates_text)
                            .replace("{reason}", leave_note or "ON LEAVE")
                            .replace("{mgr_email}", cc_addr or "N/A")
                    )

                emp_subject = _replace(emp_tpl.get("subject")) if emp_tpl.get("subject") else f"🏖️ Leave Application Confirmation - {clean_name} ({dates_text})"
                emp_body = _replace(emp_tpl.get("body")) if emp_tpl.get("body") else f"Dear {clean_name},\n\nYour leave application for {dates_text} has been submitted successfully.\n\nReason: {leave_note or 'ON LEAVE'}\nManager CC: {cc_addr or 'N/A'}"

                # Render HTML Template for Employee
                try:
                    html_employee = render_template('emails/leave_acknowledgement_employee.html', **template_vars)
                except Exception:
                    html_employee = None

                # Send email to Employee
                send_email(
                    to_email=to_addr,
                    cc_email=cc_addr,
                    subject=emp_subject,
                    body=emp_body,
                    html_body=html_employee
                )
                print(f"[LEAVE ACK SUCCESS] Sent template-based leave acknowledgement email to {to_addr} (CC: {cc_addr})")

                # Send dedicated Manager notification email using leave_notif_manager template if Manager CC address is provided
                if cc_addr:
                    mgr_subject = _replace(mgr_tpl.get("subject")) if mgr_tpl.get("subject") else f"📢 Employee Leave Notice - {clean_name} ({team_name or 'Infra Team'}) on {dates_text}"
                    mgr_body = _replace(mgr_tpl.get("body")) if mgr_tpl.get("body") else f"Dear Team Manager,\n\nStaff member {clean_name} ({to_addr}) from team '{team_name or 'Infra Team'}' has submitted a leave application for {dates_text}.\n\nReason: {leave_note or 'ON LEAVE'}"

                    try:
                        html_manager = render_template('emails/leave_notification_manager.html', **template_vars)
                    except Exception:
                        html_manager = None

                    send_email(
                        to_email=cc_addr,
                        subject=mgr_subject,
                        body=mgr_body,
                        html_body=html_manager
                    )
                    print(f"[LEAVE MGR NOTIF SUCCESS] Sent template-based manager leave notification email to {cc_addr}")
            except Exception as err:
                print(f"[LEAVE ACK ERROR] Failed to send leave acknowledgement email: {err}")

    threading.Thread(target=_send, daemon=True).start()



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
        
        # Trigger Leave Acknowledgement email if this is a Leave log
        is_leave_log = data.get("isLeave") or str(data.get("workStatus") or data.get("work_status") or "").lower() in ("leave", "on leave")
        if is_leave_log:
            emp_email_addr = data.get("email") or user_email
            mgr_cc_addr = database.get_employee_manager_cc(emp_email_addr or emp_name)
            l_note = data.get("taskDetails") or data.get("task_details") or "ON LEAVE"
            t_name = data.get("teamName") or data.get("team_name") or "Infra Team"
            send_leave_acknowledgement(emp_name, emp_email_addr, mgr_cc_addr, date_str, l_note, t_name)

        log_event(f"Submitted Daily Task Log for '{emp_name}' on date '{date_str}'.")
        return jsonify({"success": True, "message": f"Task log submitted for {emp_name}"})


@task_bp.route("/api/leave-logs", methods=["GET"])
def api_get_leave_logs():
    """Dedicated fast endpoint for leave & week-off logs with zero-latency SQL filtering and fallback alias matching."""
    current_user = session.get("user") or {}
    user_role = current_user.get("role") or request.args.get("role") or "employee"
    user_name = request.args.get("user_name") or current_user.get("name") or ""
    user_email = request.args.get("user_email") or current_user.get("email") or ""

    clean_email = user_email.strip().lower() if user_email else None
    clean_name = user_name.split(" (")[0].strip() if user_name else None

    # Security scoping: Employee sees their own leave logs, Manager sees team leave logs, Admin sees all
    if user_role == "employee":
        logs = database.get_leave_logs(email=clean_email, employee_name=clean_name)
        if not logs and (clean_email or clean_name):
            # Fallback alias matching: fetch all leave logs and match via employee roster
            all_leave_logs = database.get_leave_logs()
            all_emps = database.get_all_employees()
            matching_names = set()
            matching_emails = set()
            if clean_email:
                matching_emails.add(clean_email)
            if clean_name:
                matching_names.add(clean_name.lower())

            for emp in all_emps:
                emp_e = (emp.get("email") or "").strip().lower()
                emp_n = (emp.get("name") or "").split(" (")[0].strip().lower()
                if (emp_e and emp_e in matching_emails) or (emp_n and emp_n in matching_names):
                    if emp_e: matching_emails.add(emp_e)
                    if emp_n: matching_names.add(emp_n)

            logs = [
                l for l in all_leave_logs
                if ((l.get("email") or "").strip().lower() in matching_emails or
                    (l.get("employee_name") or "").split(" (")[0].strip().lower() in matching_names or
                    any(mn and mn in (l.get("employee_name") or "").lower() for mn in matching_names))
            ]
    elif user_role == "manager":
        mgr_team = current_user.get("teamName") or current_user.get("team_name")
        logs = database.get_leave_logs(team_name=mgr_team)
    else:
        logs = database.get_leave_logs()

    res = jsonify({"success": True, "logs": logs, "count": len(logs)})
    res.headers["Cache-Control"] = "private, max-age=5, stale-while-revalidate=15"
    return res




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

    # Trigger Leave Acknowledgement email notification
    mgr_cc_addr = database.get_employee_manager_cc(email or emp_name)
    detailed_dates = get_detailed_date_range(start_date_str, end_date_str, working_days, skip_weekends)

    if start_date_str == end_date_str:
        dates_summary = f"{start_date_str}"
        l_type = "single"
    else:
        dates_summary = f"{start_date_str} to {end_date_str} ({count_leave} Leave day(s)"
        if count_weekoff > 0:
            dates_summary += f", {count_weekoff} Week Off day(s)"
        dates_summary += ")"
        l_type = "bulk"

    send_leave_acknowledgement(
        emp_name=emp_name,
        emp_email=email,
        manager_cc=mgr_cc_addr,
        dates_summary=dates_summary,
        leave_note=leave_note,
        team_name=team_name,
        leave_type=l_type,
        start_date=start_date_str,
        end_date=end_date_str,
        count_leave=count_leave,
        count_weekoff=count_weekoff,
        detailed_dates=detailed_dates
    )

    total_processed = count_leave + count_weekoff
    log_event(f"Bulk Leave applied for '{emp_name}' across {total_processed} days ({count_leave} Leave, {count_weekoff} Week Off) from {start_date_str} to {end_date_str}.")
    return jsonify({
        "success": True,
        "count": count_leave,
        "count_weekoff": count_weekoff,
        "message": f"Successfully processed {count_leave} Leave day(s) and {count_weekoff} Week Off day(s) for {emp_name} ({start_date_str} to {end_date_str})."
    })


@task_bp.route("/api/task-logs/bulk-delete", methods=["POST"])
def bulk_delete_task_logs_route():
    current_user = session.get("user") or {}
    user_role = current_user.get("role", "employee")
    user_name = current_user.get("name", "")
    user_email = current_user.get("email", "")

    data = request.json or {}
    log_ids = data.get("log_ids") or data.get("logIds") or []

    if not isinstance(log_ids, list) or not log_ids:
        return jsonify({"success": False, "error": "No leave record IDs selected for deletion."}), 400

    if user_role == "employee":
        clean_user_name = user_name.split(" (")[0].strip().lower()
        clean_user_email = user_email.strip().lower()

        valid_log_ids = []
        for lid in log_ids:
            log = database.get_task_log_by_id(lid)
            if log:
                l_emp = (log.get("employee_name") or "").split(" (")[0].strip().lower()
                l_email = (log.get("email") or "").strip().lower()
                if l_emp == clean_user_name or l_email == clean_user_email:
                    valid_log_ids.append(lid)
        log_ids = valid_log_ids

        if not log_ids:
            return jsonify({"success": False, "error": "Forbidden: None of the selected leave records belong to your account."}), 403

    deleted_count = database.delete_task_logs_batch(log_ids)
    log_event(f"Bulk deleted {deleted_count} leave record(s).")
    return jsonify({
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} selected leave record(s)."
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

