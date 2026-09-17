#!/usr/bin/env python3
"""
Authentication & Session Management Routes Blueprint
Handles user login, logout, profile details, and password resets.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import database

auth_bp = Blueprint('auth_bp', __name__)

def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


@auth_bp.route("/login")
def login_page():
    if session.get("user"):
        role = session["user"].get("role", "employee")
        if role == "employee":
            return redirect(url_for("task_bp.task_entry_page"))
        return redirect(url_for("task_bp.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    email = data.get("email", "")
    password = data.get("password", "")

    res = database.authenticate_user(email, password)
    if not res.get("success"):
        return jsonify({"success": False, "error": res.get("error", "Invalid email or password.")}), 401

    user = res.get("user")
    session["user"] = user
    log_event(f"User '{user.get('name')}' ({user.get('email')}) logged in successfully as role '{user.get('role')}'.")
    return jsonify({
        "success": True,
        "user": user,
        "mustChangePassword": res.get("mustChangePassword", False)
    })


@auth_bp.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    user = session.get("user")
    if user:
        log_event(f"User '{user.get('name')}' logged out.")
    session.clear()
    return jsonify({"success": True, "redirect": "/login"})


@auth_bp.route("/api/me")
def api_me():
    user = session.get("user")
    if user:
        enriched_user = dict(user)
        employees = database.get_all_employees()
        email_clean = (user.get("email") or "").strip().lower()
        name_clean = (user.get("name") or "").strip().lower()
        emp_match = next((e for e in employees if (e.get("email") or "").strip().lower() == email_clean or (e.get("name") or "").strip().lower() == name_clean), None)
        if emp_match:
            enriched_user["teamName"] = emp_match.get("teamName") or "Infra Team"
            enriched_user["location"] = emp_match.get("location") or "India"
            enriched_user["timezone"] = emp_match.get("timezone") or "Asia/Kolkata"
            enriched_user["shiftName"] = emp_match.get("shiftName") or "Standard Day Shift"
            enriched_user["managerCc"] = emp_match.get("managerCc") or ""
        else:
            enriched_user.setdefault("teamName", "Infra Team")
            enriched_user.setdefault("location", "India")
            enriched_user.setdefault("timezone", "Asia/Kolkata")
            enriched_user.setdefault("shiftName", "Standard Day Shift")
        return jsonify({"success": True, "user": enriched_user})
    return jsonify({"success": False, "user": None})


@auth_bp.route("/api/request-password-reset", methods=["POST"])
def request_password_reset():
    data = request.json or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "error": "Email address is required."}), 400

    user = database.get_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "No account registered with this email address."}), 404

    new_pwd = database.generate_random_password(12)
    res = database.reset_user_password_with_expiry(email, new_pwd, hours_valid=4)

    if not res.get("success"):
        return jsonify({"success": False, "error": res.get("error", "Failed to reset password.")}), 500

    log_event(f"Password reset requested for '{email}'. New temporary 4-hr password issued.")

    return jsonify({
        "success": True,
        "message": f"Temporary password generated: {new_pwd} (Valid for 4 hours). User will be prompted to change password upon login.",
        "tempPassword": new_pwd
    })


@auth_bp.route("/api/force-change-password", methods=["POST"])
def force_change_password():
    user = session.get("user")
    if not user:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.json or {}
    new_password = data.get("newPassword", "").strip()

    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

    res = database.update_user_password(user.get("id") or user.get("email"), new_password, clear_must_change=True)
    if res.get("success"):
        user["mustChangePassword"] = False
        session["user"] = user
        log_event(f"User '{user.get('name')}' updated their password successfully.")
        return jsonify({"success": True, "message": "Password changed successfully."})

    return jsonify({"success": False, "error": res.get("error", "Failed to change password.")}), 500
