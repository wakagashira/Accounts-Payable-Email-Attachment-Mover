import os
from dotenv import load_dotenv

load_dotenv()

# =====================
# Azure / Mailbox
# =====================
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
MAILBOX = os.getenv("MAILBOX")

# =====================
# File handling
# =====================
OUTPUT_DIR = "output/invoices"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".xlsx")

# =====================
# Subject filtering (CONFIGURABLE)
# =====================
ENABLE_SUBJECT_FILTER = os.getenv(
    "ENABLE_SUBJECT_FILTER", "true"
).lower() == "true"

INVOICE_SUBJECT_KEYWORDS = [
    kw.strip().lower()
    for kw in os.getenv(
        "INVOICE_SUBJECT_KEYWORDS", "invoice,bill,statement"
    ).split(",")
    if kw.strip()
]

# =====================
# SQL Server (Processed Emails)
# =====================
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# Use "true" / "false" in .env
SQL_TRUSTED_CONNECTION = os.getenv(
    "SQL_TRUSTED_CONNECTION", "false"
).lower() == "true"

# =====================
# Mail sync range
# =====================
MAIL_LOOKBACK_DAYS = int(os.getenv("MAIL_LOOKBACK_DAYS", "30"))
