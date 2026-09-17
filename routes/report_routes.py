#!/usr/bin/env python3
"""
Master Reports & Task Fill Matrix Export Blueprint
Handles `/reports` view page and XLSX / PDF matrix report generator API.
"""

import io
import datetime
from flask import Blueprint, render_template, request, jsonify, session, send_file
import database
import report_generator

report_bp = Blueprint('report_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


@report_bp.route("/reports")
def reports_page():
    return render_template("reports.html", active_page="reports")


@report_bp.route("/api/export/task-report", methods=["GET"])
def export_task_report():
    fmt = (request.args.get("format") or "xlsx").lower()
    team_id = request.args.get("team_id")
    req_team_name = request.args.get("team_name")
    period = request.args.get("period") or "month"
    custom_start = request.args.get("start_date")
    custom_end = request.args.get("end_date")
    emp_name_filter = request.args.get("employee_name")

    current_user = session.get("user") or {}
    user_role = current_user.get("role", "employee")
    user_email = (current_user.get("email") or "").strip().lower()
    user_name = (current_user.get("name") or "").strip().lower()

    all_teams = database.get_all_teams()
    all_employees = database.get_all_employees()

    if user_role == "employee" and user_name:
        emp_name_filter = user_name
    elif user_role == "manager":
        mgr_team = current_user.get("teamName") or current_user.get("team_name")
        if not mgr_team:
            e_match = next((e for e in all_employees if (e.get("email") or "").strip().lower() == user_email or (e.get("name") or "").strip().lower() == user_name), None)
            if e_match:
                mgr_team = e_match.get("teamName")
        if mgr_team:
            mgr_teams = [t.strip().lower() for t in mgr_team.split(",") if t.strip()]
            if not req_team_name or req_team_name == "ALL" or req_team_name == "ALL_MGR" or req_team_name.strip().lower() == mgr_team.strip().lower():
                team_name = "All My Teams" if len(mgr_teams) > 1 else (mgr_team or "All Teams")
                filtered_employees = [
                    e for e in all_employees
                    if any(mt in [t.strip().lower() for t in (e.get("teamName") or "").split(",") if t.strip()] for mt in mgr_teams)
                ]
            else:
                req_clean = req_team_name.strip().lower()
                team_name = req_team_name
                filtered_employees = [
                    e for e in all_employees
                    if any(t.strip().lower() == req_clean for t in (e.get("teamName") or "").split(",")) or
                       (e.get("teamId") or "").strip().lower() == req_clean
                ]

    # Determine team name and filtered employees for Admin or non-manager override
    if user_role != "manager":
        team_name = "All Teams"
        filtered_employees = all_employees

        if req_team_name and req_team_name != "ALL":
            team_name = req_team_name
            req_clean = req_team_name.strip().lower()
            filtered_employees = [
                e for e in all_employees
                if (e.get("teamName") or "").strip().lower() == req_clean or
                   (e.get("teamId") or "").strip().lower() == req_clean or
                   req_clean in (e.get("teamName") or "").strip().lower() or
                   (e.get("teamName") or "").strip().lower() in req_clean
            ]
    elif team_id and team_id != "ALL":
        target_team = next((t for t in all_teams if t.get("id") == team_id or t.get("name").lower() == team_id.lower()), None)
        if target_team:
            team_name = target_team.get("name")
            target_clean = target_team.get("name").strip().lower()
            filtered_employees = [
                e for e in all_employees
                if (e.get("teamId") == team_id or
                    (e.get("teamName") or "").strip().lower() == target_clean or
                    target_clean in (e.get("teamName") or "").strip().lower())
            ]
        else:
            team_name = team_id
            team_clean = team_id.strip().lower()
            filtered_employees = [
                e for e in all_employees
                if (e.get("teamId") == team_id or
                    (e.get("teamName") or "").strip().lower() == team_clean or
                    team_clean in (e.get("teamName") or "").strip().lower())
            ]

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

    if custom_start or custom_end:
        try:
            if not custom_start:
                custom_start = custom_end
            if not custom_end:
                custom_end = custom_start
            d_start = datetime.datetime.strptime(custom_start, "%Y-%m-%d")
            d_end = datetime.datetime.strptime(custom_end, "%Y-%m-%d")
            if d_start > d_end:
                d_start, d_end = d_end, d_start
            curr = d_start
            while curr <= d_end:
                dates_list.append(curr.strftime("%Y-%m-%d"))
                curr += datetime.timedelta(days=1)
            period_label = f"{custom_start} to {custom_end}"
        except Exception:
            dates_list = [now.strftime("%Y-%m-%d")]
            period_label = custom_start or now.strftime("%Y-%m-%d")
    elif period in ("day", "today"):
        today_str = now.strftime("%Y-%m-%d")
        dates_list = [today_str]
        period_label = now.strftime("%d %b %Y")
    elif period in ("week", "this_week", "this week"):
        start_week = now - datetime.timedelta(days=now.weekday()) # Monday of current week
        for i in range(7):
            d = start_week + datetime.timedelta(days=i)
            dates_list.append(d.strftime("%Y-%m-%d"))
        period_label = f"Week of {dates_list[0]} to {dates_list[-1]}"
    elif period == "year":
        start_year = datetime.datetime(now.year, 1, 1)
        curr = start_year
        while curr.year == now.year:
            dates_list.append(curr.strftime("%Y-%m-%d"))
            curr += datetime.timedelta(days=1)
        period_label = now.strftime("Year %Y")
    else: # month / this_month / default
        import calendar
        _, last_day = calendar.monthrange(now.year, now.month)
        start_month = datetime.datetime(now.year, now.month, 1)
        end_month = datetime.datetime(now.year, now.month, last_day)
        curr = start_month
        while curr <= end_month:
            dates_list.append(curr.strftime("%Y-%m-%d"))
            curr += datetime.timedelta(days=1)
        period_label = now.strftime("%b %Y")

    # Fetch task logs for the calculated date range
    start_date = dates_list[0] if dates_list else None
    end_date = dates_list[-1] if dates_list else None
    logs = database.get_task_logs(start_date=start_date, end_date=end_date)

    raw_logs_map = {}
    for l in logs:
        d_str = l.get("date_str") or l.get("dateStr")
        e_name = (l.get("employee_name") or l.get("employeeName") or "").split(" (")[0].strip().lower()
        e_email = (l.get("email") or "").strip().lower()
        t_det = (l.get("task_details") or l.get("taskDetails") or "").strip()
        if d_str:
            if e_name:
                raw_logs_map[(d_str, e_name)] = t_det
            if e_email:
                raw_logs_map[(d_str, e_email)] = t_det

    logs_map = {}
    for d_str in dates_list:
        for emp in filtered_employees:
            emp_name_lower = (emp.get("name") or "").split(" (")[0].strip().lower()
            emp_email_lower = (emp.get("email") or "").strip().lower()
            key_name = (d_str, emp_name_lower)
            key_email = (d_str, emp_email_lower)

            existing_val = raw_logs_map.get(key_name) or raw_logs_map.get(key_email)
            if existing_val and str(existing_val).strip():
                logs_map[key_name] = existing_val
            else:
                # Fast in-memory week off check without opening DB connections inside loops
                w_days = emp.get("workingDays") or emp.get("working_days") or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                if isinstance(w_days, str):
                    w_days = [w.strip() for w in w_days.replace("[", "").replace("]", "").replace('"', "").replace("'", "").split(",") if w.strip()]
                if database.is_date_week_off(d_str, w_days):
                    logs_map[key_name] = "🏖️ Week Off"
                else:
                    logs_map[key_name] = "Data Not Available"

    # Extract logged-in user full name
    user = session.get("user") or {}
    downloaded_by = user.get("name") or user.get("email") or "System User"

    # Generate output format
    safe_team_name = team_name.replace(" ", "_").replace("/", "_")
    safe_period_label = period_label.replace(" ", "_").replace(",", "")

    try:
        if fmt == "pdf":
            file_data = report_generator.generate_pdf_report(team_name, period_label, locations_str, dates_list, filtered_employees, logs_map, downloaded_by=downloaded_by)
            filename = f"Task_Report_{safe_team_name}_{safe_period_label}.pdf"
            mimetype = "application/pdf"
        else:
            file_data = report_generator.generate_xlsx_report(team_name, period_label, locations_str, dates_list, filtered_employees, logs_map, downloaded_by=downloaded_by)
            filename = f"Task_Report_{safe_team_name}_{safe_period_label}.xlsx"
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return send_file(
            io.BytesIO(file_data),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as err:
        log_event(f"Error generating export report ({fmt}): {err}")
        return jsonify({"success": False, "error": f"Failed to generate report: {str(err)}"}), 500
