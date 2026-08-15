import easyocr
from .candidate_detector import find_version_candidates
 
reader = easyocr.Reader(["en"], gpu=False)
 
# Stores the detailed OCR result from the latest image
last_ocr_details = []
 
 
def read_image(path):
 
    global last_ocr_details
 
    result = reader.readtext(path)
 
    text_parts = []
    ocr_details = []
 
    for box, text, confidence in result:
 
        clean_box = [
            [int(point[0]), int(point[1])]
            for point in box
        ]
 
        text_parts.append(text)
 
        ocr_details.append({
            "text": text,
            "confidence": float(confidence),
            "box": clean_box
        })
 
    # Keep detailed OCR information available
    last_ocr_details = ocr_details
    print("\n========== DETAILED OCR ==========")
    for item in last_ocr_details:
        print("TEXT:", item["text"])
        print("CONFIDENCE:", item["confidence"])
        print("BOX:", item["box"])
    print("========== END DETAILED OCR ==========\n")
    version_candidates = find_version_candidates(ocr_details)
    print("\n========== VERSION CANDIDATES ==========")
    for candidate in version_candidates:
        print(candidate)
    print("========== END VERSION CANDIDATES ==========\n")
    
 
    # IMPORTANT:
    # Return only the text so existing Trackora code continues working
    return "\n".join(text_parts)
 