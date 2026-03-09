"""Shared fixtures for backend tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Unauthenticated test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user and return Authorization headers with a valid token."""
    email = "fixture_user@example.com"
    password = "FixturePass1"

    # Sign up (ignore if already exists)
    await client.post("/auth/signup", json={"email": email, "password": password})

    # Log in
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
