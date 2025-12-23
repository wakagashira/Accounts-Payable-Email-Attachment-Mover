import requests
from auth import get_access_token

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def graph_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "ConsistencyLevel": "eventual",
        "Content-Type": "application/json"
    }


def get_messages(mailbox):
    """
    Returns messages from the Inbox that have attachments.
    Inbox-only by endpoint design.
    """
    url = f"{GRAPH_BASE}/users/{mailbox}/mailFolders/Inbox/messages"
    params = {
        "$filter": "hasAttachments eq true",
        "$top": 25
    }

    resp = requests.get(url, headers=graph_headers(), params=params)
    resp.raise_for_status()
    return resp.json().get("value", [])


def get_attachments(mailbox, message_id):
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
    resp = requests.get(url, headers=graph_headers())
    resp.raise_for_status()
    return resp.json().get("value", [])


def add_category(mailbox, message_id, category_name="RaivenSynced"):
    """
    Adds (or overwrites) the Outlook category on the message.
    Requires Mail.ReadWrite (Application) permission.
    """
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    payload = {
        "categories": [category_name]
    }

    resp = requests.patch(url, headers=graph_headers(), json=payload)
    resp.raise_for_status()
