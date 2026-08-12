from pathlib import Path
 
def detect_type(file_path):
 
    ext = Path(file_path).suffix.lower()
 
    if ext in [".png", ".jpg", ".jpeg", ".bmp"]:
        return "IMAGE"
 
    if ext == ".pdf":
        return "PDF"
 
    if ext == ".docx":
        return "DOCX"
 
    if ext in [".xlsx", ".xls"]:
        return "EXCEL"
 
    if ext == ".zip":
        return "ZIP"
 
    raise Exception(f"Unsupported file : {ext}")