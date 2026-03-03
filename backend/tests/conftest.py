"""
Root pytest configuration and shared fixtures.

IMPORTANT: Environment variables are set BEFORE any app imports to ensure
the app's module-level engine creation uses the test database URL.
"""

import os

# ── Set test environment variables BEFORE any app imports ──────────────────
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-ci-only")
os.environ.setdefault("MISTRAL_API_KEY", "test-key")
os.environ.setdefault("PII_ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItY2ktb25seQ==")
os.environ.setdefault("REDIS_URL", "")

import pytest


def pytest_addoption(parser):
    """Add custom pytest CLI options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require real external services",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires --integration flag)",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a fast unit test",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip integration tests unless --integration flag is provided."""
    if config.getoption("--integration"):
        return

    skip_integration = pytest.mark.skip(reason="Need --integration flag to run integration tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
