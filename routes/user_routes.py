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


def send_welcome_onboarding_email(emp_name: str, emp_email: str, manager_cc: str, temp_password: str, role: str, team_name: str = "", portal_url: str = ""):
    """Dispatches onboarding welcome email notification using the GUI-configured 'welcome_email' template from the database."""
    def _send():
        try:
            import datetime
            from daily_reminder import send_email, get_logo_b64
            logo_b64 = get_logo_b64()

            clean_name = emp_name.split(" (")[0].strip()
            to_addr = (emp_email or "").strip()
            cc_addr = (manager_cc or "").strip()

            if not to_addr:
                return

            role_clean = (role or "employee").lower()
            role_title = role_clean.title()

            p_url = portal_url
            if not p_url:
                try:
                    p_url = request.host_url.rstrip("/")
                except Exception:
                    p_url = "https://ticktask-silk.vercel.app"

            # 1. Fetch template from Database (GUI configurable via /templates)
            all_tpls = database.get_all_templates()
            tpl = all_tpls.get("welcome_email", {})

            default_subject = "🎉 Welcome to TickTask - {role} Account Created ({name})"
            default_body = "Dear {name},\n\nYour new {role} account has been created on the TickTask Portal. Below are your login credentials:\n\n• Portal Login URL: {portal_url}\n• Username (Email): {email}\n• Temporary Password: {password}\n• Assigned Role: {role}\n• Team Workspace: {team}\n\nNote: Temporary passwords expire in 4 hours. You will be prompted to set your new permanent password upon your first login."
            default_ignore = "⚠️ Security Notice: Temporary passwords are valid for 4 hours only. Must be changed upon first login."

            raw_subject = tpl.get("subject") or default_subject
            raw_body = tpl.get("body") or default_body
            raw_ignore = tpl.get("ignore_note") or default_ignore

            # 2. Perform dynamic variable replacements
            replacements = {
                "{name}": clean_name,
                "{email}": to_addr,
                "{password}": temp_password,
                "{role}": role_title,
                "{team}": team_name or 'Infra Team',
                "{portal_url}": p_url,
                "{mgr_email}": cc_addr or "Ravi@d2backoffice.onmicrosoft.com",
                "{date}": datetime.datetime.now().strftime("%d-%b-%Y")
            }

            final_subject = raw_subject
            final_body = raw_body
            final_ignore = raw_ignore

            for k_var, v_var in replacements.items():
                final_subject = final_subject.replace(k_var, str(v_var))
                final_body = final_body.replace(k_var, str(v_var))
                final_ignore = final_ignore.replace(k_var, str(v_var))

            # Role badge HTML
            if role_clean == "admin":
                role_badge_html = '<span style="background-color: #fef2f2; color: #991b1b; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 12px; border: 1px solid #fecaca; display: inline-block;">🛡️ Admin</span>'
            elif role_clean == "manager":
                role_badge_html = '<span style="background-color: #f3e8ff; color: #6b21a8; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 12px; border: 1px solid #e9d5ff; display: inline-block;">👔 Manager</span>'
            else:
                role_badge_html = '<span style="background-color: #e0f2fe; color: #075985; padding: 4px 12px; border-radius: 12px; font-weight: 700; font-size: 12px; border: 1px solid #bae6fd; display: inline-block;">👤 Employee</span>'

            logo_img_html = ""
            if logo_b64:
                logo_img_html = f'''<div style="background-color: #ffffff; padding: 10px 22px; border-radius: 8px; display: inline-block; box-shadow: 0 3px 12px rgba(0,0,0,0.2); margin-bottom: 14px;">
                    <img src="data:image/png;base64,{logo_b64}" alt="TickTask Logo" style="max-height: 44px; max-width: 220px; height: auto; width: auto; display: block; border: 0;" />
                </div>'''

            # Format body text paragraphs and credentials box
            body_paragraphs = []
            for block in final_body.split("\n\n"):
                if not block.strip():
                    continue
                body_paragraphs.append(f'<p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 14px 0;">{block.replace(chr(10), "<br>")}</p>')

            body_html_content = "".join(body_paragraphs)

            credentials_box_html = f"""
            <div style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #cbd5e1; padding: 18px 20px; margin: 20px 0;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
                    🔑 ACCOUNT CREDENTIALS
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; width: 140px;"><strong>Portal Login URL:</strong></td>
                        <td style="padding: 6px 0; color: #0284c7; font-weight: 600;"><a href="{p_url}" style="color: #0284c7; text-decoration: underline;">{p_url}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Username (Email):</strong></td>
                        <td style="padding: 6px 0; color: #0f172a; font-weight: 600;"><code>{to_addr}</code></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Temporary Password:</strong></td>
                        <td style="padding: 6px 0; color: #0284c7; font-weight: 700; font-family: monospace; font-size: 15px;">{temp_password}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Assigned Role:</strong></td>
                        <td style="padding: 6px 0;">{role_badge_html}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;"><strong>Team Workspace:</strong></td>
                        <td style="padding: 6px 0; color: #0f172a;">{team_name or 'Infra Team'}</td>
                    </tr>
                </table>
            </div>
            """

            ignore_box_html = ""
            if final_ignore and final_ignore.strip():
                ignore_box_html = f"""
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #991b1b; margin-top: 18px;">
                    <strong>{final_ignore}</strong>
                </div>
                """

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
            {body_html_content}
            {credentials_box_html}
            {ignore_box_html}
            <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
                Best regards,<br>
                <strong>Daily Task Reminder System Team</strong>
            </p>
        </div>
    </div>
</body>
</html>"""

            send_email(to_email=to_addr, cc_email=cc_addr, subject=final_subject, body=final_body, html_body=html_body)
            print(f"[WELCOME EMAIL SUCCESS] Dispatched onboarding welcome email ({role_title}) using GUI DB template to {to_addr}")
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

        emp_e = (data.get("email") or "").strip()
        if database.check_email_exists(emp_e, emp_id):
            return jsonify({
                "success": False,
                "error": f"Email address '{emp_e}' is already registered. Duplicate email addresses cannot be used."
            }), 400

        raw_pwd = data.get("password", "")
        if is_new and (not raw_pwd or len(raw_pwd) < 3):
            data["password"] = database.generate_random_password(12)
            data["mustChangePassword"] = True
            data["pwdExpiresAt"] = (database.datetime.datetime.now() + database.datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")

        database.save_employee_record(data)
        emp_name = data.get("name", "User Account")
        emp_role = (data.get("role") or "employee").lower()
        log_event(f"Saved User Account Record for '{emp_name}' (Role: {emp_role}).")

        if is_new or (data.get("password") and data.get("password") != "••••••••••••"):
            pwd_val = data.get("password", "")
            t_val = data.get("teamName") or data.get("team_name", "")
            p_url = ""
            try:
                p_url = request.host_url.rstrip("/")
            except Exception:
                p_url = "https://ticktask-silk.vercel.app"

            if emp_e and pwd_val:
                # Credentials sent STRICTLY to the new user (no manager CC on password email)
                send_welcome_onboarding_email(emp_name, emp_e, "", pwd_val, emp_role, t_val, portal_url=p_url)

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
        mgr_id = data.get("id")
        is_new = not mgr_id or mgr_id == ""
        data["role"] = "manager"

        mgr_email = (data.get("email") or "").strip()
        if database.check_email_exists(mgr_email, mgr_id):
            return jsonify({
                "success": False,
                "error": f"Email address '{mgr_email}' is already registered. Duplicate email addresses cannot be used."
            }), 400

        raw_pwd = data.get("password", "")
        if is_new and (not raw_pwd or len(raw_pwd) < 3):
            data["password"] = database.generate_random_password(12)
            data["mustChangePassword"] = True
            data["pwdExpiresAt"] = (database.datetime.datetime.now() + database.datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")

        database.save_employee_record(data)

        if is_new or (data.get("password") and data.get("password") != "••••••••••••"):
            mgr_name = data.get("name", "Manager")
            pwd_val = data.get("password", "")
            t_val = data.get("teamName") or data.get("team_name", "")
            p_url = ""
            try:
                p_url = request.host_url.rstrip("/")
            except Exception:
                p_url = "https://ticktask-silk.vercel.app"

            if mgr_email and pwd_val:
                send_welcome_onboarding_email(mgr_name, mgr_email, "", pwd_val, "manager", t_val, portal_url=p_url)

        managers = database.get_all_managers()
        return jsonify({"success": True, "managers": managers})


@user_bp.route("/api/managers/<mgr_id>", methods=["DELETE"])
def delete_manager_route(mgr_id):
    database.delete_manager_record(mgr_id)
    managers = database.get_all_managers()
    return jsonify({"success": True, "managers": managers})

