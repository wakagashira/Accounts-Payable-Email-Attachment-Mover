from graph_client import get_messages, get_attachments, add_category
from invoice_processor import save_attachments, cleanup_file
from sftp_client import SFTPClient
from db import get_connection, is_processed_cur, mark_processed_cur, get_ap_mailboxes_cur
from config import (
    ENABLE_SUBJECT_FILTER,
    INVOICE_SUBJECT_KEYWORDS,
    LOOP_ENABLED,
    LOOP_SLEEP_SECONDS,
)
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def is_invoice(message):
    if not ENABLE_SUBJECT_FILTER:
        return True

    subject = (message.get("subject") or "").lower()
    return any(keyword in subject for keyword in INVOICE_SUBJECT_KEYWORDS)


def run_once():
    logger.info("Starting Raiven Invoice Sync cycle")

    # Lazy SFTP client (connects only when upload happens)
    sftp = SFTPClient()

    # One SQL connection per cycle (critical fix)
    with get_connection() as conn:
        cursor = conn.cursor()

        mailboxes = get_ap_mailboxes_cur(cursor)
        logger.info(f"Loaded {len(mailboxes)} mailbox(es) from SQL")

        total_uploaded = 0
        total_cleaned = 0
        total_marked = 0

        for cfg in mailboxes:
            mailbox = cfg["mailbox"]
            folder = cfg["folder"]

            logger.info(f"Processing mailbox: {mailbox}")

            try:
                messages = get_messages(mailbox)
            except Exception as exc:
                logger.exception(f"Failed to fetch messages for {mailbox}: {exc}")
                continue

            logger.info(f"Found {len(messages)} message(s)")

            for idx, msg in enumerate(messages, start=1):
                if idx % 250 == 0:
                    logger.info(f"{mailbox}: processed {idx}/{len(messages)} messages...")

                try:
                    message_id = msg["id"]

                    # Skip if already processed
                    if is_processed_cur(cursor, message_id):
                        continue

                    # Optional subject filter
                    if not is_invoice(msg):
                        continue

                    # Pull attachments
                    attachments = get_attachments(mailbox, message_id)
                    saved_files = save_attachments(attachments, folder)

                    # If nothing was saved (no allowed ext, no fileAttachment types, etc.)
                    # still mark processed so we don't repeatedly revisit the same message
                    if not saved_files:
                        mark_processed_cur(cursor, msg, folder)
                        conn.commit()
                        add_category(mailbox, message_id)
                        total_marked += 1
                        continue

                    # Upload + cleanup each file (cleanup = ARCHIVE or DELETE)
                    for file_path in saved_files:
                        # upload_file() handles remote-exists check and will rename if needed
                        remote_name = sftp.upload_file(file_path, folder)
                        total_uploaded += 1

                        # cleanup_file() handles POST_UPLOAD_ACTION (ARCHIVE or DELETE)
                        cleanup_file(file_path, folder)
                        total_cleaned += 1

                        logger.info(
                            f"Uploaded {file_path.name} -> {folder}/{remote_name}"
                        )

                    # Mark message processed only after successful upload+cleanup
                    mark_processed_cur(cursor, msg, folder)
                    conn.commit()
                    total_marked += 1

                    # Category for visibility (non-authoritative)
                    add_category(mailbox, message_id)

                except Exception as exc:
                    # Keep the loop alive even if one message fails
                    logger.exception(f"Error processing message in {mailbox}: {exc}")
                    continue

    # Close SFTP after all mailboxes (may not have connected at all)
    sftp.close()

    logger.info(
        f"Invoice Sync cycle complete | uploaded={total_uploaded} cleaned={total_cleaned} marked={total_marked}"
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
