import re
 
VERSION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+){1,5}(?:[-_/][A-Za-z0-9]+)?\b"
)
 
VERSION_LABELS = [
    "product version",
    "software version",
    "application version",
    "release version",
    "build version",
    "version",
    "release",
    "build",
]
STRONG_VERSION_LABELS = [
    "product version",
    "software version",
    "application version",
]
 
VERSION_EXCLUDE_LABELS = [
    "data model version",
    "database code version",
    "xml version",
    "api version",
    "schema version",
]
 
 
def get_box_position(box):
    """
    Get approximate left, top and center coordinates
    from an OCR bounding box.
    """
 
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
 
    left = min(xs)
    top = min(ys)
 
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
 
    return left, top, center_x, center_y
 
def parse_version_value(text):
    """
    Extract the actual application version and optional build number
    from a version-related OCR string.
 
    Examples:
        '11.3/216048 (64-bit)'
            -> version='11.3', build='216048'
 
        'Product Version: 20.0.2.79 (R2Z-I)'
            -> version='20.0.2.79', build=None
 
        'Version: 20.0.0.324'
            -> version='20.0.0.324', build=None
    """
 
    text = text.strip()
 
    # --------------------------------------------------
    # Pattern 1:
    # version/build
    #
    # Example:
    # 11.3/216048
    # --------------------------------------------------
 
    slash_match = re.search(
        r"\b(\d+(?:\.\d+){1,5})/(\d+)\b",
        text
    )
 
    if slash_match:
 
        return {
            "version": slash_match.group(1),
            "build": slash_match.group(2)
        }
 
    # --------------------------------------------------
    # Pattern 2:
    # normal dotted version
    #
    # Examples:
    # 20.0.2.79
    # 20.0.0.324
    # --------------------------------------------------
 
    version_match = re.search(
        r"\b\d+(?:\.\d+){1,5}\b",
        text
    )
 
    if version_match:
 
        return {
            "version": version_match.group(0),
            "build": None
        }
 
    return {
        "version": None,
        "build": None
    }
 
def find_version_candidates(ocr_details):
 
    candidates = []
 
    # --------------------------------------------------
    # STEP 1: Find explicit version labels
    # --------------------------------------------------
 
    version_labels = []
 
    for item in ocr_details:
 
        text = item["text"].strip().lower()
 
        for label in VERSION_LABELS:
 
            if label in text:
 
                version_labels.append({
                    "item": item,
                    "label": label
                })
 
                break
 
    # --------------------------------------------------
    # STEP 2: Look for version values near the label
    # --------------------------------------------------
 
    for label_info in version_labels:
 
        label_item = label_info["item"]
 
        label_box = label_item["box"]
 
        _, label_top, label_center_x, label_center_y = \
            get_box_position(label_box)
 
        for item in ocr_details:
 
            # Don't compare the label with itself
            if item is label_item:
                continue
 
            text = item["text"].strip()
 
            matches = VERSION_PATTERN.findall(text)
 
            if not matches:
                continue
            parsed=parse_version_value(text)
 
            value_box = item["box"]
 
            value_left, value_top, value_center_x, value_center_y = \
                get_box_position(value_box)
 
            # --------------------------------------------------
            # Determine whether the value is on approximately
            # the same horizontal line as the Version label.
            # --------------------------------------------------
 
            vertical_distance = abs(
                value_center_y - label_center_y
            )
 
            horizontal_distance = value_left - label_center_x
 
            # Value should normally be to the RIGHT of the label
            if horizontal_distance < 0:
                continue
 
            # Allow small vertical difference
            if vertical_distance > 30:
                continue
 
            # Strong candidate because it is next to a version label
            score = 0
            label_text = label_info["label"]

            # Strong application/product version labels
            if label_text in STRONG_VERSION_LABELS:
                score += 10
            # Generic version label
            elif label_text == "version":
                score += 5
            else:
                score += 4
 
            # Same horizontal line
            score += 3
 
            # Value is to the right of label
            score += 2
 
            # OCR confidence
            confidence = item["confidence"]
 
            if confidence >= 0.90:
                score += 2
            elif confidence >= 0.70:
                score += 1
 
            candidates.append({
                "text": text,
                "version_candidates": matches,
                "version": parsed["version"],
                "build": parsed["build"],
                "confidence": confidence,
                "score": score,
                "box": value_box,
                "reason": "near Version label"
            })
 
    # --------------------------------------------------
    # STEP 3: Normal standalone version detection
    # --------------------------------------------------
 
    for item in ocr_details:
 
        text = item["text"].strip()
        confidence = item["confidence"]
 
        matches = VERSION_PATTERN.findall(text)
 
        if not matches:
            continue
        parsed=parse_version_value(text)
 
        text_lower = text.lower()
 
        # Skip if we already added this exact item
        already_added = any(
            candidate["box"] == item["box"]
            for candidate in candidates
        )
 
        if already_added:
            continue
 
        # Label score
        label_score = 0
 
        for label in VERSION_LABELS:
 
            if label in text_lower:
                if label in STRONG_VERSION_LABELS:
                    label_score += 4
                elif label == "version":
                    label_score += 2
                else:
                    label_score += 1
 
        # Exclusion score
        exclude_score = 0
 
        for label in VERSION_EXCLUDE_LABELS:
 
            if label in text_lower:
                exclude_score += 1
 
        score = 0
 
        # Numeric version pattern
        score += 2
 
        # Label found
        score += label_score * 3
 
        # Excluded label
        score -= exclude_score * 3
 
        # OCR confidence
        if confidence >= 0.90:
            score += 2
 
        elif confidence >= 0.70:
            score += 1
 
        candidates.append({
            "text": text,
            "version_candidates": matches,
            "version": parsed["version"],
            "build": parsed["build"],
            "confidence": confidence,
            "score": score,
            "box": item["box"],
            "reason": "standalone pattern"
        })
 
    # --------------------------------------------------
    # Sort highest confidence candidate first
    # --------------------------------------------------
 
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )
 
    return candidates
 
 
if __name__ == "__main__":
 
    test_ocr = [
 
        {
            "text": "Version:",
            "confidence": 0.935,
            "box": [[429, 241], [481, 257]]
        },
 
        {
            "text": "11.3/216048 (64-bit)",
            "confidence": 0.878,
            "box": [[551, 241], [665, 257]]
        },
 
        {
            "text": "Windows Server 2022 Standard x64 build 20348",
            "confidence": 0.662,
            "box": [[551, 263], [841, 277]]
        },
 
        {
            "text": "Expires on 4/15/2027",
            "confidence": 0.649,
            "box": [[551, 305], [741, 321]]
        },
 
        {
            "text": "7/9/2026",
            "confidence": 0.624,
            "box": [[1219, 677], [1269, 691]]
        }
 
    ]
 
    results = find_version_candidates(test_ocr)
 
    print("\n========== VERSION CANDIDATES ==========")
 
    for candidate in results:
        print(candidate)
 
    print("========== END ==========")
 