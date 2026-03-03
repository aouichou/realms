"""Tests for app.services.email_service — SMTP email sending."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.email_service import send_email, send_password_reset_email

# ── send_email ────────────────────────────────────────────────────────────


async def test_send_email_success():
    """Happy path — SMTP sends without error."""
    mock_server = MagicMock()
    with (
        patch("app.services.email_service.settings") as mock_settings,
        patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls,
    ):
        mock_settings.smtp_user = "user@smtp.example.com"
        mock_settings.smtp_password = "secret"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 2525
        mock_settings.smtp_from_email = "noreply@example.com"

        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = await send_email("player@example.com", "Test", "<p>Hello</p>", "Hello")

    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@smtp.example.com", "secret")
    mock_server.send_message.assert_called_once()


async def test_send_email_no_smtp_credentials():
    """Should return False when SMTP credentials are empty."""
    with patch("app.services.email_service.settings") as mock_settings:
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""

        result = await send_email("a@b.com", "Subject", "<p>hi</p>")

    assert result is False


async def test_send_email_smtp_user_only():
    """Should return False when only smtp_user is set but not password."""
    with patch("app.services.email_service.settings") as mock_settings:
        mock_settings.smtp_user = "user"
        mock_settings.smtp_password = ""

        result = await send_email("a@b.com", "Subject", "<p>hi</p>")

    assert result is False


async def test_send_email_smtp_exception():
    """Should return False and not raise when SMTP throws."""
    with (
        patch("app.services.email_service.settings") as mock_settings,
        patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls,
    ):
        mock_settings.smtp_user = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 2525
        mock_settings.smtp_from_email = "noreply@example.com"

        mock_smtp_cls.return_value.__enter__ = MagicMock(
            side_effect=Exception("Connection refused")
        )
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = await send_email("a@b.com", "Subject", "<p>hi</p>")

    assert result is False


async def test_send_email_no_text_body():
    """Text fallback should be skipped when text_body is empty."""
    mock_server = MagicMock()
    with (
        patch("app.services.email_service.settings") as mock_settings,
        patch("app.services.email_service.smtplib.SMTP") as mock_smtp_cls,
    ):
        mock_settings.smtp_user = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 2525
        mock_settings.smtp_from_email = "noreply@example.com"

        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = await send_email("a@b.com", "Subject", "<p>hi</p>", "")

    assert result is True
    # Only HTML part attached (no text fallback)
    mock_server.send_message.assert_called_once()


# ── send_password_reset_email ─────────────────────────────────────────────


async def test_send_password_reset_email_calls_send_email():
    """Should delegate to send_email with proper HTML body."""
    with patch("app.services.email_service.send_email", return_value=True) as mock_send:
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.frontend_url = "http://localhost:3000"

            result = await send_password_reset_email(
                "user@example.com", "reset-token-123", "Gandalf"
            )

    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args[0][0] == "user@example.com"
    assert "Password Reset" in call_args[0][1]
    assert "reset-token-123" in call_args[0][2]  # token in HTML body
    assert "Gandalf" in call_args[0][2]  # username in HTML body


async def test_send_password_reset_email_failure():
    """Should propagate False from send_email."""
    with patch("app.services.email_service.send_email", return_value=False) as mock_send:
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.frontend_url = "http://localhost:3000"

            result = await send_password_reset_email("a@b.com", "tok", "User")

    assert result is False
