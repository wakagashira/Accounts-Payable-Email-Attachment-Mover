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

def is_processed(message_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM dbo.ProcessedEmails WHERE MessageId = ?",
            message_id
        )
        return cursor.fetchone() is not None
def get_ap_mailboxes():
    """
    Returns a list of mailboxes to sync from RaivenSync.dbo.APEmails.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
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

def mark_processed(message):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dbo.ProcessedEmails
            (MessageId, Subject, Sender, ReceivedDateTime)
            VALUES (?, ?, ?, ?)
        """,
            message["id"],
            message.get("subject"),
            message.get("from", {}).get("emailAddress", {}).get("address"),
            message.get("receivedDateTime")
        )
        conn.commit()
