from .extraction_worker import check_compliance_window
 
 
def run(evidence):
    """
    Compliance Worker
 
    Decides whether the extracted evidence is compliant.
    """
 
    evidence.setdefault("logs", []).append(
        "Compliance Worker started."
    )
    # Step 1 - Get required values
    timestamp_iso = evidence.get("timestamp_iso")
    review_start = evidence.get("review_start_date")
    next_due = evidence.get("next_due_date")
    
    # Step 2 - Validate required values
    if not timestamp_iso:
        evidence.setdefault("errors", []).append("Screenshot timestamp not available.")
        return evidence
    if not review_start or not next_due:
        evidence.setdefault("errors", []).append("Review period not available.")
        return evidence
    
    # Step 3 - Check timestamp compliance
    result = check_compliance_window(timestamp_iso,review_start,next_due)
    
    # Step 4 - Store result
    evidence["compliance_status"] = result["status"]
    evidence["compliance_note"] = result["note"]
    evidence["logs"].append("Timestamp compliance check completed.")
 
 
    # Remaining logic will be added step by step.
 
    return evidence