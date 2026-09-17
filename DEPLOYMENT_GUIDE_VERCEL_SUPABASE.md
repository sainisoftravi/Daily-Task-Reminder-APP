# 🚀 Complete Deployment Guide: Vercel (UI Serverless) & Supabase (PostgreSQL Database)

This guideline provides step-by-step instructions for deploying the **TickTask - Daily Task Log Reminder System** to **Vercel** for hosting the web interface UI on a 24/7 instant serverless infrastructure and **Supabase** for hosting the PostgreSQL database.

---

## ⚡ Why Deploy on Vercel?

1. **Zero Sleep / Spin-Down Delay**: Unlike Render Free Tier (which goes to sleep after 15 minutes of inactivity), **Vercel Serverless Functions stay active 24/7** with instant responses (<1 second).
2. **Global Edge Network**: Ultra-fast content delivery across global locations.
3. **Automatic Continuous Deployment**: Automatically deploys new commits from your GitHub repository `main` branch.

---

## 🏗️ Architecture & Dual Database Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Web Browsers / Users                            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   │                                       │
                   ▼                                       ▼
    ┌──────────────────────────────┐       ┌──────────────────────────────┐
    │     LOCAL TESTING / DEV      │       │   VERCEL SERVERLESS APP      │
    │  (Local Flask / Docker Port) │       │   (Python @vercel/python)    │
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

1. A **GitHub** account with this repository pushed (`Daily-Task-Reminder-APP`).
2. A free account on **[Vercel](https://vercel.com)**.
3. A free account on **[Supabase](https://supabase.com)** with your PostgreSQL URI.

---

## 1️⃣ Part 1: Setting Up Vercel (Step-by-Step)

### Step 1.1: Import Project to Vercel
1. Log in to [Vercel.com](https://vercel.com).
2. On your Overview dashboard, click **"Add New..."** $\rightarrow$ **"Project"**.
3. Select your GitHub repository: **`sainisoftravi/Daily-Task-Reminder-APP`**.
4. Click **"Import"**.

### Step 1.2: Configure Project Settings & Custom Subdomain
- **Project Name**: Change from `Daily-Task-Reminder-APP` to **`ticktask`** *(This sets your domain to `https://ticktask.vercel.app`!)*
- **Framework Preset**: Leave as `Other` (Vercel automatically detects `vercel.json`).
- **Root Directory**: `./` (default).
- **Build Command**: *(Leave default)*.
- **Output Directory**: *(Leave default)*.


### Step 1.3: Configure Environment Variables
You only need to add **2 required environment variables**:

| Key Name | Requirement | Example / Value |
| :--- | :---: | :--- |
| **`DATABASE_URL`** | **REQUIRED** | `postgresql://postgres.rwyinoptbjudttxnvrzi:%7D%29ByRWy@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres` |
| **`SECRET_KEY`** | **REQUIRED** | `ticktask-super-secret-key-2026` |
| **`SMTP_SERVER`** | *(Optional)* | *(Only if overriding database SMTP settings)* |
| **`SMTP_PORT`** | *(Optional)* | *(Only if overriding database SMTP settings)* |
| **`SMTP_USERNAME`** | *(Optional)* | *(Only if overriding database SMTP settings)* |
| **`SMTP_PASSWORD`** | *(Optional)* | *(Only if overriding database SMTP settings)* |

> 💡 **Note**: Because your SMTP accounts, templates, shifts, and rosters are **already stored inside your Supabase database**, Vercel will automatically load your SMTP settings from Supabase upon connection! You do NOT need to enter SMTP environment variables unless you wish to override them.


### Step 1.4: Deploy
1. Click **"Deploy"**.
2. Vercel will install dependencies, build your Python Flask serverless application, and issue your live URL (e.g., `https://daily-task-reminder-app.vercel.app`).

---

## 2️⃣ Part 2: Fix for Default SMTP Password Issue

### 🔐 Why did SMTP passwords require re-entering on past deployments?
In previous releases, encryption keys were generated randomly in a local file (`data/app_secret.key`). On cloud platforms with non-persistent disks (like Vercel or fresh Render deployments), the key file was recreated on every deployment, causing existing encrypted passwords in the database to become un-decryptable (`[DECRYPT ERROR]`).

### ✅ Solution Applied:
1. **Deterministic Master Key**: Encryption keys are now derived deterministically from the `SECRET_KEY` environment variable using SHA-256. The encryption key **never changes across deployments or serverless invocations**.
2. **Environment Variable Fallback**: Setting `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, and `SMTP_PASSWORD` in Vercel Environment Variables ensures default SMTP credentials are always populated and authenticated automatically on first launch!

---

## 3️⃣ Part 3: Verification & Default Credentials

Once deployed on Vercel, log in using the pre-seeded admin credentials:

| Role | Username / Email | Default Password | Access Level |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@company.com` | `admin123` | Full Access, User Management, SMTP Config |
| **Manager** | `Ravi@d2backoffice.onmicrosoft.com` | `manager123` | Master Team Task Logs, Roster View, Export Reports |
| **Employee** | `sachin.k@d2backoffice.onmicrosoft.com` | `emp123` | Personal Worklog Submission, Calendar View, Profile |

---

## ❓ Troubleshooting (FAQ)

### Q1: Vercel displays `Function Timeout`
- **Cause**: Vercel Serverless Functions have a default 10-second timeout limit on Hobby plans.
- **Solution**: The application uses optimized database connections and connection pooling via Supabase port `6543`. Ensure your `DATABASE_URL` uses port `6543`.

### Q2: How do I switch back to local testing?
- **Local machine / Docker**: When running locally without setting `DATABASE_URL`, the application automatically uses local SQLite (`data/app_database.db`).

---

*Guideline generated for TickTask Daily Task Log Reminder System.*
