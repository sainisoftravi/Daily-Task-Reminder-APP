# 🚀 Automated Daily Task & Work Log Reminder System

A complete, enterprise-grade automated daily task reminder web application and daemon engine built with **Flask**, **SQLite Database**, **Chart.js Analytics**, **Python**, and **Docker**.

Supports multi-timezone staff roster management (**India, UAE, Saudi Arabia, USA, UK, Singapore**), customizable work shifts, team management, rich HTML email notifications with dynamic **Thought of the Day** quote rotation, courtesy ignore disclaimers, and automated Excel / SharePoint sheet verification.

---

## 📑 Table of Contents
1. [Default Application Credentials & Test Accounts](#1-default-application-credentials--test-accounts)
2. [Architecture & System Features](#2-architecture--system-features)
3. [Web Application Pages Sitemap](#3-web-application-pages-sitemap)
4. [Complete REST API Reference](#4-complete-rest-api-reference)
5. [Automated Daemon Engine & Reminder Workflow](#5-automated-daemon-engine--reminder-workflow)
6. [Rich HTML Email & Quote Rotator](#6-rich-html-email--quote-rotator)
7. [Docker Deployment Guide](#7-docker-deployment-guide)
8. [Prompt-by-Prompt Development & Optimization History](#8-prompt-by-prompt-development--optimization-history)

---

## 1. Default Application Credentials & Test Accounts

The system comes pre-seeded with multi-role test accounts for immediate testing across all application roles and workspace views:

| Role | Email Address | Password | Landing Page & Access Scope |
| :--- | :--- | :--- | :--- |
| 🛡️ **Admin** | `admin@company.com` | `admin123` | `/dashboard` (Full System Access, Roster, Shifts, SMTP, Audit Logs) |
| 👔 **Manager** | `manager@company.com` | `manager123` | `/dashboard` (Manager Access, Staff Roster, Shifts, Teams Management) |
| 👤 **Employee (Sachin)** | `sachin@company.com` | `emp123` | `/task-entry` (Personal Task Workspace & Work Log Submission) |
| 👤 **Employee (Amin)** | `amin@company.com` | `emp123` | `/task-entry` (Personal Task Workspace & Work Log Submission) |

---

## 2. Architecture & System Features

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
- **Embedded Brand Logo Header**: Displays the official TickTask brand logo inline (`<img src="data:image/png;base64,...">`) across all HTML emails.
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

---

## 8. Prompt-by-Prompt Development & Optimization History

Below is the complete prompt-by-prompt history of user requests, technical implementations, affected codebase files, and visual/functional outcomes across the application development lifecycle:

| # | User Request / Feature Prompt | Technical Problem & Architectural Solution | Modified Files & Components | Functional & Visual Outcome |
| :---: | :--- | :--- | :--- | :--- |
| **1** | *"this add new member page and other all page should be responsive and full view"* | **Issue**: Fixed table dimensions and overflow caused clipped elements on medium viewports.<br>**Solution**: Refactored grid systems, flex wrappers, and CSS viewports to support `100vh` fluid layouts with auto-scaling containers. | [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html), [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | "Add New Member" modal and all admin pages render in full view with fluid responsiveness across desktop, laptop, tablet, and mobile screens. |
| **2** | *"see this page its not coming properly on my page scroller is coming in sides"* | **Issue**: Outer body scrollbars appeared due to static CSS pixel heights and overflow conflicts.<br>**Solution**: Enforced `overflow: hidden` on viewport roots, set flex scroll containers for table bodies, and used `max-height: calc(100vh - header)`. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | Completely eliminated unwanted page-level side scrollbars across all screen sizes. |
| **3** | *"same issue coming in add new member page"* | **Issue**: Form modals overflowed screen height on smaller resolutions.<br>**Solution**: Converted modal bodies to auto-scrolling glassmorphism panels (`max-height: 90vh; overflow-y: auto`). | [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html) | Modals remain centered, fit within screen bounds, and allow clean internal scrolling on lower-resolution screens. |
| **4** | *"check all other pages all should be screen resolution responsive i don't want scrollbar whether i open this on mobile or laptop or desktop"* | **Issue**: Layout inconsistencies on `/shifts`, `/teams`, `/templates`, `/quotes`, `/settings`, and `/logs`.<br>**Solution**: Unified responsive breakpoints (`@media (max-width: 992px)` and `@media (max-width: 640px)`), dynamic mobile toggle sidebar drawer, and auto-collapsing data tables. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`templates/dashboard.html`](file:///e:/Daily-Update-Email/templates/dashboard.html), [`templates/logs.html`](file:///e:/Daily-Update-Email/templates/logs.html) | Seamless responsive UI across all 10 application pages with zero horizontal or body scrollbars on mobile, laptop, or desktop. |
| **5** | *"use this logo on login page like a logo"* | **Requirement**: Add brand logo image to login page header.<br>**Implementation**: Added high-resolution `app_logo.png` image asset to `/login` card header with flex alignment and glassmorphism backdrop. | [`templates/login.html`](file:///e:/Daily-Update-Email/templates/login.html), [`static/images/app_logo.png`](file:///e:/Daily-Update-Email/static/images/app_logo.png) | Professional branding on login screen matching TickTask design guidelines. |
| **6** | *"on logo this design is there remove this from the image"* | **Requirement**: Clean up background design noise and surrounding artifacts from logo graphic.<br>**Implementation**: Edited logo image assets to remove edge design artifacts, resulting in clean transparent/dark image variants (`app_logo.png` & `app_logo_dark.png`). | [`static/images/app_logo.png`](file:///e:/Daily-Update-Email/static/images/app_logo.png), [`static/images/app_logo_dark.png`](file:///e:/Daily-Update-Email/static/images/app_logo_dark.png) | Crisp, high-contrast logo images without visual noise or background artifacts. |
| **7** | *"after login logo is looking like this"* | **Requirement**: Standardize brand logo presentation in the sidebar header post-login.<br>**Implementation**: Added `#sidebar-brand-logo` image tag in layout header, styled max dimensions, and implemented dynamic theme logo swapping. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | Sidebar header displays sharp TickTask logo brand image across all logged-in pages. |
| **8** | *"on the give the option to change the theme of page like dark light"* | **Requirement**: Add user option to toggle between Dark and Light mode themes.<br>**Implementation**: Built CSS design tokens (`[data-theme="dark"]`, `[data-theme="light"]`), header toggle pill (`Dark` / `Light`), `localStorage` theme state persistence (`ticktask_theme`), and dynamic logo switcher. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | Instant, persistent Dark/Light theme switching across the entire application with one click. |
| **9** | *"theme concept is working but see the font color that should be visible on there themes"* | **Issue**: Contrast issues in Light Theme where white text was difficult to read on light panels.<br>**Solution**: Fine-tuned light theme CSS tokens (`--text-main`, `--text-muted`, `--card-bg`, `--th-color`, `--form-control-text`, `--link-color`) to ensure WCAG-compliant contrast ratios. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | Excellent text readability and visual contrast across all tables, forms, badges, and headers in both Light and Dark themes. |
| **10** | *"on this side icon when i m clicking continuously it is showing the admin page icon in the flash i think that is some bug"* | **Issue**: Client-side JS (`fetch('/api/me')`) queried user role post-load and hid unauthorized menu items, causing a visible rendering delay (flash) of admin icons.<br>**Solution**: Implemented Flask Server-Side Rendering (SSR) via Jinja context processors (`@app.context_processor`). Injected `current_user` & `current_role` into server context and wrapped sidebar items with `{% if current_role in [...] %}`. Synchronized `window.currentUser` inline and removed post-load DOM query selector latency. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) | 100% server-side role security. Zero flash of unauthorized admin links for Manager or Employee roles during rapid navigation. |
| **11** | *"this email is coming in the signature remove the manager email id and add the logo of website in email body"* | **Requirements**: 1. Remove manager email address from email signature.<br>2. Add website brand logo at the top of email bodies.<br>**Implementation**: Removed `{mgr_email}` from welcome email signature in `app.py`. Added base64 image converter (`get_logo_b64()`) and embedded logo header banner (`<img src="data:image/png;base64,...">`) into `generate_html_email()` in `daily_reminder.py`. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`daily_reminder.py`](file:///e:/Daily-Update-Email/daily_reminder.py) | All HTML emails (Welcome & 3-stage reminders) now feature the official TickTask brand logo at the header and a clean signature without raw email strings. |
| **12** | *"in the Readme file what changes we did with every prompt what changes happen all the things update in readme file"* | **Requirement**: Comprehensive documentation update reflecting all prompt history and architectural developments.<br>**Implementation**: Added full prompt-by-prompt development changelog, technical resolutions, affected file paths, and updated system sitemap. | [`README.md`](file:///e:/Daily-Update-Email/README.md) | Fully updated, professional `README.md` serving as an authoritative reference manual for administrators and developers. |
| **13** | *"Role Email Address Password Landing Page ... add this like sample for application use in Readme file"* | **Requirement**: Add sample application test accounts and credentials reference matrix.<br>**Implementation**: Created Section 1 ("Default Application Credentials & Test Accounts") with formatted table detailing Admin, Manager, and Employee test accounts, default passwords, and landing page access scopes. | [`README.md`](file:///e:/Daily-Update-Email/README.md) | Prominently displays pre-seeded demo user credentials for instant testing and evaluation by system administrators. |
