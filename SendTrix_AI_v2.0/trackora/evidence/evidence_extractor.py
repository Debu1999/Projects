from .candidate_detector import find_version_candidates
from .timestamp_detector import find_timestamp_candidates
 
 
def extract_evidence(ocr_details):
    """
    Combine version and timestamp detection
    into one structured evidence result.
    """
 
    # -----------------------------------------
    # VERSION
    # -----------------------------------------
 
    version_candidates = find_version_candidates(
        ocr_details
    )
 
    best_version = None
    best_build = None
 
    if version_candidates:
 
        best = version_candidates[0]
 
        best_version = best.get("version")
        best_build = best.get("build")
 
 
    # -----------------------------------------
    # TIMESTAMP
    # -----------------------------------------
 
    timestamp_candidates = find_timestamp_candidates(
        ocr_details
    )
 
    best_timestamp = None
    timestamp_raw = None
 
    if timestamp_candidates:
 
        best_timestamp = timestamp_candidates[0].get(
            "timestamp_iso"
        )
 
        date_text = timestamp_candidates[0].get(
            "date_text"
        )
 
        time_text = timestamp_candidates[0].get(
            "time_text"
        )
 
        if date_text and time_text:
            timestamp_raw = f"{time_text} {date_text}"
 
 
    # -----------------------------------------
    # FINAL STRUCTURED RESULT
    # -----------------------------------------
 
    return {
        "version": best_version,
        "build": best_build,
        "timestamp_iso": best_timestamp,
        "timestamp_raw": timestamp_raw,
 
        # Keep candidates available for debugging
        "version_candidates": version_candidates,
        "timestamp_candidates": timestamp_candidates
    }
 