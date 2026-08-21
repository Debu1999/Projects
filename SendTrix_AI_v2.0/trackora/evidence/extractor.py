from .detector import detect_type
from .image_reader import read_image
from .pdf_reader import read_pdf
from .docx_reader import read_docx
from .excel_reader import read_excel
 
def extract(file_path):
 
    file_type = detect_type(file_path)
 
    if file_type == "IMAGE":
        return read_image(file_path)
 
    if file_type == "PDF":
        return read_pdf(file_path)
 
    if file_type == "DOCX":
        return read_docx(file_path)
 
    if file_type == "EXCEL":
        return read_excel(file_path)
 
    raise Exception("Unsupported file")
 