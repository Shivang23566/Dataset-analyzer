import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    @property
    def host(self) -> str:
        return settings.EMAIL_HOST

    @property
    def port(self) -> int:
        return settings.EMAIL_PORT

    @property
    def username(self) -> str:
        return settings.EMAIL_USERNAME

    @property
    def password(self) -> str:
        return settings.EMAIL_PASSWORD

    @property
    def from_name(self) -> str:
        return settings.EMAIL_FROM_NAME

    def send_verification_email(self, to_email: str, otp: str, full_name: str | None = None) -> bool:
        """Send OTP verification email."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Verify your DataLens account'
            msg['From'] = f"{self.from_name} <{self.username}>"
            msg['To'] = to_email

            name = full_name or "there"

            text = f"""Hi {name},

Your verification code for DataLens is:

{otp}

This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.

— The DataLens Team
"""

            html = f"""<!DOCTYPE html>
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
    <p>Hi {name},</p>
    <p>Enter this verification code to complete your signup:</p>
    <div class="otp-box">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Expires in {settings.OTP_EXPIRY_MINUTES} minutes</div>
    </div>
    <p>If you didn't request this code, you can safely ignore this email.</p>
    <div class="footer">
        <p>&copy; 2026 DataLens. All rights reserved.</p>
        <p>AI-powered Data Analysis Platform</p>
    </div>
</div>
</body>
</html>"""

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_email, msg.as_string())

            logger.info(f"Verification email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False


email_service = EmailService()
