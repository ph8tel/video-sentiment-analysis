"""
Shared fixtures for the sentiment-scoring test suite.

MockLLMClient
─────────────
Implements LLMClient without any network calls. Accepts a list of pre-canned
responses that are returned in order; falls back to a default response when
the list is exhausted. Pass ``raises=`` to simulate LLM errors.

Dependency injection
────────────────────
``mock_llm_client`` sets up the FastAPI dependency override so HTTP tests
never reach a real LLM. Tests that call scoring functions directly just
instantiate MockLLMClient themselves.

LLM_PROVIDER isolation
───────────────────────
The ``isolate_env`` autouse fixture ensures no real OLLAMA_HOST or
LLM_PROVIDER leaks into tests via environment variables.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_client import LLMClient  # noqa: E402
from main import app, get_client, get_emotion_client  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"

NEUTRAL_RESPONSE = json.dumps({"tone": "NEUTRAL", "score": 5})
NEUTRAL_EMOTION_RESPONSE = json.dumps(
    {"anger_level": 0, "frustration_level": 0, "sarcasm_flag": False}
)


class MockLLMClient(LLMClient):
    """
    In-memory LLM client for unit and API tests.

    Args:
        responses: Ordered list of raw JSON strings to return.
                   Falls back to ``fallback`` when exhausted.
        fallback:  Response returned when ``responses`` is exhausted.
                   Defaults to NEUTRAL_RESPONSE (tone/score format).
        raises:    If set, ``complete()`` raises this exception instead.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        fallback: str = NEUTRAL_RESPONSE,
        raises: Exception | None = None,
    ) -> None:
        self._responses = iter(responses or [])
        self._fallback  = fallback
        self._raises    = raises

    async def complete(self, prompt: str) -> str:
        if self._raises is not None:
            raise self._raises
        return next(self._responses, self._fallback)


def make_emotion_mock(**kwargs) -> MockLLMClient:
    """Return a MockLLMClient pre-configured to return neutral emotion responses."""
    return MockLLMClient(fallback=NEUTRAL_EMOTION_RESPONSE, **kwargs)


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_transcript() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_transcript.json").read_text())


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def http_client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_llm_client():
    """
    Override the FastAPI LLM dependency with MockLLMClient.
    Clears the override after each test.
    """
    mock = MockLLMClient()
    app.dependency_overrides[get_client] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Prevent real env vars from leaking into tests."""
    monkeypatch.setenv("LLM_PROVIDER",  "ollama")
    monkeypatch.setenv("OLLAMA_HOST",   "http://test-ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL",  "test-model")
    monkeypatch.delenv("GROQ_API_KEY",  raising=False)
    monkeypatch.delenv("EMOTION_MODEL", raising=False)

