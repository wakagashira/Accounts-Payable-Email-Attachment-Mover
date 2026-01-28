import pyodbc
from config import (
    SQL_SERVER,
    SQL_DATABASE,
    SQL_USERNAME,
    SQL_PASSWORD,
    SQL_TRUSTED_CONNECTION,
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


def mark_processed_cur(cursor, message, folder: str):
    """Records a processed email in dbo.ProcessedEmails."""
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
        folder,
    )


def get_active_tenants_cur(cursor):
    """Return active tenants from dbo.Tenants.

    Expected schema:
      TenantID (uniqueidentifier), Name, Active (bit), Client_id, Client_secret
    """
    cursor.execute(
        """
        SELECT TenantID, Name, Client_id, Client_secret
        FROM dbo.Tenants
        WHERE Active = 1
        ORDER BY Name
        """
    )
    rows = cursor.fetchall()

    return [
        {
            "tenant_id": str(row.TenantID).strip(),
            "tenant_name": row.Name.strip(),
            "client_id": row.Client_id.strip(),
            "client_secret": row.Client_secret,
        }
        for row in rows
    ]


def get_ap_mailboxes_for_tenant_cur(cursor, tenant_name: str):
    """Return mailboxes for a tenant from dbo.APEmails."""
    cursor.execute(
        """
        SELECT Email, Folder
        FROM dbo.APEmails
        WHERE TenantName = ?
        ORDER BY Email
        """,
        tenant_name,
    )
    rows = cursor.fetchall()
    return [
        {
            "mailbox": row.Email.strip(),
            "folder": row.Folder.strip(),
        }
        for row in rows
    ]


# -------------------------
# Backwards-compatible wrappers
# -------------------------

def is_processed(message_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        return is_processed_cur(cur, message_id)


def mark_processed(message, folder: str):
    with get_connection() as conn:
        cur = conn.cursor()
        mark_processed_cur(cur, message, folder)
        conn.commit()
