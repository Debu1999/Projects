from db import upsert_application, init_db
 
# Make sure DB + table exists
init_db()
 
# Sample test data
sample = {
    "appser_name": "Test App",
    "appser_number": "ASN123",
    "appser_install_status": "Installed",
    "so_u_sbg": "Finance",
    "owner_name": "John",
    "tech_owner_name": "Mike",
    "current_installed_version": "1.0",
    "vendor_name": "Oracle",
    "reviewer_id": "rev1",
    "u_run_operations_focal": "Ops1",
    "comments": "Initial upload"
}
 
# Insert into DB
upsert_application(sample)
 
print("✅ Test Insert Successful")
 