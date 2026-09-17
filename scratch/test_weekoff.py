import sys
import os
import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import report_generator

def test_weekoff():
    print("Testing Week Off Logic...")
    
    # Check is_employee_week_off for standard Mon-Fri employee
    # Sept 18, 2026 = Friday (Working Day)
    # Sept 19, 2026 = Saturday (Week Off)
    # Sept 20, 2026 = Sunday (Week Off)
    # Sept 21, 2026 = Monday (Working Day)
    
    fri_off = database.is_employee_week_off("test_emp", "2026-09-18")
    sat_off = database.is_employee_week_off("test_emp", "2026-09-19")
    sun_off = database.is_employee_week_off("test_emp", "2026-09-20")
    mon_off = database.is_employee_week_off("test_emp", "2026-09-21")
    
    print(f"2026-09-18 (Friday):   is_week_off = {fri_off} (Expected: False)")
    print(f"2026-09-19 (Saturday): is_week_off = {sat_off} (Expected: True)")
    print(f"2026-09-20 (Sunday):   is_week_off = {sun_off} (Expected: True)")
    print(f"2026-09-21 (Monday):   is_week_off = {mon_off} (Expected: False)")
    
    assert fri_off == False
    assert sat_off == True
    assert sun_off == True
    assert mon_off == False
    
    # Test Report Generation with Week Off cells
    dates_list = ["2026-09-18", "2026-09-19", "2026-09-20", "2026-09-21"]
    employees_list = [{"name": "Ravi Saini", "email": "sainisoftravi@gmail.com"}]
    logs_map = {
        ("2026-09-18", "ravi saini"): "ON LEAVE",
        ("2026-09-19", "ravi saini"): "WEEK OFF",
        ("2026-09-20", "ravi saini"): "WEEK OFF",
        ("2026-09-21", "ravi saini"): "ON LEAVE"
    }
    
    xlsx_bytes = report_generator.generate_xlsx_report("Infra Team", "18-21 Sep 2026", "UAE", dates_list, employees_list, logs_map, "Admin User")
    pdf_bytes = report_generator.generate_pdf_report("Infra Team", "18-21 Sep 2026", "UAE", dates_list, employees_list, logs_map, "Admin User")
    
    print(f"Generated XLSX Report: {len(xlsx_bytes)} bytes")
    print(f"Generated PDF Report:  {len(pdf_bytes)} bytes")
    assert len(xlsx_bytes) > 1000
    assert len(pdf_bytes) > 1000
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_weekoff()
