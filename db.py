import pyodbc
from config import (
    SQL_SERVER,
    SQL_DATABASE,
    SQL_USERNAME,
    SQL_PASSWORD,
    SQL_TRUSTED_CONNECTION
)


def get_connection():
    if SQL_TRUSTED_CONNECTION:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
        )
    return pyodbc.connect(conn_str)


# -------------------------
# Cursor-based helpers (preferred)
# -------------------------

def is_processed_cur(cursor, message_id: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM dbo.ProcessedEmails WHERE MessageId = ?",
        message_id
    )
    return cursor.fetchone() is not None


def get_ap_mailboxes_cur(cursor):
    """
    Returns a list of mailboxes to sync from dbo.APEmails.
    Uses an existing cursor (no per-call connections).
    """
    cursor.execute("""
        SELECT Email, Folder
        FROM dbo.APEmails
    """)
    rows = cursor.fetchall()

    return [
        {
            "mailbox": row.Email.strip(),
            "folder": row.Folder.strip()
        }
        for row in rows
    ]


def mark_processed_cur(cursor, message, folder: str):
    """
    Records a processed email in dbo.ProcessedEmails.
    """
    cursor.execute(
        """
        INSERT INTO dbo.ProcessedEmails
            (MessageId, Subject, Sender, Email_Created_Date, Folder)
        VALUES (?, ?, ?, ?, ?)
        """,
        message["id"],
        message.get("subject"),
        message.get("from", {}).get("emailAddress", {}).get("address"),
        message.get("receivedDateTime"),
        folder
    )


# -------------------------
# Backwards-compatible wrappers
# -------------------------

def is_processed(message_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        return is_processed_cur(cur, message_id)


def get_ap_mailboxes():
    with get_connection() as conn:
        cur = conn.cursor()
        return get_ap_mailboxes_cur(cur)


def mark_processed(message, folder: str):
    with get_connection() as conn:
        cur = conn.cursor()
        mark_processed_cur(cur, message, folder)
        conn.commit()
