from graph_client import get_messages, get_attachments, add_category
from invoice_processor import save_attachments
from db import is_processed, mark_processed, get_ap_mailboxes
from config import ENABLE_SUBJECT_FILTER, INVOICE_SUBJECT_KEYWORDS


def is_invoice(message):
    if not ENABLE_SUBJECT_FILTER:
        return True

    subject = (message.get("subject") or "").lower()
    return any(keyword in subject for keyword in INVOICE_SUBJECT_KEYWORDS)


def run():
    mailboxes = get_ap_mailboxes()

    for cfg in mailboxes:
        mailbox = cfg["mailbox"]
        folder = cfg["folder"]

        messages = get_messages(mailbox)

        for msg in messages:
            message_id = msg["id"]

            # Skip if already processed
            if is_processed(message_id):
                continue

            # Skip if subject filter enabled and not matched
            if not is_invoice(msg):
                continue

            # 1. Save attachments to mailbox-specific folder
            attachments = get_attachments(mailbox, message_id)
            save_attachments(attachments, folder)

            # 2. Record processed message
            mark_processed(msg)

            # 3. Tag message in Outlook
            add_category(mailbox, message_id)


if __name__ == "__main__":
    run()
