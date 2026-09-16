import requests

BASE_URL = "http://localhost:5050"

def check_role_nav(email, password, role_label):
    session = requests.Session()
    login_res = session.post(f"{BASE_URL}/api/login", json={"email": email, "password": password})
    print(f"=== Login {role_label} ({email}) ===")
    print("Login Response:", login_res.json())

    for page in ["/task-entry", "/dashboard", "/employees", "/shifts"]:
        res = session.get(f"{BASE_URL}{page}")
        html = res.text
        
        # Check if admin-only links exist in HTML
        has_locations = "Locations Management" in html
        has_managers = "Managers Directory" in html
        has_templates = "Email Templates" in html
        has_logs = "Daemon Logs & Audit" in html

        print(f"Page {page:15s} -> Locations: {has_locations}, Managers: {has_managers}, Templates: {has_templates}, Logs: {has_logs}")

print("Testing role-based navigation rendering:")
check_role_nav("manager@company.com", "manager123", "Manager")
check_role_nav("admin@company.com", "admin123", "Admin")
check_role_nav("john@company.com", "emp123", "Employee")
