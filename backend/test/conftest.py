"""Shared fixtures for backend tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy import select


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Unauthenticated test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _ensure_test_user(email: str, password: str):
    """Create a test user directly in the DB if they don't exist."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                is_active=True,
            )
            session.add(user)
            await session.commit()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user and return Authorization headers with a valid token."""
    email = "fixture_user@example.com"
    password = "FixturePass1"

    # Create user directly in DB (legacy /signup is disabled)
    await _ensure_test_user(email, password)

    # Log in
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
