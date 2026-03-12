import random
import hashlib
import secrets
from datetime import datetime, timedelta, timezone


def generate_otp(length: int = 6) -> str:
    """Generate a secure random numeric OTP."""
    return ''.join([str(random.SystemRandom().randint(0, 9)) for _ in range(length)])


def hash_otp(otp: str, salt: str | None = None) -> tuple[str, str]:
    """Hash OTP with salt for secure storage. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{otp}{salt}".encode()).hexdigest()
    return hashed, salt


def verify_otp(otp: str, hashed_otp: str, salt: str) -> bool:
    """Verify OTP against stored hash (constant-time comparison)."""
    computed_hash = hashlib.sha256(f"{otp}{salt}".encode()).hexdigest()
    return secrets.compare_digest(computed_hash, hashed_otp)


def get_otp_expiry(minutes: int = 10) -> datetime:
    """Get OTP expiry timestamp."""
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def is_otp_expired(expires_at: datetime) -> bool:
    """Check if OTP has expired."""
    now = datetime.now(timezone.utc)
    # Handle naive datetimes (treat as UTC)
    if expires_at.tzinfo is None:
        return now.replace(tzinfo=None) > expires_at
    return now > expires_at
