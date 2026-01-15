import requests
from datetime import datetime, timedelta, timezone
from auth import get_access_token
from config import (
    MAIL_SYNC_TYPE,
    MAIL_LOOKBACK_DAYS,
    MAIL_FROM_DATE,
    MAIL_TO_DATE,
)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def graph_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }


def build_received_date_filter():
    """
    Builds the receivedDateTime filter for Microsoft Graph
    based on MAIL_SYNC_TYPE.
    """
    now = datetime.now(timezone.utc)

    if MAIL_SYNC_TYPE.lower() == "days":
        start = now - timedelta(days=MAIL_LOOKBACK_DAYS)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"receivedDateTime ge {start_str}"

    if MAIL_SYNC_TYPE.lower() == "span":
        if not MAIL_FROM_DATE or not MAIL_TO_DATE:
            raise ValueError(
                "MAIL_FROM_DATE and MAIL_TO_DATE must be set when MAIL_SYNC_TYPE=Span"
            )

        start = datetime.fromisoformat(MAIL_FROM_DATE).replace(
            tzinfo=timezone.utc
        )
        end = datetime.fromisoformat(MAIL_TO_DATE).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

        return (
            f"receivedDateTime ge {start_str} "
            f"and receivedDateTime le {end_str}"
        )

    raise ValueError(f"Invalid MAIL_SYNC_TYPE: {MAIL_SYNC_TYPE}")


def get_messages(mailbox):
    date_filter = build_received_date_filter()

    url = f"{GRAPH_BASE}/users/{mailbox}/messages"
    params = {
        "$filter": f"hasAttachments eq true and {date_filter}",
        "$top": 50,
    }

    messages = []

    while url:
        resp = requests.get(url, headers=graph_headers(), params=params)
        resp.raise_for_status()

        data = resp.json()
        messages.extend(data.get("value", []))

        url = data.get("@odata.nextLink")
        params = None  # nextLink already contains params

    return messages


def get_attachments(mailbox, message_id):
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
    resp = requests.get(url, headers=graph_headers())
    resp.raise_for_status()
    return resp.json().get("value", [])


def add_category(mailbox, message_id):
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
    body = {"categories": ["RaivenSynced"]}
    resp = requests.patch(url, headers=graph_headers(), json=body)
    resp.raise_for_status()
