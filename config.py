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
# Invoice logic
# =====================
OUTPUT_DIR = "output/invoices"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".xlsx")
SEARCH_KEYWORDS = ["invoice", "bill", "statement"]

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
