def recommend_next_action(application):
 
    score = 0
    reasons = []
 
    # =====================================
    # Rule 1 - Non-Compliant
    # =====================================
    if application.get("internal_status") == "Non-compliant":
        score += 40
        reasons.append("Application is currently Non-Compliant.")
 
    # =====================================
    # Decide Priority
    # =====================================
    if score >= 90:
        priority = "CRITICAL"
    elif score >= 70:
        priority = "HIGH"
    elif score >= 40:
        priority = "MEDIUM"
    else:
        priority = "LOW"
 
    return {
        "priority": priority,
        "score": score,
        "next_action": "REVIEW_APPLICATION",
        "reasons": reasons
    }
