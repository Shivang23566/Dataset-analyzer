"""Auth endpoint tests."""
import pytest
from httpx import AsyncClient


# ── Signup ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_signup_success(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "test_signup_ok@example.com",
        "password": "StrongPass1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test_signup_ok@example.com"
    assert "id" in data


@pytest.mark.anyio
async def test_signup_weak_password(client: AsyncClient):
    """Password validation now lives in the Pydantic schema, so FastAPI
    returns 422 (Unprocessable Entity) when the password is too weak."""
    resp = await client.post("/auth/signup", json={
        "email": "weak@example.com",
        "password": "short",
    })
    assert resp.status_code == 422
    body = resp.json()
    assert any("password" in str(e).lower() for e in body.get("detail", []))


@pytest.mark.anyio
async def test_signup_duplicate_email(client: AsyncClient):
    email = "dup_test@example.com"
    await client.post("/auth/signup", json={"email": email, "password": "StrongPass1"})
    resp = await client.post("/auth/signup", json={"email": email, "password": "StrongPass1"})
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_signup_invalid_email(client: AsyncClient):
    resp = await client.post("/auth/signup", json={
        "email": "not-an-email",
        "password": "StrongPass1",
    })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_login_success(client: AsyncClient):
    email = "login_ok@example.com"
    password = "StrongPass1"
    await client.post("/auth/signup", json={"email": email, "password": password})
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
