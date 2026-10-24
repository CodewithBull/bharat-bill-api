"""API-key auth.

Send the key on every request (except /health and the docs) as:

    X-API-Key: <your key>

The expected key comes from the BHARAT_BILL_API_KEY environment variable.
For local development it defaults to ``dev-key-change-me`` — change it in
production, obviously.
"""
from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

DEFAULT_DEV_KEY = "dev-key-change-me"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    expected = os.getenv("BHARAT_BILL_API_KEY", DEFAULT_DEV_KEY)
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Send it as the X-API-Key header.",
        )
    return api_key
