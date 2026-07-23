"""
Unit tests for llm_client.py.

All HTTP calls are intercepted by respx — no real network traffic is made.
Environment variables are isolated by the ``isolate_env`` autouse fixture
in conftest.py.
"""

import os

import httpx
import pytest
import respx

from llm_client import GroqClient, OllamaClient, get_llm_client


class TestOllamaClient:
    @respx.mock
    async def test_posts_to_generate_endpoint(self, respx_mock):
        respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": '{"tone":"NEUTRAL","score":5}'})
        )
        client = OllamaClient()
        await client.complete("hello")
        assert respx_mock.calls.call_count == 1

    @respx.mock
    async def test_request_body_includes_model(self, respx_mock):
        route = respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": '{"tone":"NEUTRAL","score":5}'})
        )
        client = OllamaClient()
        await client.complete("test")
        sent = route.calls[0].request
        import json
        body = json.loads(sent.content)
        assert body["model"] == "test-model"

    @respx.mock
    async def test_request_body_includes_prompt(self, respx_mock):
        route = respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": '{"tone":"NEUTRAL","score":5}'})
        )
        client = OllamaClient()
        await client.complete("my specific prompt")
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["prompt"] == "my specific prompt"

    @respx.mock
    async def test_request_sets_format_json(self, respx_mock):
        route = respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={"response": '{"tone":"NEUTRAL","score":5}'})
        )
        client = OllamaClient()
        await client.complete("test")
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["format"] == "json"
        assert body["stream"] is False

    @respx.mock
    async def test_returns_response_field(self, respx_mock):
        respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200, json={"response": '{"tone":"POSITIVE","score":8}'}
            )
        )
        client = OllamaClient()
        result = await client.complete("test")
        assert result == '{"tone":"POSITIVE","score":8}'

    @respx.mock
    async def test_raises_on_http_error(self, respx_mock):
        respx_mock.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        client = OllamaClient()
        with pytest.raises(httpx.HTTPStatusError):
            await client.complete("test")

    def test_reads_host_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:11434")
        client = OllamaClient()
        assert client.host == "http://custom-host:11434"

    def test_reads_model_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
        client = OllamaClient()
        assert client.model == "llama3.2:3b"


class TestGroqClient:
    def test_raises_if_api_key_not_set(self):
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            GroqClient()

    def test_initialises_with_api_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        client = GroqClient()
        assert client.api_key == "test-key"

    def test_reads_groq_model_from_env(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        client = GroqClient()
        assert client.model == "llama-3.3-70b-versatile"

    def test_default_groq_model(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        client = GroqClient()
        assert client.model == "llama-3.1-8b-instant"

    @respx.mock
    async def test_posts_to_groq_endpoint(self, respx_mock, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": '{"tone":"NEUTRAL","score":5}'}}
                    ]
                },
            )
        )
        client = GroqClient()
        result = await client.complete("test")
        assert result == '{"tone":"NEUTRAL","score":5}'

    @respx.mock
    async def test_sends_authorization_header(self, respx_mock, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "my-secret-key")
        route = respx_mock.post("https://api.groq.com/openai/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"tone":"NEUTRAL","score":5}'}}]},
            )
        )
        client = GroqClient()
        await client.complete("test")
        auth = route.calls[0].request.headers.get("authorization")
        assert auth == "Bearer my-secret-key"


class TestGetLlmClient:
    def test_returns_ollama_client_by_default(self):
        client = get_llm_client()
        assert isinstance(client, OllamaClient)

    def test_returns_ollama_client_when_provider_is_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        assert isinstance(get_llm_client(), OllamaClient)

    def test_returns_groq_client_when_provider_is_groq(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "some-key")
        assert isinstance(get_llm_client(), GroqClient)

    def test_provider_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "OLLAMA")
        assert isinstance(get_llm_client(), OllamaClient)

    def test_raises_for_unknown_provider(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm_client()
