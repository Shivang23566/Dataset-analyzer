"""Payment and coupon tests with mocked Razorpay."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


# ── Payment: unauthenticated ──────────────────────────────────

@pytest.mark.anyio
async def test_create_order_unauthenticated(client: AsyncClient):
    """POST /payments/create-order without auth → 401."""
    resp = await client.post("/payments/create-order")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_get_payment_status_unauthenticated(client: AsyncClient):
    """GET /payments/status without auth → 401."""
    resp = await client.get("/payments/status")
    assert resp.status_code == 401


# ── Payment: authenticated + mocked Razorpay ──────────────────

@pytest.mark.anyio
async def test_create_order_with_auth_mocked(client: AsyncClient, auth_headers: dict):
    """POST /payments/create-order with auth and mocked Razorpay → 200."""
    mock_order = {"id": "order_test123", "amount": 21900, "currency": "INR"}
    with patch("app.api.payments.razorpay_client") as mock_client:
        mock_client.order.create.return_value = mock_order
        resp = await client.post("/payments/create-order", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"] == "order_test123"
    assert data["currency"] == "INR"
    assert "razorpay_key_id" in data


@pytest.mark.anyio
async def test_create_order_razorpay_failure(client: AsyncClient, auth_headers: dict):
    """POST /payments/create-order when Razorpay raises → 500."""
    with patch("app.api.payments.razorpay_client") as mock_client:
        mock_client.order.create.side_effect = Exception("Razorpay error")
        resp = await client.post("/payments/create-order", headers=auth_headers)
    assert resp.status_code == 500


# ── Coupon: unauthenticated ───────────────────────────────────

@pytest.mark.anyio
async def test_apply_coupon_unauthenticated(client: AsyncClient):
    """POST /coupons/apply without auth → 401."""
    resp = await client.post("/coupons/apply", json={"code": "TESTCODE"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_get_coupon_status_unauthenticated(client: AsyncClient):
    """GET /coupons/status without auth → 401."""
    resp = await client.get("/coupons/status")
    assert resp.status_code == 401


# ── Coupon: validation errors ─────────────────────────────────

@pytest.mark.anyio
async def test_apply_coupon_invalid_characters(client: AsyncClient, auth_headers: dict):
    """Coupon codes with special chars fail Pydantic validation → 422."""
    resp = await client.post(
        "/coupons/apply",
        json={"code": "bad code!"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_apply_coupon_empty_code(client: AsyncClient, auth_headers: dict):
    """Empty coupon code → 422."""
    resp = await client.post(
        "/coupons/apply",
        json={"code": "   "},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_apply_coupon_too_long(client: AsyncClient, auth_headers: dict):
    """Coupon code longer than 50 chars → 422."""
    resp = await client.post(
        "/coupons/apply",
        json={"code": "A" * 51},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── Coupon: not found ─────────────────────────────────────────

@pytest.mark.anyio
async def test_apply_invalid_coupon(client: AsyncClient, auth_headers: dict):
    """POST /coupons/apply with non-existent code → 400."""
    resp = await client.post(
        "/coupons/apply",
        json={"code": "INVALID123"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "detail" in body


# ── Payment status: authenticated ────────────────────────────

@pytest.mark.anyio
async def test_get_payment_status_authenticated(client: AsyncClient, auth_headers: dict):
    """GET /payments/status with auth → 200 with plan info."""
    resp = await client.get("/payments/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert "status" in data
