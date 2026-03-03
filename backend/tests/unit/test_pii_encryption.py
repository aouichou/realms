"""Tests for app.core.pii_encryption — AES-256-GCM + HMAC blind index."""

from app.core.pii_encryption import create_blind_index, decrypt_pii, encrypt_pii

# ── encrypt / decrypt roundtrip ──────────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    plaintext = "alice@example.com"
    encrypted = encrypt_pii(plaintext)
    assert encrypted != plaintext
    assert decrypt_pii(encrypted) == plaintext


def test_encrypt_empty_string():
    assert encrypt_pii("") == ""


def test_decrypt_empty_string():
    assert decrypt_pii("") == ""


def test_encrypt_produces_different_ciphertext():
    """Each call uses a random nonce, so ciphertext must differ."""
    a = encrypt_pii("same-input")
    b = encrypt_pii("same-input")
    assert a != b
    # Both still decrypt to the same value
    assert decrypt_pii(a) == "same-input"
    assert decrypt_pii(b) == "same-input"


def test_encrypt_unicode_roundtrip():
    text = "Ünïcödé 日本語 emoji 🎲🐉"
    assert decrypt_pii(encrypt_pii(text)) == text


# ── blind index ──────────────────────────────────────────────────────────


def test_blind_index_deterministic():
    idx1 = create_blind_index("test@example.com")
    idx2 = create_blind_index("test@example.com")
    assert idx1 == idx2
    assert len(idx1) == 64  # SHA-256 hex digest length


def test_blind_index_case_insensitive():
    """Index normalises to lowercase, so case shouldn't matter."""
    a = create_blind_index("Test@Example.com")
    b = create_blind_index("test@example.com")
    assert a == b


def test_blind_index_strips_whitespace():
    a = create_blind_index("  test@example.com  ")
    b = create_blind_index("test@example.com")
    assert a == b


def test_blind_index_empty():
    assert create_blind_index("") == ""
