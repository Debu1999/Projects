from pathlib import Path
from ocr_engine import extract_text

image = Path(__file__).parent / "BARTENDER-26.png"

results = extract_text(str(image))

print("\n========== OCR RESULT ==========\n")

for item in results:
    print(
        f"{item['text']} "
        f"(Confidence: {item['confidence']:.2f})"
    )