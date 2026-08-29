from parser import load_server_workbook
 
 
file_path = r"C:\Users\H574648\Downloads\Total_Assets (5).xlsx"
 
data = load_server_workbook(file_path)
 
print("\nParser executed successfully.")