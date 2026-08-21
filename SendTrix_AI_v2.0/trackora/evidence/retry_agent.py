from .extraction_worker import call_ollama, try_parse_json
#from validator import validate_result

def build_retry_prompt(missing_fields, ocr_text):
    """
    Builds a retry prompt based on which fields are missing.
    """
 
    if "timestamp_raw" in missing_fields:
        return f"""
The application name and version have already been identified.
 
Focus ONLY on identifying the PC system clock timestamp from the OCR text below.
 
OCR TEXT:
{ocr_text}
 
Return ONLY this JSON:
 
{{
    "timestamp_raw": "",
    "timestamp_iso": ""
}}
"""
 
    if "version" in missing_fields:
        return f"""
Focus ONLY on identifying the application version.
 
OCR TEXT:
{ocr_text}
 
Return ONLY:
 
{{
    "version": ""
}}
"""
 
    if "application_name" in missing_fields:
        return f"""
Focus ONLY on identifying the application name.
 
OCR TEXT:
{ocr_text}
 
Return ONLY:
 
{{
    "application_name": ""
}}
"""
 
    return None

def merge_results(original, retry):
 
    if not retry:
        return original
 
    for key, value in retry.items():
 
        # Only update if original value is missing
        if not original.get(key) and value:
            original[key] = value
 
    return original
 
#MAX_RETRIES = 3
 
 
def run(evidence):
    print("Retry Worker Called")
    print("Current Retry Count:", evidence.get("retry_count"))
    """
    Retry Worker
 
    Input:
        evidence (dict)
 
    Output:
        Updated evidence (dict)
    """
 
    # Step 1 - Check if anything is missing
    missing_fields = evidence.get("missing_fields", [])
 
    # Nothing to retry
    if not missing_fields:
        return evidence
 
    # Step 2 - Check retry limit
    '''if evidence.get("retry_count", 0) >= MAX_RETRIES:
        evidence.setdefault("errors", []).append(
            "Maximum retry attempts reached."
        )
        return evidence'''
    # Step 3 - Build retry prompt
    retry_prompt = build_retry_prompt(missing_fields,evidence["ocr_text"])
    # Step 4 - Ask Ollama again
    #raw_response = call_ollama(retry_prompt)
    try:
        print("Calling Ollama")
        raw_response = call_ollama(retry_prompt)
        print("Returned from Ollama")
        print(type(raw_response))
        print(raw_response[:200])
    except Exception as e:
        evidence.setdefault("errors", []).append(str(e))
        return evidence
    if not retry_prompt:
        evidence.setdefault("errors", []).append("Unable to build retry prompt.")
        return evidence
    if not raw_response:
        evidence.setdefault("errors", []).append("Retry failed. Ollama returned no response.")
        return evidence
    print("Raw Ollama Response:", raw_response)
    retry_result = try_parse_json(raw_response)
    print("Parsed Retry Result:", retry_result)
    print("Retry Result Type:", type(retry_result))
    if not isinstance(retry_result, dict):
        evidence.setdefault("errors", []).append(f"Retry returned invalid type: {type(retry_result).__name__}")

        return evidence
    if not retry_result:
        evidence.setdefault("errors", []).append("Retry failed. Invalid JSON returned.")
        return evidence
    # Step 5 - Merge retry result with existing evidence
    print("Retry Result Type:", type(retry_result))
    print("Retry Result:", retry_result)
    evidence = merge_results(evidence, retry_result)
    # Step 6 - Increase retry count
    evidence["retry_count"] = evidence.get("retry_count", 0) + 1
    # Step 7 - Log completion
    evidence.setdefault("logs", []).append(f"Retry #{evidence['retry_count']} completed.")
    #evidence["logs"].append(f"Retry #{evidence['retry_count'] + 1} started.")
    #evidence.setdefault("logs", []).append(f"Retry #{evidence['retry_count'] + 1} started.")
    return evidence
 