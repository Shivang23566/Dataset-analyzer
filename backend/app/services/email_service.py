"""
Email Service using Resend API
Works on Render free tier (HTTPS instead of blocked SMTP port 587)

Configuration:
- RESEND_API_KEY: Your Resend API key (required for sending)
- EMAIL_FROM: Sender email (default: onboarding@resend.dev)
- EMAIL_FROM_NAME: Sender display name (default: DataLens)
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import httpx with fallback
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not installed - email sending will be disabled")


class EmailService:
    """
    Email service using Resend HTTP API.
    Gracefully falls back to logging if not configured.
    """

    def __init__(self):
        self.api_key = os.environ.get("RESEND_API_KEY", "")
        self.from_email = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
        self.from_name = os.environ.get("EMAIL_FROM_NAME", "DataLens")
        self.api_url = "https://api.resend.com/emails"

        # Legacy attributes for backwards compatibility
        self.host = "api.resend.com"
        self.port = 443
        self.username = self.from_email
        self.password = self.api_key

        if not self.api_key:
            logger.warning(
                "RESEND_API_KEY not configured. "
                "Emails will be logged but not sent. "
                "Get your free API key at https://resend.com"
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using Resend API.

        Returns True if sent successfully or logged (when not configured).
        Returns False only on actual send failures.
        """

        # Log-only mode when API key not set
        if not self.api_key:
            logger.info(f"[EMAIL LOG] To: {to_email}")
            logger.info(f"[EMAIL LOG] Subject: {subject}")
            logger.debug(f"[EMAIL LOG] Content preview: {html_content[:200]}...")
            # Return True so signup flow continues (OTP logged in server logs)
            return True

        if not HTTPX_AVAILABLE:
            logger.error("Cannot send email: httpx package not installed")
            return False

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

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Email sent successfully to {to_email}, "
                        f"ID: {result.get('id', 'unknown')}"
                    )
                    return True
                else:
                    logger.error(
                        f"Email send failed: HTTP {response.status_code} - "
                        f"{response.text[:200]}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Email send timeout for {to_email}")
            return False
        except httpx.ConnectError as e:
            logger.error(f"Email connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Email send error: {type(e).__name__}: {str(e)}")
            return False

    async def send_otp_email(self, email: str, otp: str) -> bool:
        """Send OTP verification email for signup."""

        subject = f"Your DataLens Verification Code: {otp}"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #0e0f0d;
    color: #cdc9c0;
    margin: 0;
    padding: 40px 20px;
}}
.container {{
    max-width: 480px;
    margin: 0 auto;
    background: #1a1b19;
    border-radius: 16px;
    padding: 40px;
    border: 1px solid rgba(255,255,255,0.1);
}}
.logo {{
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    color: #c9a84c;
    margin-bottom: 32px;
}}
h1 {{
    font-size: 24px;
    margin: 0 0 16px 0;
    color: #cdc9c0;
}}
.otp-box {{
    background: linear-gradient(135deg, rgba(201,168,76,0.1), rgba(46,184,160,0.1));
    border: 2px solid #c9a84c;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    margin: 24px 0;
}}
.otp-code {{
    font-size: 36px;
    font-weight: bold;
    letter-spacing: 8px;
    color: #c9a84c;
    font-family: monospace;
}}
.expiry {{
    color: #8a8780;
    font-size: 14px;
    margin-top: 12px;
}}
.footer {{
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.1);
    color: #5a5955;
    font-size: 12px;
    text-align: center;
}}
</style>
</head>
<body>
<div class="container">
    <div class="logo">&#9670; DataLens</div>
    <h1>Verify your email</h1>
    <p>Enter this verification code to complete your signup:</p>
    <div class="otp-box">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Expires in 10 minutes</div>
    </div>
    <p>If you didn't request this code, you can safely ignore this email.</p>
    <div class="footer">
        <p>&copy; 2026 DataLens. All rights reserved.</p>
        <p>AI-powered Data Analysis Platform</p>
    </div>
</div>
</body>
</html>"""

        text_content = f"""DataLens - Email Verification

Your verification code is: {otp}

This code expires in 10 minutes.

If you didn't request this, please ignore this email.

© 2026 DataLens - AI-Powered Data Analysis
"""

        return await self.send_email(email, subject, html_content, text_content)

    def send_verification_email(self, to_email: str, otp: str, full_name: str | None = None) -> bool:
        """
        Sync wrapper for backwards compatibility.
        Note: This blocks - prefer send_otp_email for async code.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.send_otp_email(to_email, otp)
                    )
                    return future.result(timeout=35)
            else:
                return loop.run_until_complete(self.send_otp_email(to_email, otp))
        except Exception as e:
            logger.error(f"send_verification_email failed: {e}")
            # Log OTP for debugging in development
            logger.info(f"[OTP DEBUG] Email: {to_email}, OTP: {otp}")
            return True  # Return True so signup flow continues

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

        subject = "Reset Your DataLens Password"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #0e0f0d;
    color: #cdc9c0;
    margin: 0;
    padding: 40px 20px;
}}
.container {{
    max-width: 480px;
    margin: 0 auto;
    background: #1a1b19;
    border-radius: 16px;
    padding: 40px;
    border: 1px solid rgba(255,255,255,0.1);
}}
.logo {{
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    color: #c9a84c;
    margin-bottom: 32px;
}}
h1 {{
    font-size: 24px;
    margin: 0 0 16px 0;
    color: #cdc9c0;
}}
.btn {{
    display: inline-block;
    background: linear-gradient(135deg, #c9a84c 0%, #b8963a 100%);
    color: #0e0f0d;
    text-decoration: none;
    padding: 16px 40px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    margin: 24px 0;
}}
.link {{
    color: #c9a84c;
    font-size: 12px;
    word-break: break-all;
    background: rgba(255,255,255,0.05);
    padding: 12px;
    border-radius: 6px;
    margin: 16px 0;
}}
.expiry {{
    background: rgba(201,168,76,0.1);
    border-left: 4px solid #c9a84c;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 24px 0;
    color: #cdc9c0;
    font-size: 14px;
}}
.footer {{
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.1);
    color: #5a5955;
    font-size: 12px;
    text-align: center;
}}
</style>
</head>
<body>
<div class="container">
    <div class="logo">&#9670; DataLens</div>
    <h1>Reset Your Password</h1>
    <p>We received a request to reset your password. Click the button below to create a new password:</p>
    <div style="text-align: center;">
        <a href="{reset_url}" class="btn">Reset Password</a>
    </div>
    <p style="color: #8a8780; font-size: 13px;">Or copy this link:</p>
    <div class="link">{reset_url}</div>
    <div class="expiry">This link expires in 1 hour</div>
    <p>If you didn't request a password reset, please ignore this email.</p>
    <div class="footer">
        <p>&copy; 2026 DataLens. All rights reserved.</p>
    </div>
</div>
</body>
</html>"""

        text_content = f"""DataLens - Password Reset

Click the link below to reset your password:
{reset_url}

This link expires in 1 hour.

If you didn't request this, please ignore this email.

© 2026 DataLens
"""

        return await self.send_email(email, subject, html_content, text_content)

    async def send_welcome_email(self, email: str, full_name: str) -> bool:
        """Send welcome email after successful signup."""

        first_name = full_name.split()[0] if full_name else "there"
        subject = f"Welcome to DataLens, {first_name}!"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #0e0f0d;
    color: #cdc9c0;
    margin: 0;
    padding: 40px 20px;
}}
.container {{
    max-width: 480px;
    margin: 0 auto;
    background: #1a1b19;
    border-radius: 16px;
    padding: 40px;
    border: 1px solid rgba(255,255,255,0.1);
}}
.logo {{
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    color: #c9a84c;
    margin-bottom: 32px;
}}
h1 {{
    font-size: 24px;
    margin: 0 0 16px 0;
    color: #cdc9c0;
}}
.features {{
    margin: 24px 0;
    padding: 0;
    list-style: none;
}}
.features li {{
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.btn {{
    display: inline-block;
    background: linear-gradient(135deg, #c9a84c 0%, #b8963a 100%);
    color: #0e0f0d;
    text-decoration: none;
    padding: 16px 40px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
}}
.footer {{
    margin-top: 32px;
    padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.1);
    color: #5a5955;
    font-size: 12px;
    text-align: center;
}}
</style>
</head>
<body>
<div class="container">
    <div class="logo">&#9670; DataLens</div>
    <h1>Welcome, {first_name}!</h1>
    <p>Your account has been created successfully. You're now ready to unlock powerful insights from your data!</p>
    <h3 style="color: #c9a84c; margin: 24px 0 16px 0;">What you can do:</h3>
    <ul class="features">
        <li>📊 <strong>Exploratory Data Analysis</strong> - Instant statistical insights</li>
        <li>📈 <strong>Smart Visualizations</strong> - AI-recommended charts</li>
        <li>🔧 <strong>Data Preprocessing</strong> - Clean and transform data (Pro)</li>
        <li>🤖 <strong>ML Model Training</strong> - Build models without code (Pro)</li>
    </ul>
    <div style="text-align: center; margin: 32px 0;">
        <a href="https://densho.me/dashboard" class="btn">Go to Dashboard</a>
    </div>
    <p style="color: #8a8780;">Questions? Just reply to this email - we're happy to help!</p>
    <div class="footer">
        <p>&copy; 2026 DataLens. All rights reserved.</p>
    </div>
</div>
</body>
</html>"""

        text_content = f"""Welcome to DataLens, {first_name}!

Your account has been created successfully.

What you can do:
- Exploratory Data Analysis - Instant statistical insights
- Smart Visualizations - AI-recommended charts
- Data Preprocessing - Clean and transform data (Pro)
- ML Model Training - Build models without code (Pro)

Get started: https://densho.me/dashboard

© 2026 DataLens
"""

        return await self.send_email(email, subject, html_content, text_content)


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


# Backwards compatible singleton
email_service = EmailService()
