#!/usr/bin/env python3
"""
Integration Test Suite for Leave Features (Bulk Delete & Email Acknowledgement)
Runs inside Docker container.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database

def run_tests():
    print("==================================================")
    print("🚀 RUNNING LEAVE FEATURES DOCKER TEST SUITE")
    print("==================================================")

    client = app.test_client()

    # Log in as Admin / Sachin
    with client.session_transaction() as sess:
        sess['user'] = {
            'id': 'u_sachin',
            'name': 'Sachin',
            'email': 'sachin@d2backoffice.onmicrosoft.com',
            'role': 'admin',
            'teamName': 'Infra Team'
        }

    print("\n[STEP 1] Testing Multi-Day Bulk Leave Submission & Email Ack Trigger...")
    bulk_payload = {
        "employeeName": "Sachin",
        "email": "sachin@d2backoffice.onmicrosoft.com",
        "teamName": "Infra Team",
        "teamId": "team_infra",
        "startDate": "2026-10-10",
        "endDate": "2026-10-14",
        "leaveNote": "Medical Leave Test Batch",
        "skipWeekends": True
    }

    res = client.post('/api/task-logs/bulk-leave', json=bulk_payload)
    print(f"Bulk Leave status: {res.status_code}, data: {res.get_json()}")
    assert res.status_code == 200, "Bulk leave API failed"
    data = res.get_json()
    assert data.get("success") == True, "Bulk leave success flag not True"
    print("✓ Multi-Day Bulk Leave applied successfully!")

    print("\n[STEP 2] Fetching Created Leave Logs...")
    res_logs = client.get('/api/task-logs')
    assert res_logs.status_code == 200, "Fetch task logs failed"
    logs = res_logs.get_json().get("logs", [])
    oct_logs = [l for l in logs if (l.get("date_str") or l.get("dateStr", "")).startswith("2026-10-1")]
    print(f"Created {len(oct_logs)} October leave log entries.")
    assert len(oct_logs) >= 3, "Expected at least 3 October leave entries"
    target_ids = [l["id"] for l in oct_logs]

    print(f"\n[STEP 3] Testing Bulk Delete API with IDs: {target_ids}...")
    del_res = client.post('/api/task-logs/bulk-delete', json={"log_ids": target_ids})
    print(f"Bulk Delete status: {del_res.status_code}, data: {del_res.get_json()}")
    assert del_res.status_code == 200, "Bulk delete API failed"
    del_data = del_res.get_json()
    assert del_data.get("success") == True, "Bulk delete success flag not True"
    assert del_data.get("deleted_count") == len(target_ids), f"Expected deleted_count {len(target_ids)}, got {del_data.get('deleted_count')}"
    print(f"✓ Bulk Delete successfully removed {del_data.get('deleted_count')} leave records in one operation!")

    print("\n[STEP 4] Verifying Deletion in DB...")
    res_logs_after = client.get('/api/task-logs')
    logs_after = res_logs_after.get_json().get("logs", [])
    remaining = [l for l in logs_after if l["id"] in target_ids]
    print(f"Remaining deleted IDs count: {len(remaining)}")
    assert len(remaining) == 0, "Deleted logs still present in database"
    print("✓ DB verification confirmed 0 remaining deleted logs!")

    print("\n[STEP 5] Testing Employee Manager CC Lookup...")
    mgr_cc = database.get_employee_manager_cc("sachin@d2backoffice.onmicrosoft.com")
    print(f"Manager CC for Sachin: {mgr_cc}")
    assert mgr_cc != "", "Manager CC should not be empty"
    print("✓ Employee Manager CC lookup verified!")

    print("\n==================================================")
    print("🎉 ALL LEAVE FEATURE TESTS PASSED IN DOCKER!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
