import hmac

from fastapi import Header, HTTPException

from .config import settings


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), settings.agent_api_key.encode()):
        raise HTTPException(401, "Invalid or missing API key")
    return x_api_key
