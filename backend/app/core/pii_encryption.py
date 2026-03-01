"""
PII Encryption Service
Encrypts personally identifiable information at rest using AES-256-GCM.
Uses blind index pattern (HMAC-SHA256) for encrypted field lookups.
"""

import base64
import hashlib
import hmac
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.observability.logger import get_logger

logger = get_logger(__name__)


def _get_encryption_key() -> bytes:
    """Get the PII encryption key from environment, derive a proper 256-bit key."""
    raw_key = os.getenv("PII_ENCRYPTION_KEY", "")
    if not raw_key:
        raise ValueError(
            "PII_ENCRYPTION_KEY environment variable is required. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    # Derive a proper 32-byte key using SHA-256 (handles any input length)
    return hashlib.sha256(raw_key.encode()).digest()


def _get_hmac_key() -> bytes:
    """Derive a separate HMAC key from the encryption key for blind indices."""
    encryption_key = _get_encryption_key()
    # Use a different derivation to ensure HMAC key != encryption key
    return hashlib.sha256(b"blind-index:" + encryption_key).digest()


def encrypt_pii(plaintext: str) -> str:
    """
    Encrypt a PII string using AES-256-GCM.

    Returns: base64-encoded string of nonce + ciphertext + tag
    """
    if not plaintext:
        return ""

    key = _get_encryption_key()
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Combine nonce + ciphertext (tag is appended by AESGCM automatically)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_pii(encrypted: str) -> str:
    """
    Decrypt a PII string encrypted with encrypt_pii.

    Returns: original plaintext string
    """
    if not encrypted:
        return ""

    key = _get_encryption_key()
    raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))

    nonce = raw[:12]
    ciphertext = raw[12:]

    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    return plaintext.decode("utf-8")


def create_blind_index(value: str) -> str:
    """
    Create a deterministic blind index for encrypted field lookups.
    Uses HMAC-SHA256 — same input always produces same output,
    but the value cannot be reversed without the HMAC key.

    Returns: hex-encoded HMAC digest
    """
    if not value:
        return ""

    key = _get_hmac_key()
    # Normalize: lowercase, strip whitespace (emails are case-insensitive)
    normalized = value.lower().strip()
    digest = hmac.new(key, normalized.encode("utf-8"), hashlib.sha256).hexdigest()

    return digest
