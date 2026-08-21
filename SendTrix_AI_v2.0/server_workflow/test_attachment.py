from parser import load_server_workbook
from processor import build_server_inventory
from attachment_builder import generate_hostname_attachment
 
 
file_path = r"C:\Users\H574648\Downloads\Total_Assets (5).xlsx"
 
workbook = load_server_workbook(file_path)
 
inventory = build_server_inventory(workbook)
 
# Test first 5 hostnames only
for item in inventory[:5]:
 
    attachment = generate_hostname_attachment(item)
    item["attachment_path"]=attachment
 
    print("Attachment:", attachment)