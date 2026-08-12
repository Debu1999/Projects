import easyocr

# Load the model only once
reader = easyocr.Reader(
    ['en'],
    gpu=False
)

def extract_text(image_path):

    results = reader.readtext(image_path)

    extracted_text = []

    for result in results:
        text = result[1]
        confidence = result[2]

        extracted_text.append({
            "text": text,
            "confidence": confidence
        })

    return extracted_text