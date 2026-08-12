from evidence.extractor import extract

ocr_text = extract()
result = extract_version_and_timestamp(ocr_text)

from evidence.screenshot_analysis import extract_version_and_timestamp, check_compliance_window

ocr_text = extract("BARTENDER-26.png")
result = extract_version_and_timestamp(ocr_text)

if result:
    # review_start_date and next_due_date already exist in your
    # application_analysis table for this ASN - just pull them from there
    window_check = check_compliance_window(
        result["timestamp_iso"],
        review_start_date_iso,   # from application_analysis
        next_due_date_iso        # from application_analysis
    )
    print("Version:", result["version"])
    print("Timestamp found:", result["timestamp_raw"])
    print("Compliance check:", window_check["status"], "-", window_check["note"])