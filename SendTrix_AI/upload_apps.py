'''import pandas as pd
from db import upsert_application, init_db
 
# Initialize DB
init_db()
 
file_path = "applications_dump.xlsx"  # your Excel file
 
df = pd.read_excel(file_path)
 
for _, row in df.iterrows():
    app_data = {
        "appser_name": row.get("appser_name"),
        "appser_number": row.get("appser_number"),
        "appser_install_status": row.get("appser_install_status"),
        "so_u_sbg": row.get("so_u_sbg"),
        "owner_name": row.get("owner_name"),
        "tech_owner_name": row.get("tech_owner_name"),
        "current_installed_version": row.get("current_installed_version"),
        "vendor_name": row.get("vendor_name"),
        "reviewer_id": row.get("reviewer_id"),
        "u_run_operations_focal": row.get("u_run_operations_focal"),
        "u_run_focals": "",
        "comments": ""
    }
 
    if app_data["appser_number"]:
        upsert_application(app_data)
 
print("✅ Excel upload completed")'''
 
import csv
from db import upsert_application, init_db
 
# Initialize DB
init_db()
 
file_path = "applications_dump.csv"  # change if needed
 
with open(file_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
 
    for row in reader:
        app_data = {
            "appser_name": row.get("appser_name"),
            "appser_number": row.get("appser_number"),
            "appser_install_status": row.get("appser_install_status"),
            "so_u_sbg": row.get("so_u_sbg"),
            "owner_name": row.get("owner_name"),
            "tech_owner_name": row.get("tech_owner_name"),
            "current_installed_version": row.get("current_installed_version"),
            "vendor_name": row.get("vendor_name"),
            "reviewer_id": row.get("reviewer_id"),
            "u_run_operations_focal": row.get("u_run_operations_focal"),
            "comments": ""
        }
 
        if app_data["appser_number"]:  # skip empty rows
            upsert_application(app_data)
 
print("✅ Bulk upload completed")
 