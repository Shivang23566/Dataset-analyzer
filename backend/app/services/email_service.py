"""
Email Service using Resend API
Works on Render free tier (HTTPS instead of blocked SMTP)

Setup:
1. Set RESEND_API_KEY in Render environment
2. Verify domain in Resend to send to any email
3. Update EMAIL_FROM to your verified domain
"""

import os
import logging
import sys
from typing import Optional

# Configure logger to write to stdout for Render logs
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure logs go to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Try import httpx
try:
    import httpx
    HTTPX_AVAILABLE = True
    print("✅ httpx is available", flush=True)
except ImportError:
    HTTPX_AVAILABLE = False
    print("❌ httpx is NOT installed - emails will fail!", flush=True)


class EmailService:
    """Email service using Resend HTTP API."""

    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY", "")
        self.from_email = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
        self.from_name = os.environ.get("EMAIL_FROM_NAME", "DataLens")
        self.api_url = "https://api.resend.com/emails"

        # Legacy compatibility attributes
        self.host = "api.resend.com"
        self.port = 443
        self.username = self.from_email
        self.password = self.api_key

        # Log initialization
        print(f"=" * 60, flush=True)
        print(f"📧 EMAIL SERVICE INITIALIZED", flush=True)
        print(f"   API Key Set: {'✅ Yes (' + self.api_key[:10] + '...)' if self.api_key else '❌ No'}", flush=True)
        print(f"   From Email: {self.from_email}", flush=True)
        print(f"   From Name: {self.from_name}", flush=True)
        print(f"   HTTPX Available: {'✅ Yes' if HTTPX_AVAILABLE else '❌ No'}", flush=True)
        print(f"=" * 60, flush=True)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Resend API."""

        print(f"\n{'=' * 60}", flush=True)
        print(f"📤 SEND EMAIL CALLED", flush=True)
        print(f"   To: {to_email}", flush=True)
        print(f"   Subject: {subject}", flush=True)
        print(f"   From: {self.from_name} <{self.from_email}>", flush=True)
        print(f"{'=' * 60}\n", flush=True)

        # Check prerequisites
        if not self.api_key:
            print("❌ ERROR: RESEND_API_KEY is not set!", flush=True)
            logger.error("RESEND_API_KEY environment variable is not set")
            return False

        if not HTTPX_AVAILABLE:
            print("❌ ERROR: httpx is not installed!", flush=True)
            logger.error("httpx package is not installed")
            return False

        # Prepare request
        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        if text_content:
            payload["text"] = text_content

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Send request
        try:
            print(f"📡 Sending request to Resend API...", flush=True)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                print(f"📡 Response Status: {response.status_code}", flush=True)
                print(f"📡 Response Body: {response.text}", flush=True)

                if response.status_code == 200:
                    result = response.json()
                    email_id = result.get('id', 'unknown')
                    print(f"✅ EMAIL SENT SUCCESSFULLY!", flush=True)
                    print(f"   Resend Email ID: {email_id}", flush=True)
                    logger.info(f"Email sent to {to_email}, ID: {email_id}")
                    return True
                else:
                    print(f"❌ EMAIL SEND FAILED!", flush=True)
                    print(f"   Status: {response.status_code}", flush=True)
                    print(f"   Error: {response.text}", flush=True)
                    logger.error(f"Resend API error: {response.status_code} - {response.text}")
                    return False

        except httpx.TimeoutException as e:
            print(f"❌ TIMEOUT ERROR: {e}", flush=True)
            logger.error(f"Email timeout: {e}")
            return False
        except httpx.ConnectError as e:
            print(f"❌ CONNECTION ERROR: {e}", flush=True)
            logger.error(f"Email connection error: {e}")
            return False
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}", flush=True)
            logger.error(f"Email error: {type(e).__name__}: {e}")
            return False

    async def send_otp_email(self, email: str, otp: str) -> bool:
        """Send OTP verification email."""

        # CRITICAL: Always log OTP so we can see it in Render logs
        print(f"\n{'#' * 60}", flush=True)
        print(f"#", flush=True)
        print(f"#  🔐 OTP VERIFICATION EMAIL", flush=True)
        print(f"#", flush=True)
        print(f"#  To: {email}", flush=True)
        print(f"#  OTP Code: {otp}", flush=True)
        print(f"#", flush=True)
        print(f"{'#' * 60}\n", flush=True)

        logger.info(f"OTP for {email}: {otp}")

        subject = f"Your DataLens Verification Code: {otp}"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); padding: 32px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">
                🔬 DataLens
            </h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">
                AI-Powered Data Analysis
            </p>
        </div>

        <div style="background: white; padding: 40px 32px; border-radius: 0 0 16px 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <h2 style="color: #111827; margin: 0 0 16px 0; font-size: 22px;">
                Verify Your Email
            </h2>

            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 32px 0;">
                Enter this code to complete your registration:
            </p>

            <div style="background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border: 2px dashed #6366f1; border-radius: 12px; padding: 28px; text-align: center; margin: 0 0 32px 0;">
                <span style="font-family: 'SF Mono', 'Courier New', monospace; font-size: 40px; font-weight: 700; letter-spacing: 10px; color: #4338ca;">
                    {otp}
                </span>
            </div>

            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 0 0 24px 0;">
                <p style="color: #92400e; font-size: 14px; margin: 0;">
                    ⏱️ This code expires in <strong>10 minutes</strong>
                </p>
            </div>

            <p style="color: #6b7280; font-size: 14px; margin: 0;">
                If you didn't create an account, please ignore this email.
            </p>
        </div>

        <div style="text-align: center; padding: 24px;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                © 2024 DataLens
            </p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"Your DataLens verification code is: {otp}\n\nThis code expires in 10 minutes."

        result = await self.send_email(email, subject, html_content, text_content)

        print(f"\n📧 OTP Email Result: {'✅ Sent' if result else '❌ Failed'}\n", flush=True)

        return result

    def send_verification_email(self, to_email: str, otp: str, full_name: str | None = None) -> bool:
        """
        Sync wrapper for backwards compatibility with BackgroundTasks.
        WARNING: This blocks - prefer send_otp_email for async code.
        """
        import asyncio

        print(f"\n🔄 send_verification_email (sync wrapper) called", flush=True)
        print(f"   to_email: {to_email}", flush=True)
        print(f"   otp: {otp}", flush=True)
        print(f"   full_name: {full_name}", flush=True)

        try:
            # Try to get existing event loop
            try:
                loop = asyncio.get_running_loop()
                print(f"   Running loop detected - using run_coroutine_threadsafe", flush=True)
                # We're in an async context - need to run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.send_otp_email(to_email, otp)
                    )
                    return future.result(timeout=35)
            except RuntimeError:
                # No running loop - we can use asyncio.run directly
                print(f"   No running loop - using asyncio.run", flush=True)
                return asyncio.run(self.send_otp_email(to_email, otp))
        except Exception as e:
            print(f"❌ send_verification_email failed: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Log OTP for debugging
            print(f"[OTP DEBUG] Email: {to_email}, OTP: {otp}", flush=True)
            return False

    async def send_password_reset_email(
        self,
        email: str,
        reset_token: str,
        reset_url: Optional[str] = None
    ) -> bool:
        """Send password reset email."""

        if not reset_url:
            base_url = os.environ.get("FRONTEND_URL", "https://densho.me")
            reset_url = f"{base_url}/reset-password?token={reset_token}"

        print(f"🔑 Password reset for: {email}", flush=True)

        subject = "Reset Your DataLens Password"

        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; font-family: sans-serif; background-color: #f4f4f5;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: linear-gradient(135deg, #6366f1, #4f46e5); padding: 32px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0;">🔬 DataLens</h1>
        </div>
        <div style="background: white; padding: 40px 32px; border-radius: 0 0 16px 16px;">
            <h2 style="color: #111827;">Reset Your Password</h2>
            <p style="color: #4b5563;">Click below to reset your password:</p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{reset_url}" style="background: #4f46e5; color: white; padding: 16px 40px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    Reset Password
                </a>
            </div>
            <p style="color: #6b7280; font-size: 12px;">Link: {reset_url}</p>
            <p style="color: #92400e; background: #fef3c7; padding: 12px; border-radius: 8px;">⏱️ Expires in 1 hour</p>
        </div>
    </div>
</body>
</html>
"""

        return await self.send_email(email, subject, html_content)


# Singleton
_email_service: Optional[EmailService] = None

def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


# Backwards compatible module-level singleton
email_service = EmailService()
