#!/usr/bin/env python3
"""
Automated Integration & Performance Test Suite for Docker
Tests bulk leave batching, employee name sanitization, and DB operations.
"""

import sys
import os
import time
import datetime

# Ensure app path is loaded
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database

def run_all_tests():
    print("==================================================")
    print("🚀 RUNNING DOCKER AUTOMATED TEST SUITE")
    print("==================================================")
    
    # 1. Test Database Initialization & Cleanup
    print("\n[STEP 1] Testing Database Initialization & Migration...")
    database.init_db()
    print("  ✓ Database initialized successfully.")

    # 2. Test Employee Working Days Lookup
    print("\n[STEP 2] Testing Working Days Schedule Lookup...")
    wd = database.get_employee_working_days("Sachin (Infra Team)")
    print(f"  ✓ Working Days for Sachin: {wd}")
    assert isinstance(wd, list) and len(wd) > 0, "Failed to retrieve working days"

    # 3. Test Bulk Leave Batch Performance (17 days)
    print("\n[STEP 3] Testing Bulk Leave Batch Performance (17 days)...")
    emp_name = "Sachin (Infra Team)"
    email = "sachin@d2backoffice.onmicrosoft.com"
    team_name = "Infra Team"
    team_id = "team_infra"
    start_date = "2026-09-01"
    end_date = "2026-09-17"

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    t0 = time.time()
    payloads = []
    count_leave = 0
    count_wo = 0
    curr = start_dt

    while curr <= end_dt:
        dt_str = curr.strftime("%Y-%m-%d")
        is_wo = database.is_date_week_off(curr, wd)
        if is_wo:
            payloads.append({
                "employeeName": emp_name,
                "email": email,
                "teamName": team_name,
                "teamId": team_id,
                "dateStr": dt_str,
                "taskDetails": "WEEK OFF",
                "isLeave": False,
                "workStatus": "Week Off"
            })
            count_wo += 1
        else:
            payloads.append({
                "employeeName": emp_name,
                "email": email,
                "teamName": team_name,
                "teamId": team_id,
                "dateStr": dt_str,
                "taskDetails": "ON LEAVE",
                "isLeave": True,
                "workStatus": "Leave"
            })
            count_leave += 1
        curr += datetime.timedelta(days=1)

    database.save_task_logs_batch(payloads)
    elapsed = time.time() - t0
    print(f"  ✓ Bulk leave batch completed in {elapsed:.4f} seconds ({count_leave} Leave, {count_wo} Week Off).")
    assert elapsed < 1.0, f"Batch performance took too long: {elapsed}s"

    # 4. Test Employee Name Sanitization in Database
    print("\n[STEP 4] Verifying Employee Name Sanitization in DB...")
    logs = database.get_task_logs(start_date=start_date, end_date=end_date)
    dirty_logs = [l for l in logs if " (" in l.get("employee_name", "")]
    print(f"  ✓ Total retrieved logs: {len(logs)} | Unsanitized logs: {len(dirty_logs)}")
    assert len(dirty_logs) == 0, f"Found {len(dirty_logs)} unsanitized log entries with parenthetical team names"

    print("\n==================================================")
    print("✅ ALL DOCKER AUTOMATED TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
