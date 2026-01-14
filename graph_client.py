import requests
from datetime import datetime, timedelta, timezone

from auth import get_access_token
from config import MAIL_LOOKBACK_DAYS

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def graph_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "ConsistencyLevel": "eventual",
        "Content-Type": "application/json",
    }


def get_messages(mailbox):
    """
    Returns messages from ALL folders in the mailbox,
    filtered by receivedDateTime and paginated safely.
    """
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=MAIL_LOOKBACK_DAYS)
    cutoff_iso = cutoff_dt.isoformat()

    url = f"{GRAPH_BASE}/users/{mailbox}/messages"
    params = {
        "$filter": f"hasAttachments eq true and receivedDateTime ge {cutoff_iso}",
        "$top": 50,
    }

    messages = []

    while url:
        resp = requests.get(url, headers=graph_headers(), params=params)
        resp.raise_for_status()

        data = resp.json()
        messages.extend(data.get("value", []))

        # Pagination
        url = data.get("@odata.nextLink")
        params = None  # nextLink already contains params

    return messages


def get_attachments(mailbox, message_id):
    """
    Returns all attachments for a specific message.
    """
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
    resp = requests.get(url, headers=graph_headers())
    resp.raise_for_status()
    return resp.json().get("value", [])


def add_category(mailbox, message_id, category_name="RaivenSynced"):
    """
    Applies an Outlook category to the message.
    Requires Mail.ReadWrite (Application).
    """
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    payload = {"categories": [category_name]}

    resp = requests.patch(url, headers=graph_headers(), json=payload)
    resp.raise_for_status()
