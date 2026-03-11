"""Cloudinary helpers — upload, delete, and URL construction for raw files."""

import io
import cloudinary
import cloudinary.uploader
from app.core.config import settings


def configure_cloudinary():
    """Initialise the Cloudinary SDK from application settings."""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_to_cloudinary(file_bytes: bytes, public_id: str) -> dict:
    """Upload raw file bytes to Cloudinary with a deterministic *public_id*.

    Returns a dict with ``public_id``, ``secure_url`` and ``bytes``.
    """
    configure_cloudinary()
    result = cloudinary.uploader.upload(
        io.BytesIO(file_bytes),
        resource_type="raw",
        public_id=public_id,
        overwrite=True,
    )
    return {
        "public_id": result["public_id"],
        "secure_url": result["secure_url"],
        "bytes": result["bytes"],
    }


def delete_from_cloudinary(public_id: str) -> bool:
    """Delete a raw file from Cloudinary.  Returns *True* on success."""
    configure_cloudinary()
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="raw")
        return result.get("result") == "ok"
    except Exception:
        return False


def cloudinary_download_url(public_id: str) -> str:
    """Build a direct download URL for a raw Cloudinary asset."""
    return (
        f"https://res.cloudinary.com/"
        f"{settings.CLOUDINARY_CLOUD_NAME}/raw/upload/{public_id}"
    )
