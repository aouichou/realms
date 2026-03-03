"""Tests for ErrorLoggerMiddleware — error_logger.py"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.error_logger import ErrorLoggerMiddleware

# ---------------------------------------------------------------------------
# Test app
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorLoggerMiddleware)

    @app.get("/ok")
    async def ok_endpoint():
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("test error")

    @app.get("/chained-error")
    async def chained_error():
        try:
            raise TypeError("root cause")
        except TypeError as e:
            raise RuntimeError("wrapper") from e

    return app


async def _get_client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    async def test_success_passes_through(self):
        app = _make_app()
        async with await _get_client(app) as client:
            resp = await client.get("/ok")
            assert resp.status_code == 200

    async def test_error_returns_500(self):
        app = _make_app()
        async with await _get_client(app) as client:
            resp = await client.get("/error")
            assert resp.status_code == 500


# ---------------------------------------------------------------------------
# _build_error_details
# ---------------------------------------------------------------------------


class TestBuildErrorDetails:
    def test_builds_details(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())

        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"
        request.url.__str__ = lambda self: "http://test/test"
        request.query_params = {}
        request.path_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.client.port = 8000
        request.headers = MagicMock()
        request.headers.items.return_value = [
            ("content-type", "application/json"),
            ("authorization", "Bearer secret"),
        ]
        request.state = MagicMock()
        request.state.request_id = "req-123"
        request.state.user_id = None
        request.state.character_id = None
        request.state.session_id = None
        request.state.active_companion_ids = []
        request.state.combat_session_id = None
        request.state.in_combat = False

        exc = ValueError("test error")
        details = middleware._build_error_details(request, exc)

        assert details["error"]["type"] == "ValueError"
        assert details["error"]["message"] == "test error"
        assert details["request"]["method"] == "GET"
        assert details["request"]["path"] == "/test"
        # Authorization should be filtered out
        headers = details["request"]["headers"]
        assert "authorization" not in headers

    def test_no_client(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())

        request = MagicMock()
        request.method = "POST"
        request.url = MagicMock()
        request.url.path = "/x"
        request.url.__str__ = lambda self: "http://test/x"
        request.query_params = {}
        request.path_params = {}
        request.client = None
        request.headers = MagicMock()
        request.headers.items.return_value = []
        request.state = MagicMock()
        request.state.request_id = None
        request.state.user_id = None
        request.state.character_id = None
        request.state.session_id = None
        request.state.active_companion_ids = []
        request.state.combat_session_id = None
        request.state.in_combat = False

        exc = RuntimeError("err")
        details = middleware._build_error_details(request, exc)
        assert details["request"]["client"]["host"] is None
        assert details["request"]["client"]["port"] is None


# ---------------------------------------------------------------------------
# _get_exception_chain
# ---------------------------------------------------------------------------


class TestExceptionChain:
    def test_single_exception(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())
        exc = ValueError("single")
        chain = middleware._get_exception_chain(exc)
        assert len(chain) == 1
        assert chain[0]["type"] == "ValueError"

    def test_chained_exception(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())
        try:
            try:
                raise TypeError("root")
            except TypeError as e:
                raise RuntimeError("wrapper") from e
        except RuntimeError as outer:
            chain = middleware._get_exception_chain(outer)
            assert len(chain) == 2
            assert chain[0]["type"] == "RuntimeError"
            assert chain[1]["type"] == "TypeError"

    def test_implicit_chain(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())
        try:
            try:
                raise TypeError("root")
            except TypeError:
                raise RuntimeError("wrapper")
        except RuntimeError as outer:
            chain = middleware._get_exception_chain(outer)
            assert len(chain) >= 2


# ---------------------------------------------------------------------------
# _write_error_to_file
# ---------------------------------------------------------------------------


class TestWriteErrorToFile:
    def test_writes_json_and_txt(self, tmp_path):
        middleware = ErrorLoggerMiddleware(app=MagicMock())

        error_details = {
            "timestamp": "2026-01-01T00:00:00",
            "error": {
                "type": "ValueError",
                "message": "test",
                "module": "builtins",
                "traceback": "Traceback ...",
                "chain": [{"type": "ValueError", "message": "test", "module": "builtins"}],
            },
            "request": {
                "method": "GET",
                "url": "http://test/x",
                "path": "/x",
                "client": {"host": "127.0.0.1"},
            },
        }

        with patch("app.middleware.error_logger.ERROR_LOG_DIR", tmp_path):
            middleware._write_error_to_file(error_details)

        json_files = list(tmp_path.glob("*.json"))
        txt_files = list(tmp_path.glob("*.txt"))
        assert len(json_files) == 1
        assert len(txt_files) == 1

        data = json.loads(json_files[0].read_text())
        assert data["error"]["type"] == "ValueError"

    def test_handles_write_error(self):
        middleware = ErrorLoggerMiddleware(app=MagicMock())
        # Passing non-serializable data shouldn't crash
        with patch("app.middleware.error_logger.ERROR_LOG_DIR") as mock_dir:
            mock_dir.__truediv__ = MagicMock(side_effect=PermissionError("no access"))
            # Should not raise, just log the error
            middleware._write_error_to_file({"timestamp": "x", "error": {}})
