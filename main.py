from graph_client import get_messages, get_attachments, add_category
from invoice_processor import save_attachments, archive_file
from sftp_client import SFTPClient
from db import is_processed, mark_processed, get_ap_mailboxes
from config import ENABLE_SUBJECT_FILTER, INVOICE_SUBJECT_KEYWORDS
import logging

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


def run():
    logger.info("Starting Raiven Invoice Sync")

    mailboxes = get_ap_mailboxes()
    logger.info(f"Loaded {len(mailboxes)} mailbox(es) from SQL")

    sftp = SFTPClient()
    sftp.connect()
    logger.info("SFTP connection established")

    try:
        for cfg in mailboxes:
            mailbox = cfg["mailbox"]
            folder = cfg["folder"]

            logger.info(f"Processing mailbox: {mailbox}")

            messages = get_messages(mailbox)
            logger.info(f"Found {len(messages)} message(s)")

            for msg in messages:
                message_id = msg["id"]
                subject = msg.get("subject", "")

                logger.info(f"Evaluating message {message_id}")

                if is_processed(message_id):
                    logger.info("Message already processed, skipping")
                    continue

                if not is_invoice(msg):
                    logger.info("Message does not match invoice filter, skipping")
                    continue

                logger.info("Fetching attachments")
                attachments = get_attachments(mailbox, message_id)

                logger.info("Saving attachments locally")
                saved_files = save_attachments(attachments, folder)

                for file_path in saved_files:
                    logger.info(f"Uploading file via SFTP: {file_path.name}")
                    sftp.upload_file(file_path, folder)

                    logger.info(f"Archiving file: {file_path.name}")
                    archive_file(file_path, folder)

                logger.info("Marking message as processed")
                mark_processed(msg)
                add_category(mailbox, message_id)

    finally:
        sftp.close()
        logger.info("SFTP connection closed")
        logger.info("Raiven Invoice Sync complete")


if __name__ == "__main__":
    run()
