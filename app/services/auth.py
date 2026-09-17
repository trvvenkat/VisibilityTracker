import base64
import hashlib
import hmac
import json
import time
from fastapi import HTTPException, Request, status
from app.config import settings


def create_session_token(username: str) -> str:
    """Creates a cryptographically signed session token with an expiration timestamp."""
    exp = int(time.time()) + settings.SESSION_MAX_AGE_SECS
    payload = {"u": username, "exp": exp}
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str | None) -> str | None:
    """Verifies the signature and expiration of a session token, returning the username if valid."""
    if not token or "." not in token:
        return None

    try:
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add base64 padding if needed
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += "=" * padding

        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)

        if not isinstance(payload, dict):
            return None

        if payload.get("exp", 0) < time.time():
            return None

        return payload.get("u")
    except Exception:
        return None


def check_credentials(username: str, password: str) -> bool:
    """Validates user credentials against configured authentication values."""
    user_match = hmac.compare_digest(username.strip(), settings.AUTH_USERNAME)
    pass_match = hmac.compare_digest(password, settings.AUTH_PASSWORD)
    return user_match and pass_match


def get_current_user(request: Request) -> str | None:
    """Extracts and verifies the current session user from cookies."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    return verify_session_token(token)


def require_authenticated_user(request: Request) -> str:
    """FastAPI dependency to enforce authentication on protected endpoints."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return user
