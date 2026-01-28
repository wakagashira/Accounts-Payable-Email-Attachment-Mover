import os
from dotenv import load_dotenv

load_dotenv()

# =====================
# Azure / Microsoft Graph
# =====================
# NOTE: v3 multi-tenant mode reads tenant/app credentials from SQL (dbo.Tenants).
# These env vars are kept only for backwards compatibility / ad-hoc testing.
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# =====================
# Invoice logic
# =====================
OUTPUT_DIR = "output/invoices"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".xlsx")

ENABLE_SUBJECT_FILTER = os.getenv("ENABLE_SUBJECT_FILTER", "true").lower() == "true"
INVOICE_SUBJECT_KEYWORDS = [
    k.strip().lower()
    for k in os.getenv("INVOICE_SUBJECT_KEYWORDS", "invoice,bill,statement").split(",")
]

# =====================
# SQL Server
# =====================
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

SQL_TRUSTED_CONNECTION = (
    os.getenv("SQL_TRUSTED_CONNECTION", "false").lower() == "true"
)

# =====================
# Mail Sync Window
# =====================
MAIL_SYNC_TYPE = os.getenv("MAIL_SYNC_TYPE", "Days")  # Days | Span
MAIL_LOOKBACK_DAYS = int(os.getenv("MAIL_LOOKBACK_DAYS", "30"))

MAIL_FROM_DATE = os.getenv("MAIL_FROM_DATE")  # YYYY-MM-DD
MAIL_TO_DATE = os.getenv("MAIL_TO_DATE")      # YYYY-MM-DD

# =====================
# SFTP Configuration
# =====================
SFTP_ENABLED = os.getenv("SFTP_ENABLED", "false").lower() == "true"

SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PRIVATE_KEY_PATH = os.getenv("SFTP_PRIVATE_KEY_PATH")

SFTP_REMOTE_BASE_DIR = os.getenv("SFTP_REMOTE_BASE_DIR", "/incoming/invoices")

# =====================
# Post-upload behavior
# =====================
# What to do with files after successful SFTP upload:
# - ARCHIVE: move to Archived/<partner>/
# - DELETE: delete from output folder
POST_UPLOAD_ACTION = os.getenv("POST_UPLOAD_ACTION", "ARCHIVE").strip().upper()

# =====================
# Runtime behavior
# =====================
LOOP_ENABLED = os.getenv("LOOP_ENABLED", "false").lower() == "true"
LOOP_SLEEP_SECONDS = int(os.getenv("LOOP_SLEEP_SECONDS", "3600"))  # 1 hour
