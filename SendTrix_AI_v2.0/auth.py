import msal
import os
from dotenv import load_dotenv
from db import get_or_create_user_from_msal,get_user_by_microsoft_id
from cryptography.fernet import Fernet
 
load_dotenv()
 
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
 
if not TOKEN_ENCRYPTION_KEY:
    raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured")
 
fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode())
 
def encrypt_cache(cache_data):
    return fernet.encrypt(cache_data.encode()).decode()
 
 
def decrypt_cache(encrypted_data):
    return fernet.decrypt(encrypted_data.encode()).decode()
 
 
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
  
def get_access_token(user_id=None):
    #Try to load the encrypted token cache from the POSTGRES database if we have a user_id
    if user_id:
        cache_data = load_cache_from_db(user_id)
        print("Current user ID:", user_id)
        print("Cache loaded from DB:", cache_data is not None)
        if cache_data:
            print("Cache data length:", len(cache_data))
            cache = msal.SerializableTokenCache()
            cache.deserialize(cache_data)
        else:
            print("Cache loaded from DB:False")
            cache = msal.SerializableTokenCache()
    else:
        #Temporary fallback for first time authentication
        cache = msal.SerializableTokenCache()
 
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache
    )
    interactive_login = False
    accounts = app.get_accounts()
    print("MSAL Accounts count:", len(accounts))
    for account in accounts:
        print("MSAL Account:", 
              account.get("username"),
              account.get("home_account_id")
            )
    result=None
    if accounts:
        # Try silent first
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    #else:
        #result = None
 
    if not result or "access_token" not in result:
        interactive_login = True
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
    if interactive_login:
        print("MSAL result keys:", result.keys())
        claims = result.get("id_token_claims",{})
        print("Microsoft user:", claims.get("preferred_username"))
        user_id=get_or_create_user_from_msal(result)
        print("SendTrix user ID:", user_id)

    if user_id:
        if cache.has_state_changed:
            save_cache_to_db(user_id, cache.serialize())
    else:
        save_cache(cache)
 
    return result["access_token"],user_id

def load_cache_from_db(user_id):
    from db import get_postgres_connection
 
    conn = get_postgres_connection()
 
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT cache_data
                FROM user_token_caches
                WHERE user_id = %s
            """, (user_id,))
 
            row = cursor.fetchone()
 
            if not row:
                return None
 
            return decrypt_cache(row[0])
 
    finally:
        conn.close()
 
 
def save_cache_to_db(user_id, cache_data):
    from db import get_postgres_connection
 
    encrypted_data = encrypt_cache(cache_data)
 
    conn = get_postgres_connection()
 
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_token_caches (
                    user_id,
                    cache_data
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    cache_data = EXCLUDED.cache_data,
                    updated_at = NOW()
            """, (
                user_id,
                encrypted_data
            ))
 
        conn.commit()
 
    finally:
        conn.close()
 