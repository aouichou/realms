"""Shared test helper utilities."""

import uuid
from datetime import datetime


def assert_valid_uuid(value: str) -> None:
    """Assert value is a valid UUID4 string."""
    uuid.UUID(value, version=4)


def assert_iso_datetime(value: str) -> None:
    """Assert value is a valid ISO 8601 datetime string."""
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def assert_error_response(response, status_code: int, detail_contains: str | None = None):
    """Assert that *response* is an error with the expected shape.

    Parameters
    ----------
    response:
        The ``httpx.Response`` (or ``TestClient`` response) to inspect.
    status_code:
        Expected HTTP status code.
    detail_contains:
        If provided, asserts that *detail* contains this substring
        (case-insensitive).
    """
    assert response.status_code == status_code
    data = response.json()
    assert "detail" in data
    if detail_contains:
        assert detail_contains.lower() in data["detail"].lower()
