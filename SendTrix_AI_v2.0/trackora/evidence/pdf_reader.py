import fitz
 
from .image_reader import read_image
 
def read_pdf(path):
 
    doc = fitz.open(path)
 
    full_text = []
 
    for page in doc:
 
        text = page.get_text()
 
        if text.strip():
 
            full_text.append(text)
 
            pix = page.get_pixmap()
 
            image = f"temp_page_{page.number}.png"
 
            pix.save(image)
            ocr_text = read_image(image)
 
            full_text.append(ocr_text)
 
    return "\n\n".join(full_text)
 