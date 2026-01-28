import logging
import random
import time
from datetime import datetime, timedelta, timezone

import requests

from auth import get_access_token
from config import (
    MAIL_SYNC_TYPE,
    MAIL_LOOKBACK_DAYS,
    MAIL_FROM_DATE,
    MAIL_TO_DATE,
)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Use your main logger name so it shows in the same stream
logger = logging.getLogger("RaivenSync")

# Retry ONLY for known transient Graph failures
_RETRY_STATUS = {429, 503, 504}


def build_received_date_filter() -> str:
    now = datetime.now(timezone.utc)

    if (MAIL_SYNC_TYPE or "").lower() == "days":
        start = now - timedelta(days=MAIL_LOOKBACK_DAYS)
        return f"receivedDateTime ge {start.strftime('%Y-%m-%dT%H:%M:%SZ')}"

    if (MAIL_SYNC_TYPE or "").lower() == "span":
        if not MAIL_FROM_DATE or not MAIL_TO_DATE:
            raise ValueError("MAIL_FROM_DATE and MAIL_TO_DATE are required when MAIL_SYNC_TYPE=Span")

        start = datetime.strptime(MAIL_FROM_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(MAIL_TO_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

        return (
            f"receivedDateTime ge {start.strftime('%Y-%m-%dT%H:%M:%SZ')} and "
            f"receivedDateTime lt {end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

    raise ValueError(f"Invalid MAIL_SYNC_TYPE: {MAIL_SYNC_TYPE}")


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

        self._access_token: str | None = None
        self._session = requests.Session()

    def _headers(self) -> dict:
        if not self._access_token:
            self._access_token = get_access_token(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        timeout: int = 60,
        max_attempts: int = 6,
    ) -> requests.Response:
        last_exc = None

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                    timeout=timeout,
                )

                # Refresh token once if needed
                if resp.status_code == 401 and self._access_token is not None:
                    self._access_token = None
                    resp = self._session.request(
                        method,
                        url,
                        headers=self._headers(),
                        params=params,
                        json=json,
                        timeout=timeout,
                    )

                # Retry ONLY transient statuses
                if resp.status_code in _RETRY_STATUS:
                    retry_after = resp.headers.get("Retry-After")
                    sleep_s = (
                        int(retry_after)
                        if retry_after
                        else min(60, 2 ** (attempt - 1)) + random.random()
                    )

                    if attempt == max_attempts:
                        resp.raise_for_status()

                    logger.warning(
                        "Graph transient error %s on %s %s (attempt %s/%s). Sleeping %.1fs",
                        resp.status_code,
                        method,
                        url,
                        attempt,
                        max_attempts,
                        sleep_s,
                    )
                    time.sleep(sleep_s)
                    continue

                # DO NOT retry client errors
                if 400 <= resp.status_code < 500:
                    logger.error(
                        "Graph client error %s on %s %s. Body: %s",
                        resp.status_code,
                        method,
                        url,
                        (resp.text or "")[:1000].replace("\n", " "),
                    )
                    resp.raise_for_status()

                resp.raise_for_status()
                return resp

            except requests.RequestException as exc:
                last_exc = exc
                if attempt == max_attempts:
                    raise
                sleep_s = min(60, 2 ** (attempt - 1)) + random.random()
                logger.warning(
                    "Graph request exception on %s %s (attempt %s/%s): %s. Sleeping %.1fs",
                    method,
                    url,
                    attempt,
                    max_attempts,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)

        raise last_exc if last_exc else RuntimeError("Graph request failed")

    # -------------------------
    # Folder discovery (Option 1)
    # -------------------------

    def _list_child_folders(self, mailbox: str, folder_id_or_wellknown: str) -> list[dict]:
        """
        Returns a flat list of child folder dicts (id, displayName, etc.) for a given folder.
        """
        # Supports well-known name "inbox" or a real folder id
        url = f"{GRAPH_BASE}/users/{mailbox}/mailFolders/{folder_id_or_wellknown}/childFolders"
        params = {
            "$top": "200",
            "$select": "id,displayName",
        }

        folders: list[dict] = []

        while url:
            resp = self._request_with_retry("GET", url, params=params)
            data = resp.json()
            folders.extend(data.get("value", []))

            url = data.get("@odata.nextLink")
            params = None

        return folders

    def _get_inbox_descendant_folder_ids(self, mailbox: str) -> list[str]:
        """
        Returns folder IDs for all descendants under Inbox (recursive),
        plus the well-known 'inbox' itself as the first element.
        """
        # We include 'inbox' as a pseudo id so callers can query it directly.
        folder_ids: list[str] = ["inbox"]

        # BFS over child folders
        queue: list[str] = ["inbox"]
        seen: set[str] = set(queue)

        while queue:
            current = queue.pop(0)
            children = self._list_child_folders(mailbox, current)

            for f in children:
                fid = f.get("id")
                if not fid or fid in seen:
                    continue
                seen.add(fid)
                folder_ids.append(fid)
                queue.append(fid)

        return folder_ids

    # -------------------------
    # Message retrieval (Inbox + subfolders)
    # -------------------------

    def _get_messages_in_folder(self, mailbox: str, folder_id_or_wellknown: str) -> list[dict]:
        """
        Query messages with attachments in a specific folder (inbox or subfolder id).
        """
        date_filter = build_received_date_filter()

        url = f"{GRAPH_BASE}/users/{mailbox}/mailFolders/{folder_id_or_wellknown}/messages"
        params = {
            "$filter": f"hasAttachments eq true and {date_filter}",
            "$top": "50",
            "$select": "id,subject,receivedDateTime,hasAttachments",
        }

        out: list[dict] = []

        while url:
            resp = self._request_with_retry("GET", url, params=params)
            data = resp.json()
            out.extend(data.get("value", []))

            url = data.get("@odata.nextLink")
            params = None

        return out

    def get_messages(self, mailbox: str) -> list[dict]:
        """
        Option 1: Fetch messages from Inbox AND all subfolders under Inbox.
        """
        folder_ids = self._get_inbox_descendant_folder_ids(mailbox)
        logger.info(f"Graph: {mailbox} | scanning Inbox + {len(folder_ids) - 1} subfolder(s)")

        all_messages: list[dict] = []
        seen_ids: set[str] = set()

        for fid in folder_ids:
            try:
                msgs = self._get_messages_in_folder(mailbox, fid)
            except Exception as exc:
                # If a single folder fails, log and continue so one bad folder doesn't kill the mailbox.
                logger.warning(f"Graph: {mailbox} | folder {fid} message query failed: {exc}")
                continue

            for m in msgs:
                mid = m.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    all_messages.append(m)

        # Optional: sort newest-first for nicer processing order
        try:
            all_messages.sort(key=lambda x: x.get("receivedDateTime") or "", reverse=True)
        except Exception:
            pass

        return all_messages

    def get_attachments(self, mailbox: str, message_id: str) -> list[dict]:
        url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
        resp = self._request_with_retry("GET", url)
        return resp.json().get("value", [])

    def add_category(self, mailbox: str, message_id: str) -> None:
        url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}"
        body = {"categories": ["RaivenSynced"]}
        self._request_with_retry("PATCH", url, json=body)

    def test_user(self, mailbox: str):
        url = f"{GRAPH_BASE}/users/{mailbox}?$select=id,userPrincipalName,mail"
        resp = self._request_with_retry("GET", url)
        return resp.status_code, resp.text
