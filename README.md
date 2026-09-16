# 🚀 Automated Daily Task & Work Log Reminder System

A complete, enterprise-grade automated daily task reminder web application and daemon engine built with **Flask**, **SQLite Database**, **Chart.js Analytics**, **Python**, and **Docker**.

Supports multi-timezone staff roster management (**India, UAE, Saudi Arabia, USA, UK, Singapore**), customizable work shifts, team management, rich HTML email notifications with dynamic **Thought of the Day** quote rotation, courtesy ignore disclaimers, and automated Excel / SharePoint sheet verification.

---

## 📑 Table of Contents
1. [Architecture & System Features](#1-architecture--system-features)
2. [Web Application Pages Sitemap](#2-web-application-pages-sitemap)
3. [Complete REST API Reference](#3-complete-rest-api-reference)
4. [Automated Daemon Engine & Reminder Workflow](#4-automated-daemon-engine--reminder-workflow)
5. [Rich HTML Email & Quote Rotator](#5-rich-html-email--quote-rotator)
6. [Docker Deployment Guide](#6-docker-deployment-guide)

---

## 1. Architecture & System Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Glassmorphism Web Dashboard (Port 5000)                     │
│  Analytics Charts • Staff Roster • Shifts • Teams • Templates • Quotes • Logs │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Thread-Safe SQLite Database Layer                          │
│                      (data/app_database.db)                                 │
│    employees • shifts • teams • locations • managers • templates • quotes   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Background Reminder Daemon (Every 15 Mins)                  │
│   Timezone Check ➔ Task Sheet Verification ➔ Stage Quote ➔ SSL SMTP Dispatch │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Persistence**: All data stored permanently in SQLite DB (`data/app_database.db`) with volume mounting.
- **Multi-Timezone Support**: Evaluates local employee time in IST, GST, AST, EST, PST, GMT, SGT independently.
- **Dynamic Work Shifts**: Automatically computes Reminder 1 (30m before shift end), Reminder 2 (15m before shift end), and Reminder 3 (Shift close).
- **Courtesy Ignore Disclaimer**: Appends polite notice for employees who updated their logs.
- **Stage-Aware Thought of the Day**: Rotates motivational quotes daily matched to shift stages.
- **Global CORS Enabled**: Preconfigured with `Access-Control-Allow-Origin: *`, `OPTIONS` preflight handling, and wildcard header permissions across all REST API endpoints.

---

## 2. Web Application Pages Sitemap

| Page Route | Title | Key Features & Purpose |
| :--- | :--- | :--- |
| `/dashboard` | **Realtime Analytics Dashboard** | Chart.js bar & doughnut visualizations for user/team email delivery with **Day**, **Week**, **Month**, and **📅 Calendar Date Range** filters, alongside live timelog submission status per employee. |
| `/employees` | **Employee Roster Management** | Add, edit, or delete staff members. Assign locations with auto-filled timezones, work shifts, working days, teams, sheet names, and manager CC emails. Search & filter controls included. |
| `/shifts` | **Custom Work Shift Creation** | Create and manage custom work shift hours (e.g. 10:00 - 19:00, 09:00 - 17:00, Night Shift). Automatically calculates 30m, 15m, and Shift End trigger times. |
| `/teams` | **Teams Management** | Manage multi-team structures (Technical Infra Team, IoT Team, Cloud Ops, etc.) and map each team to its corresponding Excel worksheet tab. |
| `/locations` | **Locations & Timezones** | Directory of global office locations (India, UAE, Saudi Arabia, USA, UK, Singapore) and their IANA timezone strings (`Asia/Kolkata`, `Asia/Dubai`, `Asia/Riyadh`, etc.). |
| `/managers` | **Managers Directory** | Manage manager contact records for automatic email CC notifications during reminder escalation. |
| `/templates` | **Email & Ignore Templates** | Configure polite notification templates for **Reminder 1**, **Reminder 2**, **Reminder 3**, and **Log Hours Filled Courtesy Template** with Real-Time Live Preview & `{name}`, `{date}`, `{quote}` variable substitution. |
| `/quotes` | **Thought of the Day Library** | View, add, edit, or delete motivational quotes using a Category Dropdown selector (`Focus, Progress & Consistency`, `Teamwork, Impact & Reliability`, `Recharge, Balance & Perspective`). |
| `/settings` | **Multi-SMTP & System Config** | Configure **Default System SMTP** & **Manager-Specific SMTP Accounts** with **Fernet AES Encryption at Rest** and API password masking, manager email routing rules, SharePoint direct link, and local Excel path. |
| `/logs` | **Daemon Logs & Audit Trail** | View live execution logs and SQLite email dispatch history table. Features an interactive **📅 Select Date Range** calendar popover button (`Start Date` & `End Date`), range-based log filtering and deletion, and a `Clear All History` button. |

---

## 3. Complete REST API Reference

### 👥 Employees API
- `GET /api/employees` - Returns all employee roster records.
- `POST /api/employees` - Creates or updates an employee record.
  ```json
  {
    "id": "emp_1",
    "name": "Sachin",
    "email": "sachin@company.com",
    "location": "India",
    "timezone": "Asia/Kolkata",
    "workingDays": ["Mon","Tue","Wed","Thu","Fri","Sat"],
    "shiftId": "shift_standard",
    "teamId": "team_infra",
    "managerCc": "Ravi@company.com"
  }
  ```
- `DELETE /api/employees/<emp_id>` - Deletes employee by ID.

---

### ⏰ Shifts API
- `GET /api/shifts` - Returns all custom shift schedules.
- `POST /api/shifts` - Creates or updates a work shift.
  ```json
  {
    "id": "shift_standard",
    "name": "Standard Day Shift",
    "startTime": "10:00",
    "endTime": "19:00",
    "reminder1": "18:30",
    "reminder2": "18:45",
    "finalCall": "19:00"
  }
  ```
- `DELETE /api/shifts/<shift_id>` - Deletes a shift schedule.

---

### 💡 Thought of the Day (Quotes) API
- `GET /api/quotes` - Returns all motivational quotes.
- `POST /api/quotes` - Creates or updates a motivational quote.
  ```json
  {
    "id": "q_101",
    "quote": "Excellence is not an act, but a habit. What we build today lays the foundation for tomorrow.",
    "category": "Focus, Progress & Consistency"
  }
  ```
- `DELETE /api/quotes/<quote_id>` - Deletes a quote by ID.

---

### 📧 Email Templates API
- `GET /api/templates` - Returns all configured email templates.
- `POST /api/templates` - Updates template dictionary (`first_reminder`, `second_reminder`, `final_reminder`, `ignore_filled`).

---

### 📊 Analytics & Maintenance API
- `GET /api/chart-data` - Returns aggregated user, team, and time slot email delivery metrics for Chart.js dashboard charts.
- `POST /api/logs/delete` - Deletes daemon console logs older than specified period (`day`, `week`, `month`, `year`, `all`).
  ```json
  { "period": "week" }
  ```
- `POST /api/history/delete` - Deletes email dispatch audit history older than specified period (`day`, `week`, `month`, `year`, `all`).
- `POST /api/trigger-test` - Executes a manual test reminder check for a specific employee.
  ```json
  { "employeeName": "Sachin", "forceTime": "18:30", "dryRun": true }
  ```

---

## 4. Automated Daemon Engine & Reminder Workflow

```
[ Background Daemon Loop (15 Mins) ]
                 │
                 ▼
[ Iterate Staff Roster from SQLite DB ]
                 │
                 ▼
[ 1. Calculate Local Time (pytz IANA Timezone) ]
                 │
                 ▼
[ 2. Check Working Day Schedule ] ──(Off Day?)──► SKIP
                 │
                 ▼
[ 3. Match Local Time against Shift Reminders ] ──(No Match?)──► SKIP
                 │
                 ▼
[ 4. Fetch Latest Excel Sheet from SharePoint ]
                 │
                 ▼
[ 5. Verify Employee Cell for Today's Date ]
                 │
                 ├─► Filled? ────► Log COMPLETED & SKIP (No Email Sent)
                 │
                 └─► Blank? ─────► Generate Rich HTML Email & Dispatch via SMTP
```

---

## 5. Rich HTML Email & Quote Rotator

### 💡 Highlighted Thought of the Day Banner
Emails are rendered in rich HTML (`MIMEMultipart("alternative")`):
- **Yellow Highlight Banner**: `💡 THOUGHT OF THE DAY:` highlighted with yellow background.
- **Bold Motivational Quote**: Formatted prominently below the header.
- **Bold Courtesy Disclaimer**: Appends `Note: If you have already submitted your daily updates, please disregard this notice.` in bold text.

---

## 6. Docker & External Host Port Deployment Guide

### External Host Port Mapping (e.g., 5050:5000)
By default, the application container listens internally on port **5000**. If port 5000 is occupied on your host server by another application, you can map any external host port (e.g., `5050:5000`, `8080:5000`, `3000:5000`) using any of the following methods:

#### Method 1: Edit `docker-compose.yml` directly
You can open `docker-compose.yml` and change the `ports:` line to map your desired external port:
```yaml
    ports:
      - "5050:5000"
```
Then start the container:
```bash
docker compose up -d
```

#### Method 2: Via `.env` File (Recommended)
Edit the `.env` file in the project root directory:
```env
HOST_PORT=5050
```
Then run Docker Compose:
```bash
docker compose up -d
```

#### Method 3: Inline Environment Variable
```bash
# On Windows PowerShell
$env:HOST_PORT="5050"; docker compose up -d

# On Linux / macOS / Bash
HOST_PORT=5050 docker compose up -d
```

The application will now be accessible externally at: **`http://localhost:5050`** (or your server's IP `http://<SERVER_IP>:5050`).

### Persistent Data Volume
Database file is mounted at `./data:/app/data`, ensuring all roster updates, custom shifts, quote additions, and audit history remain safe across container restarts or updates.
