"""Auth endpoint tests."""
import pytest
from httpx import AsyncClient


# ── Signup ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_signup_legacy_endpoint_blocked(client: AsyncClient):
    """Legacy /signup endpoint returns 410 Gone (disabled in favor of OTP flow)."""
    resp = await client.post("/auth/signup", json={
        "email": "test_signup_ok@example.com",
        "password": "StrongPass1",
    })
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_signup_weak_password_blocked(client: AsyncClient):
    """Legacy /signup returns 410 Gone regardless of payload."""
    resp = await client.post("/auth/signup", json={
        "email": "weak@example.com",
        "password": "short",
    })
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_signup_duplicate_blocked(client: AsyncClient):
    """Legacy /signup returns 410 Gone for all requests."""
    email = "dup_test@example.com"
    resp = await client.post("/auth/signup", json={"email": email, "password": "StrongPass1"})
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_signup_invalid_email_blocked(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "not-an-email",
        "password": "StrongPass1",
    })
    assert resp.status_code == 410


# ── Login ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_login_success(client: AsyncClient):
    email = "login_ok@example.com"
    password = "StrongPass1"
    from test.conftest import _ensure_test_user
    await _ensure_test_user(email, password)
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_login_wrong_credentials(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "nobody@example.com",
        "password": "WrongPass1",
    })
    assert resp.status_code == 400
