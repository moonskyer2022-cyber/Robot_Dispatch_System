import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, Response, status

SESSION_COOKIE = "robot_dispatch_session"
SESSION_SECONDS = int(os.getenv("SESSION_SECONDS", "28800"))
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-session-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").lower()
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "60"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_login_failures_lock = Lock()


def validate_auth_config() -> None:
    if APP_ENV == "production":
        insecure = []
        if ADMIN_PASSWORD == "change-me":
            insecure.append("ADMIN_PASSWORD")
        if SESSION_SECRET == "change-this-session-secret" or len(SESSION_SECRET) < 32:
            insecure.append("SESSION_SECRET")
        if not COOKIE_SECURE:
            insecure.append("COOKIE_SECURE")
        if insecure:
            raise RuntimeError(
                f"Insecure production authentication settings: {', '.join(insecure)}"
            )


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session_token(username: str) -> str:
    payload = _encode(
        json.dumps(
            {"sub": username, "exp": int(time.time()) + SESSION_SECONDS},
            separators=(",", ":"),
        ).encode("utf-8")
    )
    signature = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload}.{_encode(signature)}"


def verify_session_token(token: str) -> str | None:
    try:
        payload, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            SESSION_SECRET.encode("utf-8"),
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(supplied_signature), expected_signature):
            return None
        data = json.loads(_decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data.get("sub")
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def authenticate(username: str, password: str) -> bool:
    return secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(
        password,
        ADMIN_PASSWORD,
    )


def login_allowed(client_key: str) -> bool:
    now = time.monotonic()
    with _login_failures_lock:
        failures = _login_failures[client_key]
        while failures and now - failures[0] >= LOGIN_WINDOW_SECONDS:
            failures.popleft()
        return len(failures) < LOGIN_MAX_FAILURES


def record_login_failure(client_key: str) -> None:
    now = time.monotonic()
    with _login_failures_lock:
        failures = _login_failures[client_key]
        while failures and now - failures[0] >= LOGIN_WINDOW_SECONDS:
            failures.popleft()
        failures.append(now)


def set_session_cookie(response: Response, username: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(username),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_user(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE)
    return verify_session_token(token) if token else None


def require_authenticated(request: Request) -> str:
    username = current_user(request)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return username
