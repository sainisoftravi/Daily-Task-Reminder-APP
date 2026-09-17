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
| `/settings` | **System Settings & Policy Controls** | Configure **Employee Back-Date Task Logging Policy** (`max_backdate_days`), **Default System SMTP** & **Manager-Specific SMTP Accounts** with **Fernet AES Encryption**, SharePoint direct link, and local Excel path. |
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
| **14** | *"d2backoffice.onmicrosoft.com remove this form the readme file becauseof security concern"* | **Requirement**: Sanitize domain names in `README.md` to remove proprietary domain strings for security.<br>**Implementation**: Replaced all proprietary `d2backoffice.onmicrosoft.com` domain references in default test credentials with sanitized `company.com` placeholders (`manager@company.com`, `sachin@company.com`, `amin@company.com`). | [`README.md`](file:///e:/Daily-Update-Email/README.md) | Sanitized documentation preventing disclosure of internal organizational domains. |
| **15** | *"in this here one issue when i m refresh the page some time showing half naame some time full name"* | **Issue**: Race condition on `/employees` roster table where `fetchEmployees()` rendered before asynchronous `fetchManagers()` completed, causing manager display names to fall back to username string ("Ravi") instead of full manager name ("Ravi Saini").<br>**Solution**: Updated `loadData()` & `fetchManagers()` in `templates/employees.html` to re-trigger `renderEmployeesTable()` once manager dataset resolves and added secondary fallback check against `employeesData`. | [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html) | Manager CC column consistently renders full display names (e.g. "Ravi Saini") across all page refreshes with zero race conditions. |
| **16** | *"in the light theme role is not visble"* | **Issue**: Role, Team, Location, and Shift badges used light text colors (`#93c5fd`, `#e9d5ff`, `#fca5a5`, `#fbbf24`) with inline styles, rendering badge text unreadable against light backgrounds in Light Theme.<br>**Solution**: Added dedicated CSS badge classes (`.badge-role-employee`, `.badge-role-manager`, `.badge-role-admin`) and high-contrast light theme text overrides (`[data-theme="light"]`) in `templates/layout.html`. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html) | Role badges (Employee, Manager, Admin), Team badges, and Location badges render with crisp, bold, high-contrast text across both Light and Dark themes. |
| **17** | *"same issue on this dashboard text is not visible"* | **Issue**: Main portal title, mode switcher container, select dropdowns, metric cards, table row details snippet, and modal inputs in `task_entry.html` and `employees.html` used hardcoded white gradients (`-webkit-text-fill-color: transparent`), hardcoded white text (`#f8fafc`, `#e2e8f0`), and dark input backgrounds (`#0f172a`), causing text to become invisible on light backgrounds in Light Theme.<br>**Solution**: Replaced hardcoded text fill gradients and white text inline styles with dynamic CSS design tokens (`color: var(--text-main);`, `color: var(--link-color);`, `background-color: var(--form-control-bg);`, `color: var(--form-control-text);`, `background: var(--btn-sec-bg);`). Updated modal header titles and read-only input styles. | [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html), [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Page header titles, mode switcher controls, task details summaries, staff roster names, and form modal inputs are 100% legible with crisp WCAG-compliant contrast ratios across both Light and Dark themes. |
| **18** | *"in this give the option to download the task fill report user wise date and time wise like this Top it will SHow teh Team Namewith month or day or week or year automatcaly ... report i can download in xslx,and pdf both"* | **Requirement**: Enable exporting user-wise, date-wise matrix task fill reports in both XLSX and PDF formats, with top banner showing Team Name, time period, and team locations (e.g. `Technical Infra Team - Sept 2026 (India, UAE, Saudi)`).<br>**Implementation**: 1. Created [`report_generator.py`](file:///e:/Daily-Update-Email/report_generator.py) module utilizing `openpyxl` for Excel spreadsheets and `reportlab` for PDF document creation.<br>2. Built `/api/export/task-report` endpoint in [`app.py`](file:///e:/Daily-Update-Email/app.py) supporting `format=xlsx` & `format=pdf` query parameters.<br>3. Added **"📥 Export XLSX"** and **"📄 Export PDF"** download buttons to both Employee Personal View and Admin Master View toolbars in [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html). | [`report_generator.py`](file:///e:/Daily-Update-Email/report_generator.py), [`app.py`](file:///e:/Daily-Update-Email/app.py), [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html), [`requirements.txt`](file:///e:/Daily-Update-Email/requirements.txt), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Administrators and employees can export formatted task fill matrix reports in Excel (.xlsx) and PDF (.pdf) with 1-click download from the web interface. |
| **19** | *"in this when user downloading his compllete report month day or week wise in that at the top it should be show who downlaod thsi report his full name shu=ould be comes"* | **Requirement**: Display the full name of the logged-in user who downloaded the report at the top of both XLSX and PDF exports.<br>**Implementation**: 1. Extracted `user.get("name")` from session in `/api/export/task-report` in [`app.py`](file:///e:/Daily-Update-Email/app.py).<br>2. Updated [`report_generator.py`](file:///e:/Daily-Update-Email/report_generator.py) to render a sub-header banner line (`Downloaded By: [Full Name] | Generated On: [Timestamp]`) directly under the main title header in both Excel and PDF documents. | [`report_generator.py`](file:///e:/Daily-Update-Email/report_generator.py), [`app.py`](file:///e:/Daily-Update-Email/app.py), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Every exported task report (XLSX and PDF) displays the full name of the downloader and generation timestamp prominently in the top header. |
| **20** | *"in this we need to design Proper Page for User Manageangment as of now we have a option to add employee this is good isteady of this make a USER Page on there we will create all user employee ,admin,manager after creation we will align give teh permission of Empployee ,manager,admin while creating user same process but with one panel as of now we have manaeg page different and epmployee page different both user we will create from user managment page"* | **Requirement**: Unify Employee Roster and Managers Directory into a single **User Management** panel (`/users`) for creating, configuring, and managing all user account roles (Employees 👤, Managers 👔, Admins 🛡️) with aligned access permissions in one central creation panel.<br>**Implementation**: 1. Created `/users` page route in [`app.py`](file:///e:/Daily-Update-Email/app.py) and consolidated sidebar navigation in [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html).<br>2. Redesigned [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html) into a unified User Management dashboard featuring Role Filter Pills (`All Roles`, `Admins`, `Managers`, `Employees`), single-panel creation modal, dynamic role-specific permission badges, and multi-role user roster management. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Administrators and managers can create and manage all Employees, Managers, and Admins from a single unified User Management panel with role-aligned permissions. |
| **21** | *"this is submit work log Page in that i have open a sachin account in edit he can see all the employee and he is able to update the other employee task logs this is wrong in this employee only able to fill only his own task he cannot see other oser tasks and not able to update there task"* | **Issue**: Users with the `employee` role could see other employees in modal dropdowns and open/edit task logs belonging to other team members on `/task-entry`.<br>**Solution**: 1. Frontend ([`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html)): Locked and disabled `#task-emp-select` modal dropdown for `employee` role users, prevented opening edit modals for other employees' logs, and restricted quick-fill actions to the logged-in user.<br>2. Backend ([`app.py`](file:///e:/Daily-Update-Email/app.py) & [`database.py`](file:///e:/Daily-Update-Email/database.py)): Enforced role security in `/api/task-logs` GET (only returns employee's own logs), POST (rejects spoofed submissions with HTTP 403 Forbidden), and DELETE endpoints. Locked report export filters for employee roles. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`database.py`](file:///e:/Daily-Update-Email/database.py), [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Employee accounts are strictly isolated to their own task logs. Employees cannot view, select, or edit tasks belonging to other staff members, while Managers and Admins maintain full administrative view and edit controls. |
| **22** | *"remove this profile, and employee portal and showing his country and team instald of make a section of profile in at his name is showing show his complet profile there and also put the change password function in taht profile section"* | **Requirements**: 1. Remove redundant `SELECT PROFILE:` dropdown bar and redundant `Employee Portal` mode tab from `/task-entry`.<br>2. Build complete user profile card in bottom-left sidebar displaying Full Name, Role badge, Email, Team Workspace, and Location.<br>3. Combine My Profile details and Password Change form into a unified **"My Profile & Account Security"** modal (`openUserProfileModal()`).<br>**Implementation**: 1. Updated [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html) to remove profile select bar and restrict mode tabs to Admin/Manager roles.<br>2. Updated [`app.py`](file:///e:/Daily-Update-Email/app.py) context processor and `/api/me` route to enrich logged-in user profile with team, location, timezone, and shift metadata.<br>3. Redesigned sidebar user card and upgraded modal in [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html). | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Redundant profile select dropdowns and mode tabs removed from task entry page. User profile metadata (Name, Role, Email, Team, Location) is displayed in the bottom-left sidebar, and clicking the profile card opens a unified My Profile & Password management modal. |
| **23** | *"in this page we are submiting worklog in that we have a calender ... if user want to see his back date logs what he filled taht should be comes ... make a condtion in that admin or manager can fill teh number of days allow to fill there logs at the employee end what happend if suppose admin or manager set only 2 days back logs he can fill teh other date will be disable in calender"* | **Requirement**: 1. Enable dynamic task log pre-fill lookup on date change in the submission/edit modal so employees can view and edit past logs.<br>2. Add a system-wide configurable back-date logging window setting (`max_backdate_days`, e.g. 2 days).<br>3. Enforce calendar limits (`min` date attribute) on the employee date picker, disabling older dates in the calendar, and block API submissions older than the configured limit.<br>**Implementation**: 1. Added **Employee Task Logging & Back-Date Restrictions** policy panel in [`templates/settings.html`](file:///e:/Daily-Update-Email/templates/settings.html).<br>2. Updated [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html) modal date picker handler (`onTaskDateChange`) to dynamically fetch past logs for selected dates and set `min`/`max` calendar bounds for employee role accounts.<br>3. Updated [`app.py`](file:///e:/Daily-Update-Email/app.py) to validate `date_str >= cutoff_date` for employee role submissions, returning HTTP 403 on violations. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`templates/settings.html`](file:///e:/Daily-Update-Email/templates/settings.html), [`templates/task_entry.html`](file:///e:/Daily-Update-Email/templates/task_entry.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Employees can seamlessly view/edit back-date task logs by changing the modal calendar date within administrator policy limits. Dates prior to the allowed back-date window (e.g. 2 days) are greyed out/disabled in the employee calendar and protected at the backend API boundary. |
| **24** | *"i think it should be comes left side and here you create a page of Settings"* | **Requirement**: 1. Rename sidebar menu navigation item to **Settings** (`<i class="fa-solid fa-gear"></i> Settings` -> `/settings`) on the left navigation bar.<br>2. Restructure the `/settings` page so that **Employee Back-Date Task Logging Policy** is positioned prominently as Section 1 at the top of the page.<br>**Implementation**: 1. Updated left sidebar navigation in [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) to link `/settings` under the name **Settings**.<br>2. Restructured [`templates/settings.html`](file:///e:/Daily-Update-Email/templates/settings.html) layout into **System Settings & Policy Controls** featuring Section 1: Employee Back-Date Task Logging Policy, Section 2: Manager & System SMTP Accounts, and Section 3: SharePoint Integration. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`templates/settings.html`](file:///e:/Daily-Update-Email/templates/settings.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Left sidebar menu displays **Settings** link. Accessing `/settings` presents a dedicated System Settings page with the Employee Back-Date Task Logging Policy displayed at the top. |
| **25** | *"here make a Setting option with settings icon ,in that if i click on that in drop down it will show you email Templates,Thoughtof teh day,Team Managment,Shift Creation,,Location Managment ,Daemons Logs & Audit Page when i will click on settings in another image i have given the idea because left side so many things is showings"* | **Requirement**: Consolidate left sidebar navigation by grouping all system administration modules into an interactive collapsible **Settings** accordion menu (`<i class="fa-solid fa-gear"></i> Settings`).<br>**Implementation**: 1. Updated [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html) CSS with `.nav-dropdown`, `.nav-dropdown-header`, `.chevron-icon`, and `.nav-submenu` styles.<br>2. Grouped System SMTP & Policy Config (`/settings`), Shifts Creation (`/shifts`), Teams Management (`/teams`), Locations Management (`/locations`), Email Templates (`/templates`), Thought of the Day (`/quotes`), and Daemon Logs & Audit (`/logs`) inside the Settings collapsible accordion dropdown.<br>3. Added automatic state detection (`is_settings_active`) so the Settings menu auto-expands and highlights active sub-items when navigating configuration pages. | [`templates/layout.html`](file:///e:/Daily-Update-Email/templates/layout.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Left sidebar menu is neat, clutter-free, and organized. Clicking **Settings** expands a smooth accordion menu revealing all system configuration modules, with auto-expansion when visiting any settings page. |
| **26** | *"in this we have a option of set email template of reminder of slots i want a option in that i can set or change teh welcome email settings template"* | **Requirement**: Add configurable Welcome Email Onboarding Template (`welcome_email`) option to the Email Templates management panel (`/templates`).<br>**Implementation**: 1. Added `welcome_email` template definition to [`data/templates.json`](file:///e:/Daily-Update-Email/data/templates.json) and seed logic in [`database.py`](file:///e:/Daily-Update-Email/database.py).<br>2. Added **"Welcome Email - New User Account Onboarding Template"** option to `#template-select` dropdown and live HTML preview in [`templates/templates.html`](file:///e:/Daily-Update-Email/templates/templates.html).<br>3. Updated [`app.py`](file:///e:/Daily-Update-Email/app.py) user creation handler to dynamically fetch the custom `welcome_email` template from database and perform variable substitution (`{name}`, `{email}`, `{role}`, `{password}`, `{portal_url}`, `{mgr_email}`, `{date}`). | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`database.py`](file:///e:/Daily-Update-Email/database.py), [`data/templates.json`](file:///e:/Daily-Update-Email/data/templates.json), [`templates/templates.html`](file:///e:/Daily-Update-Email/templates/templates.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Administrators can view, edit, preview, and save custom Welcome Email onboarding templates with real-time live preview on `/templates`. Newly created accounts automatically receive personalized welcome emails matching the configured template. |
| **27** | *"in welcome mail i got this email ,earlier i was sending the Credentilas of the account also"* | **Requirement**: Restore full account login credentials breakdown (`Portal Login URL`, `Assigned Role`, `Username (Email)`, `Password`, `Manager CC`) in the Welcome Email template.<br>**Implementation**: 1. Updated `welcome_email` in [`data/templates.json`](file:///e:/Daily-Update-Email/data/templates.json), [`database.py`](file:///e:/Daily-Update-Email/database.py), and [`app.py`](file:///e:/Daily-Update-Email/app.py) default fallback.<br>2. Updated live HTML preview in [`templates/templates.html`](file:///e:/Daily-Update-Email/templates/templates.html) to substitute `{name}`, `{email}`, `{password}`, `{portal_url}`, `{role}`, and `{mgr_email}`. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`database.py`](file:///e:/Daily-Update-Email/database.py), [`data/templates.json`](file:///e:/Daily-Update-Email/data/templates.json), [`templates/templates.html`](file:///e:/Daily-Update-Email/templates/templates.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Welcome emails include full login credentials (URL, Role, Username, Password) formatted cleanly for newly created users. |
| **28** | *"in this make a function when a admin or manager create a new Emplyee ... 12 length password with upper,lower,number case ... valide for 4 hours ... password show hide eye toggle ... request for resend password"* | **Requirement**: 1. Implement automatic **12-character random password generator** (Uppercase, Lowercase, Digits) for user creation and password reset requests.<br>2. Enforce **4-hour initial password expiration** (`pwd_expires_at`) with clear email security warnings.<br>3. Enforce **mandatory first-time password setup** (`must_change_password`) upon logging in with a temporary password.<br>4. Add **show/hide password eye toggle icon** (`<i class="fa-solid fa-eye"></i>`) to login fields.<br>5. Add **"Forgot or Expired Password? Request New Password"** modal on `/login` to trigger `/api/request-password-reset`.<br>**Implementation**: 1. Created `generate_random_password(12)` and schema columns (`must_change_password`, `pwd_expires_at`) in [`database.py`](file:///e:/Daily-Update-Email/database.py).<br>2. Built `/api/request-password-reset` and `/api/force-change-password` routes in [`app.py`](file:///e:/Daily-Update-Email/app.py).<br>3. Updated [`templates/login.html`](file:///e:/Daily-Update-Email/templates/login.html) with password eye toggles, password reset request modal, and mandatory first-time password setup modal. | [`app.py`](file:///e:/Daily-Update-Email/app.py), [`database.py`](file:///e:/Daily-Update-Email/database.py), [`templates/login.html`](file:///e:/Daily-Update-Email/templates/login.html), [`templates/employees.html`](file:///e:/Daily-Update-Email/templates/employees.html), [`README.md`](file:///e:/Daily-Update-Email/README.md) | Newly created accounts receive a 12-char random password valid for 4 hours. Users can toggle password visibility on login, request password reset emails if expired, and must set a new permanent password on first login. |





