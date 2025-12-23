import os
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
MAILBOX = os.getenv("MAILBOX")

OUTPUT_DIR = "output/invoices"
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".xlsx")
SEARCH_KEYWORDS = ["invoice", "bill", "statement"]