import csv
from db import init_db, create_new_version, insert_snapshot
 
init_db()
 
file_path = "COTS_Test.csv"
 
# Step 1: Create new version
version_id, version_number = create_new_version(file_path)
 
print(f"📦 Creating Version: v{version_number}")
 
# Step 2: Insert snapshot data
with open(file_path, newline='', encoding='latin-1') as csvfile:
    reader = csv.DictReader(csvfile)
 
    count = 0
 
    for row in reader:
        if row.get("appser_number"):
            insert_snapshot(version_id, row)
            count += 1
 
print(f"✅ Version v{version_number} created with {count} records")