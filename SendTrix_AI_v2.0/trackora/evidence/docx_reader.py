from docx import Document
import os
from io import BytesIO
from .image_reader import read_image
 
def read_docx(path):
 
    doc = Document(path)
    image_ocr=[]
    for i, shape in enumerate(doc.inline_shapes):
        image = shape._inline.graphic.graphicData.pic.blipFill.blip
        rId = image.embed
        image_part = doc.part.related_parts[rId]
        image_bytes = image_part.blob
        image_path = f"temp_image_{i}.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)
            ocr_output = read_image(image_path)
            print(f"OCR output for image {i}:", ocr_output)
            image_ocr.append(ocr_output)
        print("Saved:", image_path)
 
    print("Number of inline shapes:", len(doc.inline_shapes))
 
    text = "\n".join(
        p.text
        for p in doc.paragraphs
    )
    combined_text = text + "\n\n" + "\n\n".join(image_ocr)
    return combined_text