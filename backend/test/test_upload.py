"""Upload endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_upload_rejects_without_auth(client: AsyncClient):
    resp = await client.post("/api/upload/", files={
        "file": ("test.csv", b"a,b\n1,2\n", "text/csv"),
    })
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_upload_rejects_bad_extension(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/upload/",
        headers=auth_headers,
        files={"file": ("malware.exe", b"MZ...", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "file type" in resp.json()["detail"].lower() or "allowed" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_upload_csv_success(client: AsyncClient, auth_headers: dict):
    csv_bytes = b"name,age\nAlice,30\nBob,25\n"
    resp = await client.post(
        "/api/upload/",
        headers=auth_headers,
        files={"file": ("people.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data or "file" in str(data).lower()
