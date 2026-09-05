"""Keep automated tests independent of local credentials and external services."""

import httpx
import pytest
from tests.fakes import TestPolicy


@pytest.fixture(autouse=True)
def isolate_model_environment(monkeypatch):
    # dotenv may load during collection; override before every test, not just import.
    monkeypatch.setenv("MELTDOWN_MODEL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-credential")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-only-not-a-credential")

    def reject_external_http(*args, **kwargs):
        raise AssertionError(
            "External HTTP is disabled in automated tests; use the opt-in evaluation script."
        )

    async def reject_external_async_http(*args, **kwargs):
        reject_external_http()

    # FastAPI TestClient has its own in-process transport and remains available.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject_external_http)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_external_async_http)
    monkeypatch.setattr("meltdown.service.configured_policy", lambda: TestPolicy())
