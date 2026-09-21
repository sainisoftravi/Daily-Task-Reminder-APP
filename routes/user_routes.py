#!/usr/bin/env python3
"""
User Account & Staff Roster Management Blueprint
Handles user rosters, manager directories, role-based permissions, and employee account CRUD operations.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import database

user_bp = Blueprint('user_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


@user_bp.route("/users")
@user_bp.route("/employees")
def users_page():
    return render_template("employees.html", active_page="users")


@user_bp.route("/managers")
def managers_page():
    return redirect(url_for("user_bp.users_page"))


@user_bp.route("/api/users", methods=["GET", "POST"])
@user_bp.route("/api/employees", methods=["GET", "POST"])
def manage_employees():
    if request.method == "GET":
        employees = database.get_all_employees()
        current_user = session.get("user") or {}
        user_role = current_user.get("role", "employee")
        user_email = (current_user.get("email") or "").strip().lower()
        user_name = (current_user.get("name") or "").strip().lower()

        if user_role == "manager":
            mgr_team = current_user.get("teamName") or current_user.get("team_name")
            if not mgr_team:
                e_match = next((e for e in employees if (e.get("email") or "").strip().lower() == user_email or (e.get("name") or "").strip().lower() == user_name), None)
                if e_match:
                    mgr_team = e_match.get("teamName")
            if mgr_team:
                mgr_teams = [t.strip().lower() for t in mgr_team.split(",") if t.strip()]
                def emp_belongs_to_mgr(e):
                    if (e.get("email") or "").strip().lower() == user_email:
                        return True
                    e_teams = [t.strip().lower() for t in (e.get("teamName") or "").split(",") if t.strip()]
                    return any(mt in e_teams for mt in mgr_teams)
                employees = [e for e in employees if emp_belongs_to_mgr(e)]
        return jsonify({"success": True, "employees": employees})
    
    elif request.method == "POST":
        data = request.json or {}
        emp_id = data.get("id")
        is_new = not emp_id or emp_id == ""

        raw_pwd = data.get("password", "")
        if is_new and (not raw_pwd or len(raw_pwd) < 3):
            data["password"] = database.generate_random_password(12)
            data["mustChangePassword"] = True
            data["pwdExpiresAt"] = (database.datetime.datetime.now() + database.datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")

        database.save_employee_record(data)
        emp_name = data.get("name", "Employee")
        emp_role = data.get("role", "employee")
        log_event(f"Saved User Account Record for '{emp_name}' (Role: {emp_role}).")

        employees = database.get_all_employees()
        return jsonify({"success": True, "employees": employees})


@user_bp.route("/api/employees/<emp_id>", methods=["DELETE"])
def delete_employee_route(emp_id):
    database.delete_employee_record(emp_id)
    log_event(f"Deleted User Account ID: {emp_id}")
    employees = database.get_all_employees()
    return jsonify({"success": True, "employees": employees})


@user_bp.route("/api/managers", methods=["GET", "POST"])
def manage_managers():
    if request.method == "GET":
        managers = database.get_all_managers()
        return jsonify({"success": True, "managers": managers})
    elif request.method == "POST":
        data = request.json or {}
        database.save_manager_record(data)
        managers = database.get_all_managers()
        return jsonify({"success": True, "managers": managers})


@user_bp.route("/api/managers/<mgr_id>", methods=["DELETE"])
def delete_manager_route(mgr_id):
    database.delete_manager_record(mgr_id)
    managers = database.get_all_managers()
    return jsonify({"success": True, "managers": managers})
