def validate_result(result):
    """
    Validate the structured evidence result.
 
    Focus:
        - version
        - timestamp_raw
        - timestamp_iso
        - candidate confidence / score
 
    Returns:
    {
        "valid": True/False,
        "status": "VALID" / "NEEDS_REVIEW" / "INCOMPLETE",
        "missing": [],
        "errors": [],
        "warnings": []
    }
    """
 
    validation = {
        "valid": True,
        "status": "VALID",
        "missing": [],
        "errors": [],
        "warnings": []
    }
 
    # --------------------------------------------------
    # Result itself
    # --------------------------------------------------
 
    if not result:
 
        validation["valid"] = False
        validation["status"] = "INCOMPLETE"
 
        validation["missing"] = [
            "version",
            "timestamp_raw",
            "timestamp_iso"
        ]
 
        return validation
 
    # --------------------------------------------------
    # Required fields
    # --------------------------------------------------
 
    required_fields = [
        "version",
        "timestamp_raw",
        "timestamp_iso"
    ]
 
    for field in required_fields:
 
        if not result.get(field):
            validation["missing"].append(field)
 
    # --------------------------------------------------
    # VERSION VALIDATION
    # --------------------------------------------------
 
    version_candidates = result.get(
        "version_candidates",
        []
    )
 
    if result.get("version") and version_candidates:
 
        best_version = version_candidates[0]
 
        version_score = best_version.get(
            "score",
            0
        )
 
        # Very low score means the detector
        # isn't confident enough.
        if version_score < 7:
 
            validation["warnings"].append(
                "Version candidate has low confidence"
            )
 
    # --------------------------------------------------
    # TIMESTAMP VALIDATION
    # --------------------------------------------------
 
    timestamp_candidates = result.get(
        "timestamp_candidates",
        []
    )
 
    if result.get("timestamp_iso") and timestamp_candidates:
 
        best_timestamp = timestamp_candidates[0]
 
        timestamp_score = best_timestamp.get(
            "score",
            0
        )
 
        # Low timestamp score
        if timestamp_score < 7:
 
            validation["warnings"].append(
                "Timestamp candidate has low confidence"
            )
 
        # Check whether the timestamp was found
        # in a negative context such as:
        #
        # License expires
        # Support expires
        # Expiration date
        #
 
        negative_context = best_timestamp.get(
            "negative_context",
            []
        )
 
        if negative_context:
 
            validation["warnings"].append(
                "Timestamp appears in negative context: "
                + ", ".join(negative_context)
            )
 
    # --------------------------------------------------
    # BASIC TIMESTAMP CONSISTENCY
    # --------------------------------------------------
 
    if (
        result.get("timestamp_iso")
        and result.get("timestamp_raw")
    ):
 
        timestamp_iso = result["timestamp_iso"]
 
        if len(timestamp_iso) < 10:
 
            validation["errors"].append(
                "timestamp_iso appears invalid"
            )
 
    # --------------------------------------------------
    # DETERMINE FINAL STATUS
    # --------------------------------------------------
 
    # Missing information
    if validation["missing"]:
 
        validation["valid"] = False
        validation["status"] = "INCOMPLETE"
 
    # Extraction itself is invalid
    elif validation["errors"]:
 
        validation["valid"] = False
        validation["status"] = "INVALID"
 
    # Extraction exists but needs human review
    elif validation["warnings"]:
 
        validation["valid"] = False
        validation["status"] = "NEEDS_REVIEW"
 
    # Everything looks good
    else:
 
        validation["valid"] = True
        validation["status"] = "VALID"
 
    return validation
