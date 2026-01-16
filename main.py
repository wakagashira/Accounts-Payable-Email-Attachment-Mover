from graph_client import get_messages, get_attachments, add_category
from invoice_processor import save_attachments, archive_file
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

    sftp = SFTPClient()  # lazy connect (connects only when upload happens)

    # One SQL connection per cycle (critical fix)
    with get_connection() as conn:
        cursor = conn.cursor()

        mailboxes = get_ap_mailboxes_cur(cursor)
        logger.info(f"Loaded {len(mailboxes)} mailbox(es) from SQL")

        total_uploaded = 0
        total_archived = 0
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

                    if is_processed_cur(cursor, message_id):
                        continue

                    if not is_invoice(msg):
                        continue

                    attachments = get_attachments(mailbox, message_id)
                    saved_files = save_attachments(attachments, folder)

                    # If nothing saved (no allowed extensions, no fileAttachment types, etc.)
                    if not saved_files:
                        mark_processed_cur(cursor, msg, folder)
                        conn.commit()
                        add_category(mailbox, message_id)
                        total_marked += 1
                        continue

                    # Upload + archive each file
                    for file_path in saved_files:
                        sftp.upload_file(file_path, folder)
                        total_uploaded += 1

                        archive_file(file_path, folder)
                        total_archived += 1

                    # Mark processed only after successful upload+archive
                    mark_processed_cur(cursor, msg, folder)
                    conn.commit()
                    total_marked += 1

                    add_category(mailbox, message_id)

                except Exception as exc:
                    # Keep the loop alive even if one message fails
                    logger.exception(f"Error processing message in {mailbox}: {exc}")
                    continue

    # Close SFTP after all mailboxes (may not have connected at all)
    sftp.close()

    logger.info(
        f"Invoice Sync cycle complete | uploaded={total_uploaded} archived={total_archived} marked={total_marked}"
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
