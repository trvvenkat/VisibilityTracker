import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.auth import (
    check_credentials,
    create_session_token,
    verify_session_token,
)


def test_session_token_creation_and_verification():
    token = create_session_token("admin")
    assert token is not None
    assert "." in token

    username = verify_session_token(token)
    assert username == "admin"


def test_invalid_and_tampered_session_token():
    token = create_session_token("admin")
    # Tamper with signature
    tampered = token[:-4] + "abcd"
    assert verify_session_token(tampered) is None

    assert verify_session_token("invalid.token") is None
    assert verify_session_token("") is None
    assert verify_session_token(None) is None


def test_check_credentials():
    assert check_credentials("admin", "tracker@2026") is True
    assert check_credentials("admin", "wrongpassword") is False
    assert check_credentials("nonexistent", "tracker@2026") is False


@pytest.mark.asyncio
async def test_unauthenticated_redirect_on_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/", follow_redirects=False)
        assert res.status_code == 303
        assert res.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_login_flow_and_authenticated_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login page GET
        login_page_res = await client.get("/login")
        assert login_page_res.status_code == 200
        assert "Visibility Tracker" in login_page_res.text

        # 2. Login POST invalid
        bad_login = await client.post(
            "/login",
            data={"username": "admin", "password": "wrong_password"},
        )
        assert bad_login.status_code == 401
        assert "Invalid username or password" in bad_login.text

        # 3. Login POST valid
        good_login = await client.post(
            "/login",
            data={"username": "admin", "password": "tracker@2026"},
            follow_redirects=False,
        )
        assert good_login.status_code == 303
        assert good_login.headers["location"] == "/"
        assert settings.SESSION_COOKIE_NAME in good_login.cookies

        # Extract session cookie
        session_cookie = good_login.cookies[settings.SESSION_COOKIE_NAME]

        # 4. Access root with cookie
        client.cookies.set(settings.SESSION_COOKIE_NAME, session_cookie)
        dashboard_res = await client.get("/")
        assert dashboard_res.status_code == 200
        assert "Runs History & Reports" in dashboard_res.text
        assert "admin" in dashboard_res.text

        # 5. Access /api/auth/me
        me_res = await client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "admin"

        # 6. Logout
        logout_res = await client.get("/logout", follow_redirects=False)
        assert logout_res.status_code == 303
        assert logout_res.headers["location"] == "/login"
