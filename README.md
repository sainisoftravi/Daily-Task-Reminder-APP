# Automated Daily Task/Work Log Reminder System

Complete production solution for automated daily task reminders across multiple timezones (India, UAE, Saudi Arabia) using **Microsoft 365 Excel Online**, **Office Scripts**, **Power Automate**, **Python**, and **Docker**.

---

## 1. Power Automate Flow Architecture

```
[ Recurrence Trigger (Every 15 Minutes) ]
                   │
                   ▼
[ Action 1: Get EmployeeConfig Table (Excel Online) ]
                   │
                   ▼
[ Action 2: Apply to Each Employee (Loop) ]
                   │
                   ├─► [ Step A: Calculate Local Time, Local Date, Local Day ]
                   │     • LocalTime = formatDateTime(convertFromUtc(utcNow(), TimeZone), 'HH:mm')
                   │     • LocalDay  = formatDateTime(convertFromUtc(utcNow(), TimeZone), 'ddd')
                   │     • LocalDate = formatDateTime(convertFromUtc(utcNow(), TimeZone), 'dd-MMM-yy')
                   │
                   ├─► [ Step B: Condition - Is Today a Working Day? ]
                   │     • Expression: contains(item()?['WorkingDays'], LocalDay)
                   │     • If FALSE ──► Skip Employee (Off Day)
                   │
                   ├─► [ Step C: Condition - Is Local Time 18:30 or 18:45? ]
                   │     • Expression: OR(equals(LocalTime, '18:30'), equals(LocalTime, '18:45'))
                   │     • If FALSE ──► Skip Employee
                   │
                   ├─► [ Step D: Run Office Script ]
                   │     • Script: "Daily Task Fill Reminder"
                   │     • Parameters: sheetName = item()?['SheetName'], targetDateStr = LocalDate
                   │
                   └─► [ Step E: Condition - Is Employee in missingEmployees? ]
                         • Expression: contains(outputs('Run_script')?['body/missingEmployees'], item()?['EmployeeName'])
                         • If FALSE ──► Do Nothing (Task Already Completed!)
                         • If TRUE  ──► Check Reminder Window:
                                          ├─► If 18:30 ──► Send 1st Reminder Email
                                          └─► If 18:45 ──► Send Final Reminder Email
```

---

## 2. Power Automate Action Configuration (In Order)

1. **Trigger: Recurrence**
   - **Interval**: `15`
   - **Frequency**: `Minute`

2. **Action 1: List rows present in a table** (Connector: Excel Online Business)
   - **Location**: `OneDrive for Business` or `SharePoint Site`
   - **Document Library**: `OneDrive` or `Documents`
   - **File**: `Daily Task and Update Sheet.xlsx`
   - **Table**: `EmployeeConfig`

3. **Action 2: Apply to each**
   - **Select an output from previous steps**: `@outputs('List_rows_present_in_a_table')?['body/value']`

4. **Inside Apply to Each - Action 3: Compose - LocalDay**
   - **Inputs**: `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'ddd')`

5. **Inside Apply to Each - Action 4: Compose - LocalTime**
   - **Inputs**: `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'HH:mm')`

6. **Inside Apply to Each - Action 5: Compose - LocalDate**
   - **Inputs**: `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'dd-MMM-yy')`

7. **Inside Apply to Each - Action 6: Condition - Check Working Day**
   - **Expression**: `@contains(item()?['WorkingDays'], outputs('Compose_-_LocalDay'))`

8. **Inside If Yes - Action 7: Condition - Check Reminder Time (18:30 or 18:45)**
   - **Expression**: `@or(equals(outputs('Compose_-_LocalTime'), '18:30'), equals(outputs('Compose_-_LocalTime'), '18:45'))`

9. **Inside If Yes - Action 8: Run script** (Connector: Excel Online Business)
   - **Location**: `SharePoint Site` / `OneDrive`
   - **File**: `Daily Task and Update Sheet.xlsx`
   - **Script**: `Daily Task Fill Reminder`
   - **sheetName**: `item()?['SheetName']`
   - **targetDateStr**: `outputs('Compose_-_LocalDate')`

10. **Inside If Yes - Action 9: Condition - Is Employee Missing**
    - **Expression**: `@contains(outputs('Run_script')?['body/missingEmployees'], item()?['EmployeeName'])`

11. **Inside If Yes - Action 10: Switch / Condition on LocalTime**
    - **If LocalTime equals '18:30'**:
      - **Action**: `Send an email (V2)`
      - **TO**: `item()?['Email']`
      - **CC**: `item()?['ManagerCC']`
      - **Subject**: `Daily Work Log Reminder - @{outputs('Compose_-_LocalDate')}`
      - **Body**: First Reminder Template
    - **If LocalTime equals '18:45'**:
      - **Action**: `Send an email (V2)`
      - **TO**: `item()?['Email']`
      - **CC**: `item()?['ManagerCC']`
      - **Subject**: `Final Reminder: Daily Work Log - @{outputs('Compose_-_LocalDate')}`
      - **Body**: Second Reminder Template

---

## 3. Power Automate WDL Expressions Reference

| Field | Power Automate WDL Expression |
| :--- | :--- |
| **Convert UTC to Local Timezone** | `convertFromUtc(utcNow(), item()?['TimeZone'])` |
| **Local Time Format (HH:mm)** | `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'HH:mm')` |
| **Local Day Format (ddd)** | `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'ddd')` |
| **Local Date Format (dd-MMM-yy)** | `formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'dd-MMM-yy')` |
| **Working Day Check** | `contains(item()?['WorkingDays'], formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'ddd'))` |
| **Reminder Window Check** | `@or(equals(formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'HH:mm'), '18:30'), equals(formatDateTime(convertFromUtc(utcNow(), item()?['TimeZone']), 'HH:mm'), '18:45'))` |

---

## 4. Email Templates

### First Reminder (18:30 Local Time)
- **Subject**: `Daily Work Log Reminder - [Date]`
- **Body**:
```text
Hello [EmployeeName],

This is a friendly reminder to please update your task details and working hours for today in the Daily Task and Update Sheet.

Please complete your daily work log before the end of your working day.

Thank you.

Regards,
IT Team
```

### Second/Final Reminder (18:45 Local Time)
- **Subject**: `Final Reminder: Daily Work Log - [Date]`
- **Body**:
```text
Hello [EmployeeName],

This is a final reminder to please complete today's task details and working hours in the Daily Task and Update Sheet.

Please update your work log before the end of your working day.

Thank you.

Regards,
IT Team
```

---

## 5. Preventing 6:45 PM Duplicate Reminder
Because the Office Script runs dynamically on every execution loop (both at 18:30 and 18:45 local time), it performs a live cell check on Excel. 

If an employee fills their task cell between 6:30 PM and 6:45 PM:
1. The Office Script inspects the row for today's date at 18:45.
2. The employee's cell now contains text.
3. The Office Script includes the employee in `completedEmployees` and excludes them from `missingEmployees`.
4. Power Automate checks `contains(missingEmployees, EmployeeName)` -> evaluates to `false`.
5. Email action is bypassed automatically!

---

## 6. Testing & Single Employee Test Mode

### Power Automate Test Mode
To test with one employee (e.g. `Sachin`):
Add a Filter condition inside the loop or a main condition:
`equals(item()?['EmployeeName'], 'Sachin')`

### Python Program Execution
Run the Python script for a single employee in test mode:
```bash
python daily_reminder.py --test-employee "Sachin" --force-time 18:30 --force-date 16-Sep-26
```

### Dry-Run Mode (Simulation without sending real emails)
```bash
python daily_reminder.py --dry-run --force-time 18:30
```

---

## 7. Python Configuration for Non-Admin Users (Email & Password)

If you do **not** have Azure AD Admin permissions, you can run the Python application using standard Office 365 user credentials (your email address and password) via SMTP authentication (`smtp.office365.com:587`).

### `config.json` Structure
```json
{
  "excel_file_path": "Daily Task and Update Sheet.xlsx",
  "employee_config_sheet": "EmployeeConfig",
  "table_name": "EmployeeConfig",
  "manager_cc_default": "Ravi@d2backoffice.onmicrosoft.com",
  "test_employee": null,
  "dry_run": false,
  "auth_mode": "smtp",
  "user_credentials": {
    "email": "Ravi@d2backoffice.onmicrosoft.com",
    "password": "YOUR_EMAIL_PASSWORD_HERE"
  },
  "smtp": {
    "enabled": true,
    "server": "smtp.office365.com",
    "port": 587
  }
}
```

> [!TIP]
> **Multi-Factor Authentication (MFA) Note**:
> If your Microsoft 365 account has 2FA/MFA enabled, generate an **App Password** from your Microsoft Account security settings (`https://mysignins.microsoft.com/security-info`) and place it in `"password"`.

---

## 8. Running with Docker & Docker Compose

### Option A: Standard Docker Build & Run
```bash
# Build Docker image
docker build -t daily-task-reminder .

# Run Docker container in background (checks every 15 mins)
docker run -d --name task_reminder_daemon daily-task-reminder
```

### Option B: Docker Compose
```bash
# Start container using Docker Compose
docker-compose up -d

# View real-time container logs
docker-compose logs -f
```

---

## 8. Verifying Email Delivery & Debugging

1. **Power Automate Run History**:
   - Navigate to **Power Automate -> Cloud Flows -> Daily Task Reminder -> Run History**.
   - Select a run timestamp.
   - Inspect the **Apply to each** loop for each employee.
   - Check the **Send an email (V2)** step badge (Green Checkmark = Success).

2. **Outlook Sent Items**:
   - Open Outlook / OWA for `Ravi@d2backoffice.onmicrosoft.com`.
   - Check **Sent Items** folder to confirm dispatch timestamp, recipient TO/CC addresses, and exact subject line.
