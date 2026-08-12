import msal
import os
from dotenv import load_dotenv
 
load_dotenv()
 
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
 
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.ReadWrite", "Mail.Send","Calendars.ReadWrite","OnlineMeetings.ReadWrite"]
 
CACHE_FILE = "token_cache.json"
 
 
def load_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache.deserialize(f.read())
        except Exception:
            pass
    return cache
 
 
def save_cache(cache):
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())
 
 
def get_access_token():
    cache = load_cache()
 
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )
 
    accounts = app.get_accounts()
    result=None
    if accounts:
        # Try silent first
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    #else:
        #result = None
 
    if not result or "access_token" not in result:
        print("Accounts:",accounts)
        print("Silent result:",result)
        # Device flow only if no cached token
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise Exception("Device flow failed",flow)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
 
    if "access_token" not in result:
        raise Exception("Authentication failed", result)
 
    save_cache(cache)
 
    return result["access_token"]