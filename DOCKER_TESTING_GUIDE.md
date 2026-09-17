# 🐳 Docker Testing, API Verification & Database Management Guide

This guide provides a reference of **Docker-only commands** for testing APIs, checking live application logs, inspecting the database, and running automated integration tests inside the local Docker environment (`daily_task_reminder_app`).

---

## 📌 Container Overview

| Container Name | Base Image | Internal Port | Host Mapping |
| :--- | :--- | :--- | :--- |
| `daily_task_reminder_app` | `daily-update-email-daily-task-reminder` | `5000` | `http://localhost:5000` |

---

## 1. 🚀 Checking Container Status & Restarting

### Check Active Container Status
```bash
docker ps --filter "name=daily_task_reminder_app"
```

### Restart Container (Applies Code Changes Instantly)
```bash
docker restart daily_task_reminder_app
```

### Rebuild and Restart Container (For Dockerfile / Dependency Changes)
```bash
docker compose up -d --build
```

---

## 2. 🧪 Running Automated Test Suite Inside Docker

### Run Integration & Performance Test Suite
```bash
docker exec daily_task_reminder_app python tests/test_bulk_leave.py
```
*Tests DB initialization, employee schedule lookup, bulk leave batch operations (<0.02s execution), and employee name sanitization.*

---

## 3. 🌐 Testing Application APIs Inside Docker

### Test Current Session User API (`/api/me`)
```bash
docker exec daily_task_reminder_app curl -s http://localhost:5000/api/me
```

### Test Employees Roster API (`/api/employees`)
```bash
docker exec daily_task_reminder_app curl -s http://localhost:5000/api/employees
```

### Test Task Submission Logs API (`/api/task-logs`)
```bash
docker exec daily_task_reminder_app curl -s http://localhost:5000/api/task-logs
```

### Test Bulk Leave Endpoint via `curl` Inside Container
```bash
docker exec daily_task_reminder_app curl -s -X POST http://localhost:5000/api/task-logs/bulk-leave \
  -H "Content-Type: application/json" \
  -d '{"employeeName":"Sachin", "email":"sachin@d2backoffice.onmicrosoft.com", "startDate":"2026-09-01", "endDate":"2026-09-05", "leaveNote":"ON LEAVE", "skipWeekends": true}'
```

---

## 4. 🗄️ Database Inspection & Querying (SQLite / Supabase)

### List All Tables in Local SQLite Database
```bash
docker exec daily_task_reminder_app sqlite3 data/app_database.db ".tables"
```

### View Recent 10 Task Logs from DB
```bash
docker exec daily_task_reminder_app sqlite3 data/app_database.db "SELECT id, employee_name, email, date_str, work_status, task_details FROM task_logs ORDER BY date_str DESC LIMIT 10;"
```

### View All Registered User Accounts
```bash
docker exec daily_task_reminder_app sqlite3 data/app_database.db "SELECT id, name, email, role, team_id FROM users;"
```

### View All Configured Employees
```bash
docker exec daily_task_reminder_app sqlite3 data/app_database.db "SELECT id, name, email, team_name, location, working_days FROM employees;"
```

### Execute Custom Python Database Query Inside Container
```bash
docker exec daily_task_reminder_app python -c "import database; print(database.get_task_logs(date_str='2026-09-17'))"
```

---

## 5. 📋 Checking Application & Daemon Logs

### View Last 50 Container Logs
```bash
docker logs --tail 50 daily_task_reminder_app
```

### Follow / Stream Live Container Logs in Real-Time
```bash
docker logs -f daily_task_reminder_app
```

### Query System Event Audit Logs Stored in DB
```bash
docker exec daily_task_reminder_app python -c "import database; print('\n'.join(database.get_db_logs(20)))"
```

### Query Reminder Email Delivery History Stored in DB
```bash
docker exec daily_task_reminder_app python -c "import database; print(database.get_reminder_history(10))"
```

---

## 💡 Recommended Developer Testing Workflow

1. Make your code changes in your workspace editor.
2. Run **`docker restart daily_task_reminder_app`** to reload the application.
3. Run **`docker exec daily_task_reminder_app python tests/test_bulk_leave.py`** to verify tests pass.
4. Run **`docker logs --tail 30 daily_task_reminder_app`** to confirm clean server logs.
5. Push your code to GitHub with confidence!
