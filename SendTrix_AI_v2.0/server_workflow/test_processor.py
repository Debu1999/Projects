from parser import load_server_workbook
from processor import build_server_inventory
 
 
file_path = r"C:\Users\H574648\Downloads\Total_Assets (5).xlsx"
 
workbook = load_server_workbook(file_path)
 
inventory = build_server_inventory(workbook)
 
print("\nFirst 5 Results:\n")
 
for item in inventory[:5]:
 
    print("Hostname:", item["hostname"])
    print("Assigned To:", item["assigned_to"])
    print("Email:", item["assigned_email"])
    print("Critical Count:", len(item["filtered_critical"]))
    print("-" * 50)
 