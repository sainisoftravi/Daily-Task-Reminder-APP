#!/usr/bin/env python3
"""
Daily Task Log Reminder System - Flask Web Application Entry Point
Author: Antigravity Assistant

Lightweight, modular WSGI application optimized for Vercel Serverless Function deployment
and Docker containers. Imports blueprints from the `routes/` package.
"""

import os
import time
import datetime
import threading
from flask import Flask, request, jsonify, redirect, url_for, session

import database
import daily_reminder

# Initialize Flask application
app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "daily_task_reminder_system_secret_key_2026")

# --- Authentication Middleware ---
EXEMPT_ROUTES = {
    '/login',
    '/api/login',
    '/api/logout',
    '/api/me',
    '/static',
    '/api/request-password-reset',
    '/api/export/task-report',
    '/api/health'
}


@app.before_request
def check_authentication():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return

    path = request.path
    if path in EXEMPT_ROUTES or path.startswith('/static'):
        return

    # Check session
    user = session.get("user")
    if not user:
        if path.startswith('/api/'):
            return jsonify({"success": False, "error": "Authentication required", "redirect": "/login"}), 401
        return redirect(url_for("auth_bp.login_page"))


@app.context_processor
def inject_user_context():
    user = session.get("user") or {}
    enriched_user = dict(user)
    if user and (user.get("email") or user.get("name")):
        if not enriched_user.get("teamName") or not enriched_user.get("location"):
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
    return dict(current_user=enriched_user, current_role=user.get("role", "employee"))


# --- CORS Middleware ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin, Access-Control-Request-Method, Access-Control-Request-Headers'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Max-Age'] = '86400'
    return response


@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options_preflight(path):
    return '', 204


@app.route('/api/health', methods=['GET'])
def health_check():
    """Ultra-lightweight keep-alive route to prevent Vercel Serverless Function cold starts."""
    return jsonify({
        "status": "warm",
        "app": "TickTask Daily Task Log System",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }), 200


def log_event(msg: str, level: str = "INFO"):
    database.log_to_db(msg, level)


# --- REGISTER BLUEPRINTS (MODULAR MICROSERVICES ARCHITECTURE) ---
from routes.auth_routes import auth_bp
from routes.task_routes import task_bp
from routes.report_routes import report_bp
from routes.user_routes import user_bp
from routes.settings_routes import settings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
app.register_blueprint(report_bp)
app.register_blueprint(user_bp)
app.register_blueprint(settings_bp)


def background_reminder_daemon():
    """Runs reminder evaluation cycle every 15 minutes continuously (local daemon only)."""
    log_event("Background Reminder Daemon started.")
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

                log_event("Evaluating 15-minute daily reminder cycle...")
                daily_reminder.run_reminder_cycle(args, emp_objects)
        except Exception as e:
            log_event(f"Daemon Error: {e}", "ERROR")

        time.sleep(900)  # 15 minutes


if __name__ == "__main__":
    # Start background daemon in separate thread for local server / docker
    t = threading.Thread(target=background_reminder_daemon, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    log_event(f"Starting Modular Flask Web Application on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
