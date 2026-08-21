import easyocr
from .candidate_detector import find_version_candidates
from .timestamp_detector import find_timestamp_candidates
 
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
    timestamp_results = find_timestamp_candidates(ocr_details)
    print("\n========== TIMESTAMP CANDIDATES ==========")
    for result in timestamp_results:
        print(result)
    print("========== END TIMESTAMP CANDIDATES ==========\n")
 
    # IMPORTANT:
    # Return only the text so existing Trackora code continues working
    return "\n".join(text_parts)

if __name__ == "__main__":
 
    from .evidence_extractor import extract_evidence
 
    image_path = input("Enter the path to the image file: ")
 
    read_image(image_path)
 
    result = extract_evidence(
        last_ocr_details
    )
    from .validator import validate_result
    validation = validate_result(result)
 
    print("\n========== FINAL EVIDENCE ==========")
 
    print("VERSION:")
    print(result["version"])
 
    print("BUILD:")
    print(result["build"])
 
    print("TIMESTAMP:")
    print(result["timestamp_iso"])
 
    print("RAW TIMESTAMP:")
    print(result["timestamp_raw"])
 
    print("\n========== END FINAL EVIDENCE ==========")

    print("\n========== VALIDATION ==========")
    print(validation)
    print("========== END VALIDATION ==========\n")
 