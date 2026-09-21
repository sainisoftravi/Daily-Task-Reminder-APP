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
    if user:
        if user.get("name"):
            user["name"] = user["name"].split(" (")[0].strip()
        employees = database.get_all_employees()
        email_clean = (user.get("email") or "").strip().lower()
        name_clean = user.get("name", "").lower()
        emp_match = next((e for e in employees if (e.get("email") or "").strip().lower() == email_clean or (e.get("name") or "").split(" (")[0].strip().lower() == name_clean), None)
        if emp_match:
            user["teamName"] = emp_match.get("teamName") or "Infra Team"
            user["location"] = emp_match.get("location") or "India"
            user["timezone"] = emp_match.get("timezone") or "Asia/Kolkata"
            user["shiftName"] = emp_match.get("shiftName") or "Standard Day Shift"
            user["managerCc"] = emp_match.get("managerCc") or ""
        else:
            user.setdefault("teamName", "Infra Team")
            user.setdefault("location", "India")
            user.setdefault("timezone", "Asia/Kolkata")
            user.setdefault("shiftName", "Standard Day Shift")
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
    if not user:
        return jsonify({"success": False, "user": None})

    if user.get("teamName") and user.get("location") and user.get("shiftName"):
        return jsonify({"success": True, "user": user})

    enriched_user = dict(user)
    if enriched_user.get("name"):
        enriched_user["name"] = enriched_user["name"].split(" (")[0].strip()
    employees = database.get_all_employees()
    email_clean = (user.get("email") or "").strip().lower()
    name_clean = (enriched_user.get("name") or "").strip().lower()
    emp_match = next((e for e in employees if (e.get("email") or "").strip().lower() == email_clean or (e.get("name") or "").split(" (")[0].strip().lower() == name_clean), None)
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
    session["user"] = enriched_user
    return jsonify({"success": True, "user": enriched_user})


def send_password_reset_email(email: str, temp_password: str, user_name: str = ""):
    """Dispatches password reset email notification via SMTP in a background thread."""
    def _send():
        try:
            from daily_reminder import send_email, get_logo_b64
            logo_b64 = get_logo_b64()

            clean_name = user_name or email.split("@")[0].title()
            subject = "🔐 Password Reset Request - Temporary Password Issued"
            
            logo_img_html = ""
            if logo_b64:
                logo_img_html = f'''<div style="background-color: #ffffff; padding: 10px 22px; border-radius: 8px; display: inline-block; box-shadow: 0 3px 12px rgba(0,0,0,0.2); margin-bottom: 14px;">
                    <img src="data:image/png;base64,{logo_b64}" alt="TickTask Logo" style="max-height: 44px; max-width: 220px; height: auto; width: auto; display: block; border: 0;" />
                </div>'''

            html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #334155;">
    <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
        <div style="background-color: #0f172a; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 26px 30px; text-align: center; color: #ffffff; border-bottom: 3px solid #3b82f6;">
            {logo_img_html}
            <h2 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff !important;">Password Reset Requested</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8 !important;">Daily Task Reminder System</p>
        </div>
        <div style="padding: 28px 30px;">
            <p style="font-size: 15px; margin-top: 0;">Dear <strong>{clean_name}</strong>,</p>
            <p style="font-size: 14px; line-height: 1.6; color: #475569;">
                A password reset request was initiated for your account (<code>{email}</code>). A temporary 4-hour password has been generated for you below:
            </p>
            <div style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #cbd5e1; padding: 20px; margin: 20px 0; text-align: center;">
                <div style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 6px;">Your Temporary Password</div>
                <div style="font-size: 24px; font-weight: 800; font-family: monospace; color: #0284c7; letter-spacing: 2px;">{temp_password}</div>
                <div style="font-size: 12px; color: #d97706; margin-top: 8px; font-weight: 600;">⚠️ Valid for 4 hours only</div>
            </div>
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 14px 16px; font-size: 13px; color: #991b1b; margin-top: 20px;">
                <strong>⚠️ Security Policy Notice:</strong> You will be required to change your temporary password upon logging in. If you did not request this password reset, please contact your administrator immediately.
            </div>
            <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                Best regards,<br>
                <strong>Daily Task Reminder System Team</strong>
            </p>
        </div>
    </div>
</body>
</html>"""

            body_text = f"Dear {clean_name},\n\nA password reset request was initiated for your account ({email}).\n\nYour Temporary Password: {temp_password}\n(Valid for 4 hours only)\n\nYou will be required to change this password upon logging in.\n\nBest regards,\nDaily Task Reminder System"
            send_email(to_email=email, cc_email="", subject=subject, body=body_text, html_body=html_body)
            print(f"[PASSWORD RESET EMAIL SUCCESS] Sent password reset email to {email}")
        except Exception as err:
            print(f"[PASSWORD RESET EMAIL ERROR] Failed to send password reset email to {email}: {err}")

    import threading
    threading.Thread(target=_send, daemon=True).start()


@auth_bp.route("/api/request-password-reset", methods=["POST"])
def request_password_reset():
    data = request.json or {}
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "error": "Email address is required."}), 400

    res = database.reset_user_password_with_expiry(email, hours=4)
    if not res.get("success"):
        return jsonify({"success": False, "error": res.get("error", "No account registered with this email address.")}), 404

    new_pwd = res.get("new_password")
    user_info = res.get("user") or {}
    send_password_reset_email(email, new_pwd, user_info.get("name", ""))

    log_event(f"Password reset requested for '{email}'. New temporary 4-hr password issued and email dispatched.")

    return jsonify({
        "success": True,
        "message": f"Temporary password generated and sent to {email}. Valid for 4 hours.",
        "tempPassword": new_pwd
    })


@auth_bp.route("/api/force-change-password", methods=["POST"])
def force_change_password():
    user = session.get("user")
    if not user:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.json or {}
    new_password = data.get("newPassword", "").strip()

    if not new_password or len(new_password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters long."}), 400

    email = user.get("email", "")
    res = database.update_user_password(email, old_password="", new_password=new_password, is_forced=True)
    if res.get("success"):
        user["mustChangePassword"] = False
        session["user"] = user
        log_event(f"User '{user.get('name')}' updated their password successfully.")
        return jsonify({"success": True, "message": "Password changed successfully."})

    return jsonify({"success": False, "error": res.get("error", "Failed to change password.")}), 500


@auth_bp.route("/api/change-password", methods=["POST"])
def change_password():
    user = session.get("user")
    if not user:
        return jsonify({"success": False, "error": "Authentication required."}), 401

    data = request.json or {}
    current_password = data.get("currentPassword", "").strip()
    new_password = data.get("newPassword", "").strip()

    if not new_password or len(new_password) < 4:
        return jsonify({"success": False, "error": "Password must be at least 4 characters long."}), 400

    email = user.get("email", "")
    res = database.update_user_password(email, old_password=current_password, new_password=new_password, is_forced=False)
    if res.get("success"):
        user["mustChangePassword"] = False
        session["user"] = user
        log_event(f"User '{user.get('name')}' updated their password successfully.")
        return jsonify({"success": True, "message": "Password updated successfully!"})

    return jsonify({"success": False, "error": res.get("error", "Failed to update password.")}), 400
