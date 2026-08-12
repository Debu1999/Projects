def validate_result(result):
    """
    Checks which required fields are missing from the LLM response.
 
    Returns:
        [] if everything is present.
        Otherwise returns a list of missing field names.
    """
 
    if not result:
        return [
            "application_name",
            "version",
            "timestamp_raw",
            "timestamp_iso"
        ]
 
    missing = []
 
    if not result.get("application_name"):
        missing.append("application_name")
 
    if not result.get("version"):
        missing.append("version")
 
    if not result.get("timestamp_raw"):
        missing.append("timestamp_raw")
 
    if not result.get("timestamp_iso"):
        missing.append("timestamp_iso")
 
    return missing