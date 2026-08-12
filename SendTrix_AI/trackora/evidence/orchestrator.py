from .extractor import extract
from .extraction_worker import extract_version_and_timestamp
from .validator import validate_result
from .retry_agent import run as retry_worker
from .compliance_worker import run as compliance_worker
from .review_window_worker import run as review_window_worker
from .database_worker import run as database_worker
from .recommendation_worker import run as recommendation_worker


MAX_RETRIES = 3
def process_evidence(file_path,appser_number):
 
    evidence = {
    "file_path": file_path,
    "appser_number": appser_number,
    "file_type": "",
 
    # OCR
    "ocr_text": "",
 
    # Extraction
    "application_name": "",
    "version": "",
    "timestamp_raw": "",
    "timestamp_iso": "",
    "version_candidates": [],
    "timestamp_candidates": [],
    "confidence_notes": "",

    # Compliance
    "review_start_date": "",
    "next_due_date": "",
    "expected_version": "",
    "compliance_note": "",
 
    # Validation
    "missing_fields": [],
 
    # Retry
    "retry_count": 0,
 
    # Result
    "compliance_status": "",
    "recommended_action": "",
 
    # Logs
    "logs": [],
    "errors": []
    }

    #Step 1-OCR Extraction
    #ocr_text = extract(file_path)
    try:
        ocr_text = extract(file_path)
    except Exception as e:
        evidence["errors"].append(str(e))
        return evidence
    evidence["ocr_text"] = ocr_text
    evidence["logs"].append("OCR extraction completed.")

    # Step 2 - Extract structured information
    #extracted_data = extract_version_and_timestamp(evidence["ocr_text"])
    try:
        extracted_data = extract_version_and_timestamp(evidence["ocr_text"])
    except Exception as e:
        evidence["errors"].append(str(e))
        return evidence
    if not extracted_data:
        evidence["errors"].append("Extraction Worker failed.")
        return evidence
    evidence.update(extracted_data)
    evidence["logs"].append("Extraction completed.")
    # Step 3 - Validate extraction
    missing_fields = validate_result(evidence)
    evidence["missing_fields"] = missing_fields
    
    # Step 4 - Check validation result
    if missing_fields:
        evidence["logs"].append(f"Validation failed. Missing fields: {missing_fields}")
    else:
        evidence["logs"].append("Validation passed.")
    print("Missing Fields:", evidence["missing_fields"])
    print("Evidence before retry:", evidence)
    # Step 5 - Retry loop
    print("Entered retry loop...")
    while evidence["missing_fields"] and evidence["retry_count"] < MAX_RETRIES:
        evidence = retry_worker(evidence)
        missing_fields = validate_result(evidence)
        evidence["missing_fields"] = missing_fields
        if missing_fields:
            evidence["logs"].append(f"Retry validation failed. Missing fields: {missing_fields}")
        else:
            evidence["logs"].append("Retry validation passed.")
    if evidence["missing_fields"]:
        evidence["logs"].append("Evidence requires manual review.")
        return evidence
    print("Exited retry loop.")
    print("Calling Database Worker...")
    evidence=database_worker(evidence)
    print("Database Worker completed.")
    evidence=review_window_worker(evidence)
    evidence=compliance_worker(evidence)
    evidence=recommendation_worker(evidence)
    if evidence["errors"]:
        evidence["logs"].append("Errors encountered during processing.")
        #return evidence
    else:
        evidence["logs"].append("Evidence extraction completed successfully.")
    return evidence
 