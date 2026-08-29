import re
 
# RFC-like practical email validation
EMAIL_PATTERN = re.compile(
    r"^(?=.{1,254}$)"
    r"(?=.{1,64}@)"
    r"[A-Za-z0-9._%+-]+"
    r"@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)
 
def is_valid_email(email):
    """
    Returns True if email format is valid.
    """
    if not email:
        return False
    return bool(EMAIL_PATTERN.match(email.strip()))
 
 
def clean_email_list(email_string):
    """
    Accepts mixed separators:
    , ; |
    Removes duplicates
    Removes invalid emails
    Returns clean list
    """
 
    if not email_string:
        return []
 
    # Split by comma, semicolon, or pipe
    raw_emails = re.split(r"[;,|]", email_string)
 
    cleaned = []
    seen = set()
 
    for email in raw_emails:
        email = email.strip()
 
        if not email:
            continue
 
        if not is_valid_email(email):
            continue
 
        lower_email = email.lower()
 
        if lower_email not in seen:
            cleaned.append(email)
            seen.add(lower_email)
 
    return cleaned