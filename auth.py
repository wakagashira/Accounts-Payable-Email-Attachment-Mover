import msal

SCOPE = ["https://graph.microsoft.com/.default"]


def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Acquire an app-only access token for a specific tenant/app.

    Notes:
      - This is intentionally stateless (no disk cache). Callers that loop should cache per-tenant
        (e.g., GraphClient keeps a token in memory for the run).
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )

    token = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" not in token:
        raise RuntimeError(
            "Authentication failed:\n"
            f"tenant: {tenant_id}\n"
            f"error: {token.get('error')}\n"
            f"description: {token.get('error_description')}"
        )

    return token["access_token"]
