"""
Production Diagnostics API
Temporarily add this to debug 500 errors.
DELETE AFTER DEBUGGING!
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
import os
import traceback
import smtplib

from app.core.database import get_db

router = APIRouter(prefix="/diag", tags=["diagnostics"])


@router.get("/env-check")
async def check_environment():
    """Check all required environment variables."""
    checks = {}

    required = [
        "SECRET_KEY", "DATABASE_URL",
        "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USERNAME", "EMAIL_PASSWORD",
    ]

    for var in required:
        value = os.environ.get(var)
        if value:
            if "PASSWORD" in var or "SECRET" in var or "KEY" in var or "URL" in var:
                checks[var] = f"SET ({len(value)} chars)"
            else:
                checks[var] = value[:20] + ("..." if len(value) > 20 else "")
        else:
            checks[var] = "NOT SET"

    return {"environment_variables": checks}


@router.get("/db-check")
async def check_database(db: AsyncSession = Depends(get_db)):
    """Check database connection and tables."""
    results: dict = {"connection": "unknown", "tables": {}}

    # Hardcoded table list — no dynamic SQL
    TABLE_QUERIES = {
        "users": text("SELECT COUNT(*) FROM users"),
        "email_verifications": text("SELECT COUNT(*) FROM email_verifications"),
        "refresh_tokens": text("SELECT COUNT(*) FROM refresh_tokens"),
        "datasets": text("SELECT COUNT(*) FROM datasets"),
        "subscriptions": text("SELECT COUNT(*) FROM subscriptions"),
    }

    try:
        await db.execute(text("SELECT 1"))
        results["connection"] = "OK"

        for table, query in TABLE_QUERIES.items():
            try:
                result = await db.execute(query)
                count = result.scalar()
                results["tables"][table] = f"EXISTS ({count} rows)"
            except Exception as e:
                await db.rollback()
                results["tables"][table] = f"ERROR: {str(e)[:80]}"

    except Exception as e:
        results["connection"] = f"FAILED: {str(e)[:120]}"

    return results


@router.get("/email-check")
async def check_email():
    """Test SMTP connection and authentication."""
    results: dict = {
        "config": {},
        "connection": "unknown",
        "authentication": "unknown",
        "error_details": None,
    }

    host = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    username = os.environ.get("EMAIL_USERNAME", "")
    password = os.environ.get("EMAIL_PASSWORD", "")

    results["config"] = {
        "host": host,
        "port": port,
        "username": username[:20] + "..." if username else "NOT SET",
        "password_length": len(password) if password else 0,
        "password_has_spaces": " " in password if password else False,
    }

    if not all([host, username, password]):
        results["error_details"] = "Missing email configuration"
        return results

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        results["connection"] = "Connected"

        try:
            server.ehlo()
            server.starttls()
            server.ehlo()
            results["tls"] = "TLS OK"
        except Exception as e:
            results["tls"] = f"TLS Failed: {str(e)[:80]}"
            server.quit()
            return results

        try:
            server.login(username, password)
            results["authentication"] = "Login successful"
        except smtplib.SMTPAuthenticationError as e:
            results["authentication"] = "AUTH FAILED"
            results["error_details"] = f"SMTPAuthenticationError: {str(e)[:120]}"
            results["hint"] = "For Gmail: Use App Password (16 chars, no spaces)"
        except Exception as e:
            results["authentication"] = f"Login error: {type(e).__name__}"
            results["error_details"] = str(e)[:120]
        finally:
            server.quit()

    except smtplib.SMTPConnectError as e:
        results["connection"] = "Connection refused"
        results["error_details"] = str(e)[:120]
    except Exception as e:
        results["connection"] = f"Failed: {type(e).__name__}"
        results["error_details"] = str(e)[:120]

    return results


@router.get("/auth-test")
async def test_auth_components(db: AsyncSession = Depends(get_db)):
    """Test all auth-related components."""
    results: dict = {"steps": {}, "errors": []}

    # 1: bcrypt
    try:
        import bcrypt
        test_pass = b"testpassword123"
        hashed = bcrypt.hashpw(test_pass, bcrypt.gensalt())
        verified = bcrypt.checkpw(test_pass, hashed)
        results["steps"]["1_bcrypt"] = f"OK (verified: {verified})"
    except Exception as e:
        results["steps"]["1_bcrypt"] = f"FAILED: {str(e)}"
        results["errors"].append(f"bcrypt: {str(e)}")

    # 2: JWT
    try:
        from jose import jwt
        secret = os.environ.get("SECRET_KEY", "test-secret")
        token = jwt.encode({"sub": "123"}, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        results["steps"]["2_jwt"] = f"OK (decoded sub: {decoded.get('sub')})"
    except Exception as e:
        results["steps"]["2_jwt"] = f"FAILED: {str(e)}"
        results["errors"].append(f"JWT: {str(e)}")

    # 3: OTP generation (returns tuple)
    try:
        from app.utils.otp import generate_otp, hash_otp
        otp = generate_otp()
        otp_hash, salt = hash_otp(otp)
        combined = f"{otp_hash}:{salt}"
        results["steps"]["3_otp"] = f"OK (otp_len: {len(otp)}, combined_len: {len(combined)})"
    except Exception as e:
        results["steps"]["3_otp"] = f"FAILED: {str(e)}"
        results["errors"].append(f"OTP: {str(e)}")
        results["steps"]["3_otp_traceback"] = traceback.format_exc()

    # 4: Password hashing
    try:
        from app.core.security import get_password_hash, verify_password
        pw_hash = get_password_hash("TestPassword123!")
        verified = verify_password("TestPassword123!", pw_hash)
        results["steps"]["4_password_hash"] = f"OK (verified: {verified})"
    except Exception as e:
        results["steps"]["4_password_hash"] = f"FAILED: {str(e)}"
        results["errors"].append(f"Password hash: {str(e)}")

    # 5: Email service
    try:
        from app.services.email_service import EmailService
        svc = EmailService()
        results["steps"]["5_email_service"] = (
            f"OK (host: {svc.host}, port: {svc.port}, "
            f"user: {svc.username[:15]}..., pw_len: {len(svc.password) if svc.password else 0})"
        )
    except Exception as e:
        results["steps"]["5_email_service"] = f"FAILED: {str(e)}"
        results["errors"].append(f"Email service: {str(e)}")
        results["steps"]["5_email_traceback"] = traceback.format_exc()

    # 6: User query
    try:
        from app.models.user import User
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        results["steps"]["6_user_query"] = f"OK (found user: {user is not None})"
    except Exception as e:
        results["steps"]["6_user_query"] = f"FAILED: {str(e)}"
        results["errors"].append(f"User query: {str(e)}")

    return results


@router.post("/simulate-signup")
async def simulate_signup(db: AsyncSession = Depends(get_db)):
    """Simulate signup flow step by step WITHOUT creating any records."""
    results: dict = {"steps": [], "error": None, "traceback": None}
    test_email = "test-simulation@example.com"

    try:
        # 1 — imports
        results["steps"].append("1  Importing dependencies...")
        from app.models.user import User
        from app.models.email_verification import EmailVerification
        from app.core.security import get_password_hash
        from app.utils.otp import generate_otp, hash_otp, get_otp_expiry
        from app.services.email_service import EmailService
        results["steps"].append("   All imports successful")

        # 2 — user lookup
        results["steps"].append("2  Checking if test user exists...")
        result = await db.execute(select(User).where(User.email == test_email))
        existing = result.scalar_one_or_none()
        results["steps"].append(f"   Query executed (exists: {existing is not None})")

        # 3 — OTP (returns tuple)
        results["steps"].append("3  Generating OTP...")
        otp = generate_otp()
        otp_hash, salt = hash_otp(otp)
        combined_hash = f"{otp_hash}:{salt}"
        results["steps"].append(f"   OTP length: {len(otp)}, Combined hash length: {len(combined_hash)}")

        # 4 — password hash
        results["steps"].append("4  Hashing password...")
        password_hash = get_password_hash("TestPassword123!")
        results["steps"].append(f"   Password hashed, length: {len(password_hash)}")

        # 5 — EmailVerification object (NOT saved)
        results["steps"].append("5  Creating EmailVerification object (not saving)...")
        verification = EmailVerification(
            email=test_email,
            otp_hash=combined_hash,
            temp_password_hash=password_hash,
            temp_full_name="Test User",
            expires_at=get_otp_expiry(),
            attempts=0,
            is_used=False,
        )
        results["steps"].append(f"   Object created (email={verification.email})")

        # 6 — email service init
        results["steps"].append("6  Initializing email service...")
        email_service = EmailService()
        results["steps"].append(f"   Host: {email_service.host}")
        results["steps"].append(f"   Port: {email_service.port}")
        results["steps"].append(f"   Username: {email_service.username}")
        results["steps"].append(f"   Password set: {bool(email_service.password)}")
        results["steps"].append(f"   Password length: {len(email_service.password) if email_service.password else 0}")

        # 7 — SMTP live test
        results["steps"].append("7  Testing SMTP connection...")
        try:
            with smtplib.SMTP(email_service.host, email_service.port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                results["steps"].append("   TLS connection established")
                server.login(email_service.username, email_service.password)
                results["steps"].append("   SMTP LOGIN SUCCESSFUL")
        except smtplib.SMTPAuthenticationError as e:
            error_msg = str(e)
            results["steps"].append(f"   SMTP AUTH FAILED: {error_msg[:120]}")
            results["error"] = "SMTP Authentication Failed"
            if "535" in error_msg or "Username and Password not accepted" in error_msg:
                results["steps"].append("")
                results["steps"].append("   FIX: EMAIL_PASSWORD is wrong.")
                results["steps"].append("   For Gmail use an App Password (16 chars, no spaces).")
                results["steps"].append("   https://myaccount.google.com/apppasswords")
            return results
        except Exception as e:
            results["steps"].append(f"   SMTP Error: {type(e).__name__}: {str(e)[:120]}")
            results["error"] = f"SMTP Error: {str(e)[:120]}"
            return results

        results["steps"].append("")
        results["steps"].append("ALL STEPS PASSED — signup should work.")

    except Exception as e:
        results["error"] = f"{type(e).__name__}: {str(e)}"
        results["traceback"] = traceback.format_exc()
        results["steps"].append(f"FAILED: {str(e)}")

    return results
