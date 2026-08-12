from datetime import datetime, timedelta
 
 
def run(evidence):
    """
    Review Window Worker
 
    Calculates the review window for an application.
    """
 
    evidence.setdefault("logs", []).append(
        "Review Window Worker started."
    )
 
    # Step 1 - Read compliance mode
    mode = evidence.get("compliance_mode", "").upper()
    review_start = evidence.get("review_start_date")
    next_due = evidence.get("next_due_date")
    
    # Step 2 - DATE based applications
    if mode == "DATE":
        evidence["logs"].append("DATE based compliance detected.")
        #review_start = evidence.get("review_start_date")
        #next_due = evidence.get("next_due_date")
        
        if not review_start or not next_due:
            evidence.setdefault("errors", []).append("Review window is incomplete.")
            return evidence
        evidence["logs"].append("Review window prepared successfully.")
        return evidence
    # Step 3 - FREQUENCY based applications
    if mode == "FREQUENCY":
        evidence["logs"].append("FREQUENCY based compliance detected.")
        frequency = evidence.get("frequency")
        frequency_unit = evidence.get("frequency_unit", "days")

        if not review_start:
            evidence.setdefault("errors", []).append("Review start date is missing.")
            return evidence
        if not frequency:
            evidence.setdefault("errors", []).append("Frequency is missing.")
            return evidence
        try:
            review_start_date = datetime.fromisoformat(review_start)
        except Exception:
            evidence.setdefault("errors", []).append("Invalid review start date.")
            return evidence
        # Step 5 - Convert frequency to integer
        try:
            frequency = int(frequency)
        except Exception:
            evidence.setdefault("errors", []).append("Invalid frequency value.")
            return evidence
        # Step 6 - Calculate next due date
        if frequency_unit.lower() == "days":
            next_due = review_start_date + timedelta(days=frequency)
        elif frequency_unit.lower() == "minutes":
            next_due = review_start_date + timedelta(minutes=frequency)
        else:
            evidence.setdefault("errors", []).append(f"Unsupported frequency unit: {frequency_unit}")
            return evidence
        # Step 7 - Save calculated due date
        evidence["next_due_date"] = next_due.isoformat()
        evidence["logs"].append("Frequency review window calculated successfully.")
        return evidence
 
 
    return evidence