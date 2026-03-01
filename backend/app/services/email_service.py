"""
Email service using SMTP (SMTP2GO).
Handles sending transactional emails like password reset.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)


async def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send an email via SMTP.

    Returns True if sent successfully, False otherwise.
    Note: Uses synchronous smtplib — for production scale, use aiosmtplib.
    """
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP credentials not configured — email not sent")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        # Plain text fallback
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))

        # HTML body
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email[:3]}***")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_password_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """Send password reset email with a secure link."""
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

    subject = "Mistral Realms — Password Reset"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 40px 20px; }}
            .container {{ max-width: 480px; margin: 0 auto; background: #1a1a2e; border-radius: 12px; padding: 32px; border: 1px solid #2a2a3e; }}
            .logo {{ text-align: center; font-size: 24px; font-weight: bold; color: #a78bfa; margin-bottom: 24px; }}
            .btn {{ display: inline-block; background: #7c3aed; color: #ffffff; text-decoration: none; padding: 12px 32px; border-radius: 8px; font-weight: 600; margin: 16px 0; }}
            .btn:hover {{ background: #6d28d9; }}
            .footer {{ font-size: 12px; color: #666; margin-top: 24px; text-align: center; }}
            .warning {{ font-size: 13px; color: #f59e0b; margin-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">⚔️ Mistral Realms</div>
            <p>Hi <strong>{username}</strong>,</p>
            <p>We received a request to reset your password. Click the button below to choose a new password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="btn">Reset Password</a>
            </p>
            <p class="warning">⏰ This link expires in 30 minutes. If you didn't request this, you can safely ignore this email.</p>
            <div class="footer">
                <p>Mistral Realms — AI-Powered D&D Adventures</p>
                <p>If the button doesn't work, copy this link:<br>
                <a href="{reset_url}" style="color: #a78bfa; word-break: break-all;">{reset_url}</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Hi {username},

We received a request to reset your password for Mistral Realms.

Reset your password: {reset_url}

This link expires in 30 minutes. If you didn't request this, ignore this email.

— Mistral Realms
    """

    return await send_email(to_email, subject, html_body, text_body)
