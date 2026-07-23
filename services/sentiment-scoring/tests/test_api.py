"""
Integration tests for the /health and /score API endpoints.

The LLM dependency is overridden with MockLLMClient for every test in
this module — no real Ollama or Groq calls are ever made.
"""

import json

import pytest

from color_mapper import Tone
from main import app, get_client
from tests.conftest import MockLLMClient


@pytest.fixture(autouse=True)
def default_mock_llm():
    """Replace the LLM client with a neutral mock for all tests in this module."""
    app.dependency_overrides[get_client] = lambda: MockLLMClient()
    yield
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    def test_returns_200(self, http_client):
        assert http_client.get("/health").status_code == 200

    def test_returns_ok_status(self, http_client):
        assert http_client.get("/health").json()["status"] == "ok"


class TestScoreEndpoint:
    def test_valid_transcript_returns_200(self, http_client, sample_transcript):
        response = http_client.post("/score", json=sample_transcript)
        assert response.status_code == 200

    def test_response_has_chunks_and_overall(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        assert "chunks" in data
        assert "overall" in data

    def test_chunk_count_matches_input(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        assert len(data["chunks"]) == len(sample_transcript)

    def test_each_chunk_has_required_fields(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        required = {"start", "end", "tone", "score", "color", "text"}
        for chunk in data["chunks"]:
            assert required.issubset(chunk.keys())

    def test_chunk_color_is_hex(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        for chunk in data["chunks"]:
            assert chunk["color"].startswith("#")
            assert len(chunk["color"]) == 7

    def test_chunk_score_in_range(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        for chunk in data["chunks"]:
            assert 0 <= chunk["score"] <= 10

    def test_chunk_tone_is_valid(self, http_client, sample_transcript):
        valid_tones = {t.value for t in Tone}
        data = http_client.post("/score", json=sample_transcript).json()
        for chunk in data["chunks"]:
            assert chunk["tone"] in valid_tones

    def test_overall_has_score_and_tone(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        assert "score" in data["overall"]
        assert "tone"  in data["overall"]

    def test_overall_score_in_range(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        assert 0 <= data["overall"]["score"] <= 10

    def test_chunk_text_preserved_in_response(self, http_client, sample_transcript):
        data = http_client.post("/score", json=sample_transcript).json()
        for i, chunk in enumerate(data["chunks"]):
            assert chunk["text"] == sample_transcript[i]["text"]

    def test_specific_mock_response_is_used(self, http_client):
        app.dependency_overrides[get_client] = lambda: MockLLMClient(
            responses=[json.dumps({"tone": "VERY_POSITIVE", "score": 10})]
        )
        data = http_client.post(
            "/score",
            json=[{"start": 0.0, "end": 2.0, "text": "Amazing!"}],
        ).json()
        assert data["chunks"][0]["tone"] == "VERY_POSITIVE"
        assert data["chunks"][0]["score"] == 10

    def test_empty_array_returns_422(self, http_client):
        assert http_client.post("/score", json=[]).status_code == 422

    def test_missing_text_field_returns_422(self, http_client):
        response = http_client.post(
            "/score",
            json=[{"start": 0.0, "end": 2.0}],  # missing 'text'
        )
        assert response.status_code == 422

    def test_not_an_array_returns_422(self, http_client):
        response = http_client.post(
            "/score",
            json={"start": 0.0, "end": 2.0, "text": "test"},
        )
        assert response.status_code == 422

    def test_llm_error_returns_502(self, http_client):
        app.dependency_overrides[get_client] = lambda: MockLLMClient(
            raises=RuntimeError("Ollama unreachable")
        )
        response = http_client.post(
            "/score",
            json=[{"start": 0.0, "end": 2.0, "text": "test"}],
        )
        assert response.status_code == 502

    def test_llm_bad_json_returns_502(self, http_client):
        app.dependency_overrides[get_client] = lambda: MockLLMClient(
            responses=["this is not json"]
        )
        response = http_client.post(
            "/score",
            json=[{"start": 0.0, "end": 2.0, "text": "test"}],
        )
        assert response.status_code == 502
