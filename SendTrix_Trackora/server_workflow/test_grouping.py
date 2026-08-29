from parser import load_server_workbook
from processor import build_server_inventory
from attachment_builder import generate_hostname_attachment
from grouping import group_per_hostname,group_by_owner
 
 
file_path = r"C:\Users\H574648\Downloads\Total_Assets (5).xlsx"
 
workbook = load_server_workbook(file_path)
 
inventory = build_server_inventory(workbook)
 
# Only first 5 for testing
inventory = inventory[:5]
 
# Generate attachments
for item in inventory:
 
    attachment = generate_hostname_attachment(item)
 
    item["attachment_path"] = attachment
 
# Grouping
grouped = group_per_hostname(inventory)
owner_grouped = group_by_owner(inventory)
 
print("\nGROUPED BY OWNER:\n")
 
for g in owner_grouped:
 
    print(g)
    print("-" * 50)
 
print("\nGrouped Results:\n")
 
for g in grouped:
 
    print(g)
    print("-" * 50)
 