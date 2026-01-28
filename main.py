import logging
import sys
import time
import json

from graph_client import GraphClient
from invoice_processor import save_attachments, cleanup_file
from sftp_client import SFTPClient
from db import (
    get_connection,
    is_processed_cur,
    mark_processed_cur,
    get_active_tenants_cur,
    get_ap_mailboxes_for_tenant_cur,
)
from config import (
    ENABLE_SUBJECT_FILTER,
    INVOICE_SUBJECT_KEYWORDS,
    LOOP_ENABLED,
    LOOP_SLEEP_SECONDS,
)

# ------------------------------------------------------------------
# 🔧 DETERMINISTIC CONSOLE LOGGING
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("RaivenSync")


def is_invoice(message: dict) -> bool:
    if not ENABLE_SUBJECT_FILTER:
        return True

    subject = (message.get("subject") or "").lower()
    return any(k.lower() in subject for k in INVOICE_SUBJECT_KEYWORDS)


def _log_graph_http_error(context: str, exc: Exception) -> None:
    """
    Attempts to extract useful diagnostic info from requests HTTPError / Response
    and logs a friendly, actionable message.
    """
    try:
        resp = getattr(exc, "response", None)
        if resp is None:
            return

        status = getattr(resp, "status_code", None)
        body_text = ""
        try:
            body_text = resp.text or ""
        except Exception:
            body_text = ""

        snippet = body_text[:500].replace("\n", " ").strip()

        if status == 404:
            logger.error(
                f"{context}: Graph returned 404 Not Found. This usually means one of:\n"
                "  1) The mailbox/user does not exist in this tenant\n"
                "  2) The user exists but has no Exchange Online mailbox provisioned\n"
                "  3) The mailbox belongs to a different tenant than the one you're querying\n"
                "Check in the target tenant:\n"
                "  - Entra ID Users: does the mailbox exist?\n"
                "  - Exchange admin center: does it appear under Mailboxes?\n"
                f"Response snippet: {snippet}"
            )
        elif status in (401, 403):
            logger.error(
                f"{context}: Graph returned {status}. Likely auth/consent/permissions issue.\n"
                f"Response snippet: {snippet}"
            )
        elif status:
            logger.error(
                f"{context}: Graph HTTP error {status}. Response snippet: {snippet}"
            )

    except Exception:
        return


def run_once():
    logger.info("Starting Raiven Invoice Sync cycle")

    sftp = SFTPClient()

    with get_connection() as conn:
        cursor = conn.cursor()

        tenants = get_active_tenants_cur(cursor)
        logger.info(f"Loaded {len(tenants)} active tenant(s) from SQL")

        total_uploaded = 0
        total_cleaned = 0
        total_marked = 0

        for t in tenants:
            tenant_name = t["tenant_name"]
            logger.info(f"Processing tenant: {tenant_name}")

            graph = GraphClient(
                tenant_id=t["tenant_id"],
                client_id=t["client_id"],
                client_secret=t["client_secret"],
            )

            mailboxes = get_ap_mailboxes_for_tenant_cur(cursor, tenant_name)
            logger.info(f"{tenant_name}: Loaded {len(mailboxes)} mailbox(es)")

            for cfg in mailboxes:
                mailbox = cfg["mailbox"]
                folder = cfg["folder"]

                logger.info(f"{tenant_name} | Processing mailbox: {mailbox}")

                try:
                    messages = graph.get_messages(mailbox)
                except Exception as exc:
                    _log_graph_http_error(
                        context=f"{tenant_name} | Failed to fetch messages for {mailbox}",
                        exc=exc,
                    )
                    logger.exception(
                        f"{tenant_name} | Failed to fetch messages for {mailbox}"
                    )
                    continue

                logger.info(f"{tenant_name} | {mailbox}: Found {len(messages)} message(s)")

                for msg in messages:
                    try:
                        message_id = msg["id"]

                        if is_processed_cur(cursor, message_id):
                            continue

                        if not is_invoice(msg):
                            continue

                        attachments = graph.get_attachments(mailbox, message_id)
                        saved_files = save_attachments(attachments, folder)

                        if not saved_files:
                            mark_processed_cur(cursor, msg, folder)
                            conn.commit()
                            graph.add_category(mailbox, message_id)
                            total_marked += 1
                            continue

                        for file_path in saved_files:
                            remote_name = sftp.upload_file(file_path, folder)
                            total_uploaded += 1

                            cleanup_file(file_path, folder)
                            total_cleaned += 1

                            logger.info(
                                f"{tenant_name} | Uploaded {file_path.name} -> {remote_name}"
                            )

                        mark_processed_cur(cursor, msg, folder)
                        conn.commit()
                        total_marked += 1

                        graph.add_category(mailbox, message_id)

                    except Exception as exc:
                        logger.exception(
                            f"{tenant_name} | Error processing message in {mailbox}: {exc}"
                        )

    sftp.close()

    logger.info(
        f"Invoice Sync cycle complete | "
        f"uploaded={total_uploaded} cleaned={total_cleaned} marked={total_marked}"
    )


def run():
    if not LOOP_ENABLED:
        run_once()
        return

    logger.info("Loop mode enabled — running on interval")
    try:
        while True:
            run_once()
            logger.info(f"Sleeping for {LOOP_SLEEP_SECONDS} seconds")
            time.sleep(LOOP_SLEEP_SECONDS)
    except KeyboardInterrupt:
        logger.info("Loop stopped by user (Ctrl+C)")


if __name__ == "__main__":
    run()
