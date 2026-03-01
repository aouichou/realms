#!/usr/bin/env python3
"""
One-time data migration: Encrypt existing plaintext emails and populate blind indices.

Run this AFTER the Alembic migration (d4e5f6g7h8i9) has been applied.
Requires PII_ENCRYPTION_KEY environment variable to be set.

Usage:
    cd backend
    PII_ENCRYPTION_KEY=<your-key> python scripts/migrate_encrypt_emails.py

What it does:
    1. Reads all users with non-null, non-encrypted emails
    2. Encrypts each email with AES-256-GCM
    3. Creates a blind index (HMAC-SHA256) for each email
    4. Updates the user record in the database
    5. Reports results (encrypted count, skipped, errors)

Safety:
    - Idempotent: skips already-encrypted emails (detected by base64 pattern)
    - Transactional: commits per-user to avoid losing progress on large datasets
    - Logged: prints every action for audit trail
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure PII_ENCRYPTION_KEY is set before importing app modules
if not os.getenv("PII_ENCRYPTION_KEY"):
    print("ERROR: PII_ENCRYPTION_KEY environment variable is required")
    print('Generate one with: python -c "import secrets; print(secrets.token_hex(32))"')
    sys.exit(1)


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.pii_encryption import create_blind_index, encrypt_pii


def is_already_encrypted(value: str) -> bool:
    """
    Heuristic to detect if an email is already encrypted.
    Encrypted values are base64url-encoded and don't contain '@'.
    Plaintext emails always contain '@'.
    """
    if not value:
        return False
    # Plaintext emails must contain '@'
    if "@" in value:
        return False
    # Try to decode as base64 — encrypted values are valid base64
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        # AES-GCM: 12-byte nonce + at least 16-byte tag + some ciphertext
        return len(decoded) >= 28
    except Exception:
        return False


async def migrate_emails():
    """Encrypt all plaintext emails and populate blind indices."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stats = {"encrypted": 0, "skipped": 0, "errors": 0, "total": 0}

    async with async_session() as session:
        # Fetch all users with non-null emails
        result = await session.execute(
            text("SELECT id, email, email_blind_index FROM users WHERE email IS NOT NULL")
        )
        users = result.fetchall()
        stats["total"] = len(users)

        print(f"Found {len(users)} users with emails to process")

        for user_id, email, existing_blind_index in users:
            try:
                # Skip already-encrypted emails
                if is_already_encrypted(email):
                    if existing_blind_index:
                        print(f"  SKIP {user_id}: already encrypted with blind index")
                        stats["skipped"] += 1
                        continue
                    else:
                        # Encrypted but missing blind index — this shouldn't happen
                        # but handle it by decrypting first
                        print(f"  WARN {user_id}: encrypted but missing blind index, re-processing")
                        from app.core.pii_encryption import decrypt_pii

                        plaintext_email = decrypt_pii(email)
                else:
                    plaintext_email = email

                # Encrypt the email
                encrypted_email = encrypt_pii(plaintext_email)
                blind_index = create_blind_index(plaintext_email)

                # Update the record
                await session.execute(
                    text(
                        "UPDATE users SET email = :encrypted, email_blind_index = :blind "
                        "WHERE id = :uid"
                    ),
                    {
                        "encrypted": encrypted_email,
                        "blind": blind_index,
                        "uid": str(user_id),
                    },
                )
                await session.commit()

                print(f"  OK   {user_id}: {plaintext_email[:3]}*** -> encrypted + blind index")
                stats["encrypted"] += 1

            except Exception as e:
                await session.rollback()
                print(f"  ERR  {user_id}: {e}")
                stats["errors"] += 1

    await engine.dispose()

    print("\n--- Migration Summary ---")
    print(f"Total users with email: {stats['total']}")
    print(f"Encrypted:              {stats['encrypted']}")
    print(f"Skipped (already done): {stats['skipped']}")
    print(f"Errors:                 {stats['errors']}")

    if stats["errors"] > 0:
        print("\n⚠️  Some users had errors — check logs above and re-run if needed")
        sys.exit(1)
    else:
        print("\n✅ All emails encrypted successfully")


if __name__ == "__main__":
    asyncio.run(migrate_emails())
