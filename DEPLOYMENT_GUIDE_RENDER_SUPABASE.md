# 🚀 Complete Deployment Guide: Render (UI Web Service) & Supabase (PostgreSQL Database)

This guideline provides step-by-step instructions for deploying the **TickTask - Daily Task Log Reminder System** to **Render** for hosting the web interface UI and **Supabase** for hosting the PostgreSQL database.

---

## 🏗️ Architecture & Dual Database Design

The application features an automatic **Dual Database Engine**:

- **Local Development Mode (Default)**: Uses local SQLite (`data/app_database.db`). No setup or environment variables required.
- **Cloud Production Mode (Render + Supabase)**: When the `DATABASE_URL` environment variable is detected, the app automatically connects to Supabase PostgreSQL, provisions all 12 tables, and seeds initial rosters, shifts, teams, templates, and quotes.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Web Browsers / Users                            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   │                                       │
                   ▼                                       ▼
    ┌──────────────────────────────┐       ┌──────────────────────────────┐
    │     LOCAL TESTING / DEV      │       │     RENDER CLOUD SERVICE     │
    │  (Local Flask / Docker Port) │       │ (Python Gunicorn Web Service)│
    └──────────────┬───────────────┘       └──────────────┬───────────────┘
                   │                                      │
                   ▼                                      ▼
    ┌──────────────────────────────┐       ┌──────────────────────────────┐
    │  Local SQLite Database File  │       │  Supabase PostgreSQL Cloud   │
    │   (data/app_database.db)     │       │    (Cloud Connection Pool)   │
    └──────────────────────────────┘       └──────────────────────────────┘
```

---

## 📋 Prerequisites

Before starting, ensure you have:
1. A **GitHub** account with this repository pushed to your account (`Daily-Task-Reminder-APP`).
2. A free account on **[Supabase](https://supabase.com)**.
3. A free account on **[Render](https://render.com)**.

---

## 1️⃣ Part 1: Setting Up Supabase (PostgreSQL Database)

### Step 1.1: Create a New Supabase Project
1. Log in to [Supabase](https://supabase.com) and click **"New Project"**.
2. Select your organization.
3. Fill in the project details:
   - **Name**: `daily-task-reminder-db` (or any name you prefer)
   - **Database Password**: Set a strong password (save this password in a secure place!).
   - **Region**: Choose the region closest to your users (e.g., `East US`, `South Asia / Mumbai`, `EU West`).
   - **Pricing Plan**: Free Tier.
4. Click **"Create new project"** and wait ~1 minute while Supabase provisions your PostgreSQL server.

### Step 1.2: Obtain Database Connection String (URI)
1. In your Supabase dashboard, click **Project Settings** (gear icon at the bottom-left sidebar).
2. Go to **Database** under the Configuration section.
3. Scroll down to **Connection String** and select the **URI** tab.
4. Copy the connection string format:
   ```text
   postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
5. Replace `[YOUR_PASSWORD]` with the actual database password you created in Step 1.1.

> 💡 **Tip**: If your database password contains special characters like `@`, `#`, `:`, or `/`, make sure to URL-encode them (e.g., `@` becomes `%40`).

---

## 2️⃣ Part 2: Setting Up Render (UI Web Service)

### Step 2.1: Create a New Render Web Service
1. Log in to [Render.com](https://render.com).
2. On your dashboard, click **"New +"** $\rightarrow$ **"Web Service"**.
3. Choose **"Build and deploy from a Git repository"** and connect your GitHub account.
4. Select your **Daily-Task-Reminder-APP** repository.

### Step 2.2: Configure Web Service Settings
Fill in the service details:

| Setting Field | Value to Enter |
| :--- | :--- |
| **Name** | `daily-task-reminder-app` |
| **Region** | Select closest region (e.g., Oregon, Frankfurt, Singapore) |
| **Branch** | `main` |
| **Root Directory** | *(Leave blank for root)* |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120` |
| **Instance Type** | Free |

### Step 2.3: Configure Environment Variables
Scroll down to the **Environment Variables** section and click **"Add Environment Variable"**:

1. **`DATABASE_URL`**: Paste your Supabase URI connection string from Part 1.
   ```text
   postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
2. **`SECRET_KEY`**: Type any random secret string (e.g. `super_secret_ticktask_key_2026`).
3. *(Optional)* **`PYTHON_VERSION`**: `3.11.0`

### Step 2.4: Deploy Web Service
1. Click **"Create Web Service"**.
2. Render will pull your repository, install all dependencies (`Flask`, `psycopg2-binary`, `gunicorn`, `openpyxl`, `reportlab`), and boot your web server.
3. Once deployment is complete, Render will display your live URL:
   `https://daily-task-reminder-app.onrender.com`

---

## 3️⃣ Part 3: Automatic Database Initialisation & Seeding

You do **NOT** need to run manual SQL migration scripts!

On the first application boot on Render:
1. `database.py` detects `DATABASE_URL`.
2. Connects to your Supabase PostgreSQL instance.
3. Automatically executes `CREATE TABLE IF NOT EXISTS` for all 12 core tables:
   - `users` (Admin, Manager, Employee authentication accounts)
   - `employees` (Staff roster)
   - `managers` (Managers directory)
   - `teams` (Workspaces & sheets mapping)
   - `shifts` (Shift timings & reminder slots)
   - `locations` (Country timezones)
   - `templates` (Email templates including Welcome Email)
   - `settings` (SMTP & policy configurations)
   - `quotes` (Thought of the Day quotes)
   - `task_logs` (Daily task submission entries)
   - `logs` (Daemon system logs)
   - `reminder_history` (Email reminder audit history)
4. Seeds default admin (`admin@company.com`), initial employee roster, default shifts, and templates.

---

## 4️⃣ Part 4: Default Admin Credentials & Testing

Once deployed on Render, log in to your application using the pre-seeded admin account:

| Role | Username / Email | Default Password | Access Level |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@company.com` | `admin123` | Full System Access, User Management, SMTP Config |
| **Manager** | `Ravi@d2backoffice.onmicrosoft.com` | `manager123` | Master Team Task Logs, Roster View, Export Reports |
| **Employee** | `sachin.k@d2backoffice.onmicrosoft.com` | `emp123` | Personal Worklog Submission, Calendar View, Profile |

> 🔒 **Security Note**: After logging in for the first time, click your profile card in the bottom-left sidebar and change your password.

---

## 5️⃣ Part 5: Environment Variables Reference Table

| Variable Name | Required? | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes (for Cloud)** | *(None - fallback SQLite)* | Supabase PostgreSQL URI connection string. |
| `SUPABASE_DB_URL` | Optional | *(None)* | Alternate key name for Supabase connection string. |
| `SECRET_KEY` | Recommended | `secret-key-12345` | Flask session encryption key. |
| `PORT` | Auto (Render) | `5000` | Port assigned by Render for Gunicorn web server. |
| `HOST_PORT` | Auto (Docker) | `5050` | Host port mapping for Docker local testing. |

---

## ❓ Part 6: Troubleshooting & Frequently Asked Questions (FAQ)

### Q1: Render log shows `psycopg2.OperationalError: connection to server at "db.xxx.supabase.co" ... port 5432 failed: Network is unreachable`
- **Root Cause**: You are using Supabase's **Direct Connection string** (`db.[REF].supabase.co:5432`). Supabase direct connections rely strictly on **IPv6**, whereas Render free instances do not support IPv6 outbound networking.
- **Solution**: Switch your `DATABASE_URL` in Render Environment Variables to your Supabase **Pooler Connection string** (which uses IPv4 over port 6543):
  1. In Supabase Dashboard, go to **Project Settings** $\rightarrow$ **Database**.
  2. Under **Connection String**, select **Pooler** (or Pooler URI).
  3. Copy the Pooler connection string (starts with `aws-0-[REGION].pooler.supabase.com:6543`).
  4. Paste this string into `DATABASE_URL` on Render and click Save.

### Q2: Render log shows `psycopg2.OperationalError: password authentication failed`
- **Cause**: Incorrect database password or special characters not URL-encoded in the connection URI.
- **Solution**: Check your Supabase database password. Ensure non-alphanumeric characters (like `@`, `#`, `:`, `/`) are URL-encoded (`@` $\rightarrow$ `%40`, `#` $\rightarrow$ `%23`).


### Q2: Will my local database be affected when I test locally?
- **No**. When running on your local machine or local Docker container without setting `DATABASE_URL`, the application automatically uses local SQLite (`data/app_database.db`). Local testing remains 100% isolated.

### Q3: Why does the first request on Render take 30 seconds?
- **Cause**: Render Free Tier Web Services automatically spin down to sleep after 15 minutes of inactivity.
- **Solution**: The first request wakes up the service (takes ~20-30s). Subsequent requests are instant. Upgrading to Render Starter tier keeps the service awake 24/7.

---

*Guideline generated for TickTask Daily Task Log Reminder System.*
