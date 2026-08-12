from workflow_service import (
    prepare_server_workflow
)
 
file_path = r"C:\Users\H574648\Downloads\Total_Assets (5).xlsx"
 
# ==========================
# Choose mode
# ==========================
 
mode = "owner"
 
# mode = "hostname"
 
results = prepare_server_workflow(
    file_path=file_path,
    mode=mode
)
 
print("\nFINAL RESULTS:\n")
 
for item in results[:5]:
 
    print(item)
 
    print("-" * 60)
 