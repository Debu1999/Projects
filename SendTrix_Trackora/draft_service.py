import requests
from auth import get_access_token
from graph_client import get_graph_token
 
BASE_URL = "https://graph.microsoft.com/v1.0"
 
 
# =====================================
# Get All Drafts
# =====================================
def get_drafts():
    token=get_graph_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    url = f"{BASE_URL}/me/mailFolders/Drafts/messages?$select=id,subject,createdDateTime"

    drafts=[]
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(response.text)
        data=response.json()
        drafts.extend(data.get("value",[]))
        url=data.get("@odata.nextLink")
 
    return drafts
 
 
# =====================================
# Get Draft By ID
# =====================================
def get_draft_by_id(draft_id,folder_id="Drafts"):
    token=get_graph_token()
 
    headers = {
        "Authorization": f"Bearer {token}"
    }
 
    url = (
        f"{BASE_URL}/me/mailFolders/{folder_id}/messages/{draft_id}"
        "?$select=id,subject,body,toRecipients,ccRecipients"
    )
 
    response = requests.get(url, headers=headers)
 
    if response.status_code != 200:
        raise Exception(response.text)
 
    return response.json()
 