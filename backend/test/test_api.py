"""Foundational tests for Dataset Analyzer backend."""
import pytest
from httpx import AsyncClient


# ── Health ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Forgot password: no email enumeration ─────────────────────

@pytest.mark.anyio
async def test_forgot_password_no_enumeration(client: AsyncClient):
    resp = await client.post("/auth/forgot-password", params={"email": "nonexistent@example.com"})
    assert resp.status_code == 200
    assert "recovery link" in resp.json()["message"].lower() or "sent" in resp.json()["message"].lower()
