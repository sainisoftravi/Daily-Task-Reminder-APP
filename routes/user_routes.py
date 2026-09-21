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


def send_welcome_onboarding_email(emp_name: str, emp_email: str, manager_cc: str, temp_password: str, role: str, team_name: str = ""):
    """Dispatches onboarding welcome email notification with credentials via SMTP in a background thread."""
    def _send():
        try:
            from daily_reminder import send_email, get_logo_b64
            logo_b64 = get_logo_b64()

            clean_name = emp_name.split(" (")[0].strip()
            to_addr = (emp_email or "").strip()
            cc_addr = (manager_cc or "").strip()

            if not to_addr:
                return

            subject = f"🎉 Welcome to TickTask - Account Created ({clean_name})"
            
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
        <div style="background-color: #0f172a; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 26px 30px; text-align: center; color: #ffffff; border-bottom: 3px solid #0284c7;">
            {logo_img_html}
            <h2 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff !important;">Welcome to TickTask!</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8 !important;">Daily Task Reminder & Team Management System</p>
        </div>
        <div style="padding: 28px 30px;">
            <p style="font-size: 15px; margin-top: 0;">Dear <strong>{clean_name}</strong>,</p>
            <p style="font-size: 14px; line-height: 1.6; color: #475569;">
                Your new account has been created on the <strong>TickTask Portal</strong>. Below are your login credentials:
            </p>
            <div style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #cbd5e1; padding: 18px 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
                    🔑 Account Credentials
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; width: 140px;"><strong>Username (Email):</strong></td>
                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;"><code>{to_addr}</code></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Temporary Password:</strong></td>
                        <td style="padding: 6px 0; color: #0284c7; font-weight: 700; font-family: monospace; font-size: 15px;">{temp_password}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Assigned Role:</strong></td>
                        <td style="padding: 6px 0; color: #0f172a; text-transform: capitalize; font-weight: 600;">{role}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Team Workspace:</strong></td>
                        <td style="padding: 6px 0; color: #0f172a;">{team_name or 'Infra Team'}</td>
                    </tr>
                </table>
            </div>
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #991b1b; margin-top: 18px;">
                <strong>⚠️ Security Notice:</strong> Temporary passwords are valid for 4 hours only. You will be prompted to set your new password upon your first login.
            </div>
            <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                Best regards,<br>
                <strong>Daily Task Reminder System Team</strong>
            </p>
        </div>
    </div>
</body>
</html>"""

            body_text = f"Dear {clean_name},\n\nWelcome to TickTask!\n\nYour account has been created.\n• Username: {to_addr}\n• Temporary Password: {temp_password}\n• Role: {role}\n\nNote: Temporary passwords expire in 4 hours. Please log in to set your password.\n\nBest regards,\nDaily Task Reminder System Team"
            send_email(to_email=to_addr, cc_email=cc_addr, subject=subject, body=body_text, html_body=html_body)
            print(f"[WELCOME EMAIL SUCCESS] Dispatched onboarding welcome email to {to_addr}")
        except Exception as err:
            print(f"[WELCOME EMAIL ERROR] Failed to send welcome email to {emp_email}: {err}")

    import threading
    threading.Thread(target=_send, daemon=True).start()


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

        if is_new or (data.get("password") and data.get("password") != "••••••••••••"):
            emp_e = data.get("email", "")
            mgr_cc = data.get("managerCc") or data.get("manager_cc") or "Ravi@d2backoffice.onmicrosoft.com"
            pwd_val = data.get("password", "")
            r_val = data.get("role", "employee")
            t_val = data.get("teamName") or data.get("team_name", "")
            if emp_e and pwd_val:
                send_welcome_onboarding_email(emp_name, emp_e, mgr_cc, pwd_val, r_val, t_val)

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
