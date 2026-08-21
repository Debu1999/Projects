import re
from datetime import datetime
 
 
# --------------------------------------------------
# DATE PATTERNS
# --------------------------------------------------
 
DATE_PATTERNS = [
    # 6/5/2025
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
 
    # 6-5-2025
    re.compile(r"\b\d{1,2}-\d{1,2}-\d{4}\b"),
 
    # 6.5.2025
    re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"),
]
 
 
# --------------------------------------------------
# TIME PATTERNS
# --------------------------------------------------
 
TIME_PATTERNS = [
    # 4:31 PM
    re.compile(
        r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b"
    ),
 
    # 431 PM
    re.compile(
        r"\b\d{3,4}\s*(?:AM|PM|am|pm)\b"
    ),
 
    # 4:31
    re.compile(
        r"\b\d{1,2}:\d{2}\b"
    ),
]
TIMESTAMP_POSITIVE_LABELS = [
    "timestamp",
    "last updated",
    "updated",
    "update time",
    "modified",
    "modified time",
    "created",
    "created time",
    "date",
    "time",
]
 
TIMESTAMP_NEGATIVE_LABELS = [
    "expires",
    "expiry",
    "expiration",
    "license",
    "licence",
    "support",
    "valid until",
]
 
 
def get_box_position(box):
    """
    Return approximate OCR box position.
    """
 
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
 
    return (
        min(xs),
        min(ys),
        sum(xs) / len(xs),
        sum(ys) / len(ys)
    )
 
 
# --------------------------------------------------
# FIND DATE CANDIDATES
# --------------------------------------------------
 
def find_date_candidates(ocr_details):
 
    candidates = []
 
    for item in ocr_details:
 
        text = item["text"].strip()
        confidence = item["confidence"]
 
        matches = []
 
        for pattern in DATE_PATTERNS:
 
            matches.extend(pattern.findall(text))
 
        if not matches:
            continue
 
        candidates.append({
            "text": text,
            "date_candidates": matches,
            "confidence": confidence,
            "box": item["box"]
        })
 
    return candidates
 
 
# --------------------------------------------------
# FIND TIME CANDIDATES
# --------------------------------------------------
 
def find_time_candidates(ocr_details):
 
    candidates = []
 
    for item in ocr_details:
 
        text = item["text"].strip()
        confidence = item["confidence"]
 
        matches = []
 
        for pattern in TIME_PATTERNS:
 
            matches.extend(pattern.findall(text))
 
        if not matches:
            continue
 
        candidates.append({
            "text": text,
            "time_candidates": matches,
            "confidence": confidence,
            "box": item["box"]
        })
 
    return candidates
 
 
# --------------------------------------------------
# PARSE DATE
# --------------------------------------------------
 
def parse_date(date_text):
 
    date_text = date_text.strip()
 
    formats = [
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m.%d.%Y"
    ]
 
    for fmt in formats:
 
        try:
 
            return datetime.strptime(
                date_text,
                fmt
            ).date()
 
        except ValueError:
            continue
 
    return None
 
 
# --------------------------------------------------
# PARSE TIME
# --------------------------------------------------
 
def parse_time(time_text):
 
    time_text = time_text.strip()
 
    # Example:
    # 431 PM
    match = re.match(
        r"^(\d{3,4})\s*(AM|PM|am|pm)$",
        time_text
    )
 
    if match:
 
        digits = match.group(1)
        meridiem = match.group(2).upper()
 
        if len(digits) == 3:
 
            hour = int(digits[0])
            minute = int(digits[1:])
 
        else:
 
            hour = int(digits[:2])
            minute = int(digits[2:])
 
        if hour > 12 or minute > 59:
            return None
 
        if meridiem == "AM":
 
            if hour == 12:
                hour = 0
 
        else:
 
            if hour != 12:
                hour += 12
 
        return hour, minute
 
    # Example:
    # 4:31 PM
    match = re.match(
        r"^(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)$",
        time_text
    )
 
    if match:
 
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = match.group(3).upper()
 
        if hour > 12 or minute > 59:
            return None
 
        if meridiem == "AM":
 
            if hour == 12:
                hour = 0
 
        else:
 
            if hour != 12:
                hour += 12
 
        return hour, minute
 
    return None
 
 
# --------------------------------------------------
# COMBINE DATE + TIME
# --------------------------------------------------
def get_nearby_context(ocr_details, target_item, max_distance=180):
    """
    Find OCR text located near a date/time candidate.
    """
 
    _, _, target_x, target_y = get_box_position(
        target_item["box"]
    )
 
    nearby = []
 
    for item in ocr_details:
 
        if item is target_item:
            continue
 
        _, _, x, y = get_box_position(
            item["box"]
        )
 
        distance = (
            (target_x - x) ** 2 +
            (target_y - y) ** 2
        ) ** 0.5
 
        if distance <= max_distance:
            nearby.append({
                "text": item["text"],
                "distance": distance
            })
 
    return nearby
 
def find_timestamp_candidates(ocr_details):
 
    date_candidates = find_date_candidates(
        ocr_details
    )
 
    time_candidates = find_time_candidates(
        ocr_details
    )
 
    results = []
 
    for date_item in date_candidates:
 
        date_value = parse_date(
            date_item["date_candidates"][0]
        )
 
        if not date_value:
            continue
 
        _, _, date_x, date_y = get_box_position(
            date_item["box"]
        )
 
        for time_item in time_candidates:
 
            time_value = parse_time(
                time_item["time_candidates"][0]
            )
 
            if not time_value:
                continue
 
            _, _, time_x, time_y = get_box_position(
                time_item["box"]
            )
 
            # Distance between date and time
            distance = (
                (date_x - time_x) ** 2
                +
                (date_y - time_y) ** 2
            ) ** 0.5
 
            # Only combine reasonably close OCR elements
            if distance > 150:
                continue
 
            hour, minute = time_value
 
            timestamp = datetime(
                date_value.year,
                date_value.month,
                date_value.day,
                hour,
                minute
            )
 
            # ------------------------------------------
            # SCORE
            # ------------------------------------------
 
            score = 0
            # ------------------------------------------
            # CONTEXT SCORING
            # ------------------------------------------
            context_items = (
            get_nearby_context(ocr_details, date_item)
            +
            get_nearby_context(ocr_details,time_item)
            )
            positive_context = []
            negative_context = []

            for context in context_items:
                context_text = context["text"].lower()

                for label in TIMESTAMP_POSITIVE_LABELS:
                    if label in context_text:
                        positive_context.append(label)
                for label in TIMESTAMP_NEGATIVE_LABELS:
                    if label in context_text:
                        negative_context.append(label)
            # Positive timestamp context
            score += len(set(positive_context)) * 3
            # Negative expiry/license context
            score -= len(set(negative_context)) * 4
 
 
            # OCR confidence
            confidence = (
                date_item["confidence"]
                +
                time_item["confidence"]
            ) / 2
 
            if confidence >= 0.90:
                score += 3
 
            elif confidence >= 0.70:
                score += 2
 
            else:
                score += 1
 
            # Date and time are close together
            if distance <= 50:
                score += 5
 
            elif distance <= 100:
                score += 3
 
            else:
                score += 1
 
            results.append({
                "date": date_value.isoformat(),
                "time": f"{hour:02d}:{minute:02d}",
                "timestamp_iso": timestamp.isoformat(),
                "score": score,
                "distance": distance,
                "date_text": date_item["text"],
                "time_text": time_item["text"],
                "positive_context": list(set(positive_context)),
                "negative_context": list(set(negative_context))
            })
 
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )
 
    return results

if __name__ == "__main__":
 
    test_ocr = [
 
    # ------------------------------------------
    # GOOD TIMESTAMP
    # ------------------------------------------
 
    {
        "text": "Last Updated:",
        "confidence": 0.95,
        "box": [
            [100, 100],
            [200, 100],
            [200, 120],
            [100, 120]
        ]
    },
 
    {
        "text": "6/5/2025",
        "confidence": 0.90,
        "box": [
            [210, 100],
            [280, 100],
            [280, 120],
            [210, 120]
        ]
    },
 
    {
        "text": "431 PM",
        "confidence": 0.95,
        "box": [
            [290, 100],
            [350, 100],
            [350, 120],
            [290, 120]
        ]
    },
 
 
    # ------------------------------------------
    # BAD / IRRELEVANT TIMESTAMP
    # ------------------------------------------
 
    {
        "text": "License Expires:",
        "confidence": 0.95,
        "box": [
            [100, 300],
            [220, 300],
            [220, 320],
            [100, 320]
        ]
    },
 
    {
        "text": "4/15/2027",
        "confidence": 0.90,
        "box": [
            [230, 300],
            [310, 300],
            [310, 320],
            [230, 320]
        ]
    },
 
    {
        "text": "12:00 AM",
        "confidence": 0.95,
        "box": [
            [320, 300],
            [400, 300],
            [400, 320],
            [320, 320]
        ]
    }
]
 
 
    results = find_timestamp_candidates(
        test_ocr
    )
 
    print("\n========== TIMESTAMP CANDIDATES ==========")
 
    for result in results:
        print(result)
 
    print("========== END ==========")
 