def run(evidence):
    """
    Recommendation Worker
 
    Converts compliance results into
    analyst actions.
    """
 
    evidence.setdefault("logs", []).append(
        "Recommendation Worker started."
    )
    status=evidence.get("compliance_status","").lower()
    if status == "compliant":
        evidence["recommended_action"] = "ACCEPT_EVIDENCE"
    elif status == "late":
        evidence["recommended_action"] = "REQUEST_UPDATED_EVIDENCE"
    elif status == "suspicious":
        evidence["recommended_action"] = "MANUAL_REVIEW"
    elif status == "missing":
        evidence["recommended_action"] = "RETRY_OCR"
    elif status == "unparseable":
        evidence["recommended_action"] = "MANUAL_REVIEW"
    else:
        evidence["recommended_action"] = "MANUAL_REVIEW"
    evidence["logs"].append("Recommendation generated.")
    #return evidence
 
 
    return evidence