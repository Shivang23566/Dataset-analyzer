"""
Security headers middleware — adds HSTS, X-Content-Type-Options, X-Frame-Options,
CSP, Referrer-Policy, and Permissions-Policy to every HTTP response.
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_IS_PRODUCTION = os.getenv("RENDER") is not None or os.getenv("ENVIRONMENT", "").lower() == "production"

# CSP: Allow Razorpay, Google Fonts, Resend, and Cloudinary
_CSP_PRODUCTION = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com https://api.razorpay.com https://*.razorpay.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https: http:; "
    "connect-src 'self' https://api.razorpay.com https://lumberjack.razorpay.com https://*.razorpay.com https://api.resend.com https://res.cloudinary.com; "
    "frame-src 'self' https://api.razorpay.com https://*.razorpay.com; "
    "frame-ancestors 'self'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

_CSP_DEVELOPMENT = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com https://api.razorpay.com https://*.razorpay.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https: http:; "
    "connect-src 'self' http://localhost:* ws://localhost:* https://api.razorpay.com https://*.razorpay.com; "
    "frame-src 'self' https://api.razorpay.com https://*.razorpay.com; "
    "frame-ancestors 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects security-hardening headers into every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Transport security (only meaningful over HTTPS but safe to always set)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - allow same origin for Razorpay iframe
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy — disable sensitive APIs not needed by the app
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            _CSP_PRODUCTION if _IS_PRODUCTION else _CSP_DEVELOPMENT
        )

        return response
