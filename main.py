from graph_client import get_messages, get_attachments, add_category
from invoice_processor import save_attachments
from db import is_processed, mark_processed
from config import MAILBOX, SEARCH_KEYWORDS


def is_invoice(message):
    subject = (message.get("subject") or "").lower()
    return any(keyword in subject for keyword in SEARCH_KEYWORDS)


def run():
    messages = get_messages(MAILBOX)

    for msg in messages:
        message_id = msg["id"]

        # Skip if already processed (SQL Server is source of truth)
        if is_processed(message_id):
            continue

        # Skip if not invoice-like
        if not is_invoice(msg):
            continue

        # 1. Save attachments locally
        attachments = get_attachments(MAILBOX, message_id)
        save_attachments(attachments)

        # 2. Record message as processed in SQL Server
        mark_processed(msg)

        # 3. Apply Outlook category (non-authoritative, for visibility)
        add_category(MAILBOX, message_id)


if __name__ == "__main__":
    run()
