import msal
from config import TENANT_ID, CLIENT_ID, CLIENT_SECRET

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

def get_access_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    token = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" not in token:
        raise RuntimeError(
            f"Authentication failed:\n"
            f"error: {token.get('error')}\n"
            f"description: {token.get('error_description')}"
        )

    return token["access_token"]
