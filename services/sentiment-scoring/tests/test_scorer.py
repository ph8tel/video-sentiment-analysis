"""
Unit tests for scorer.py — MockLLMClient is used throughout.
No network calls, no real LLM.
"""

import json

import pytest

from color_mapper import Tone, tone_to_color
from scorer import (
    ScoredChunk,
    TranscriptChunk,
    _LLMResponse,
    build_prompt,
    parse_llm_response,
    score_chunk,
    score_transcript,
)
from tests.conftest import MockLLMClient


class TestBuildPrompt:
    def test_includes_chunk_text(self):
        prompt = build_prompt("Hello world")
        assert "Hello world" in prompt

    def test_includes_all_tone_names(self):
        prompt = build_prompt("test")
        for tone in Tone:
            assert tone.value in prompt

    def test_instructs_json_only_output(self):
        prompt = build_prompt("test")
        assert "JSON" in prompt.upper()

    def test_score_range_mentioned(self):
        prompt = build_prompt("test")
        assert "0" in prompt and "10" in prompt


class TestParseLlmResponse:
    def test_valid_response_returns_model(self):
        raw = json.dumps({"tone": "NEUTRAL", "score": 5})
        result = parse_llm_response(raw)
        assert result.tone == Tone.NEUTRAL
        assert result.score == 5

    def test_all_valid_tones_accepted(self):
        for tone in Tone:
            raw = json.dumps({"tone": tone.value, "score": 5})
            result = parse_llm_response(raw)
            assert result.tone == tone

    def test_extra_fields_are_ignored(self):
        raw = json.dumps({"tone": "NEUTRAL", "score": 5, "explanation": "ignored"})
        result = parse_llm_response(raw)
        assert result.tone == Tone.NEUTRAL

    def test_score_zero_is_valid(self):
        raw = json.dumps({"tone": "VERY_NEGATIVE", "score": 0})
        assert parse_llm_response(raw).score == 0

    def test_score_ten_is_valid(self):
        raw = json.dumps({"tone": "VERY_POSITIVE", "score": 10})
        assert parse_llm_response(raw).score == 10

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_llm_response("not json at all")

    def test_invalid_tone_raises_value_error(self):
        raw = json.dumps({"tone": "VERY_HAPPY", "score": 8})
        with pytest.raises(ValueError):
            parse_llm_response(raw)

    def test_score_above_10_raises_value_error(self):
        raw = json.dumps({"tone": "NEUTRAL", "score": 11})
        with pytest.raises(ValueError):
            parse_llm_response(raw)

    def test_score_below_0_raises_value_error(self):
        raw = json.dumps({"tone": "NEUTRAL", "score": -1})
        with pytest.raises(ValueError):
            parse_llm_response(raw)

    def test_missing_tone_raises_value_error(self):
        raw = json.dumps({"score": 5})
        with pytest.raises(ValueError):
            parse_llm_response(raw)

    def test_missing_score_raises_value_error(self):
        raw = json.dumps({"tone": "NEUTRAL"})
        with pytest.raises(ValueError):
            parse_llm_response(raw)


class TestScoreChunk:
    async def test_calls_client_complete(self):
        calls = []

        class TrackingClient(MockLLMClient):
            async def complete(self, prompt: str) -> str:
                calls.append(prompt)
                return json.dumps({"tone": "NEUTRAL", "score": 5})

        chunk = TranscriptChunk(start=0.0, end=3.0, text="Hello world")
        await score_chunk(chunk, TrackingClient())
        assert len(calls) == 1
        assert "Hello world" in calls[0]

    async def test_prompt_contains_chunk_text(self):
        captured = []

        class CapturingClient(MockLLMClient):
            async def complete(self, prompt: str) -> str:
                captured.append(prompt)
                return json.dumps({"tone": "POSITIVE", "score": 8})

        chunk = TranscriptChunk(start=0.0, end=2.0, text="Great news!")
        await score_chunk(chunk, CapturingClient())
        assert "Great news!" in captured[0]

    async def test_returns_scored_chunk_with_correct_fields(self):
        client = MockLLMClient(responses=[json.dumps({"tone": "POSITIVE", "score": 8})])
        chunk = TranscriptChunk(start=1.0, end=4.0, text="Great job")
        result = await score_chunk(chunk, client)

        assert isinstance(result, ScoredChunk)
        assert result.start == 1.0
        assert result.end == 4.0
        assert result.tone == Tone.POSITIVE
        assert result.score == 8
        assert result.text == "Great job"

    async def test_color_matches_tone(self):
        client = MockLLMClient(responses=[json.dumps({"tone": "NEGATIVE", "score": 2})])
        chunk = TranscriptChunk(start=0.0, end=2.0, text="Bad news")
        result = await score_chunk(chunk, client)
        assert result.color == tone_to_color(Tone.NEGATIVE)

    async def test_propagates_llm_error(self):
        client = MockLLMClient(raises=RuntimeError("timeout"))
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(RuntimeError, match="timeout"):
            await score_chunk(chunk, client)

    async def test_raises_on_invalid_llm_response(self):
        client = MockLLMClient(responses=["not valid json"])
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(ValueError, match="invalid JSON"):
            await score_chunk(chunk, client)


class TestScoreTranscript:
    async def test_scores_all_chunks(self):
        responses = [
            json.dumps({"tone": "POSITIVE",  "score": 8}),
            json.dumps({"tone": "NEUTRAL",   "score": 5}),
            json.dumps({"tone": "NEGATIVE",  "score": 2}),
        ]
        chunks = [
            TranscriptChunk(start=0.0, end=3.0, text="Great"),
            TranscriptChunk(start=3.0, end=6.0, text="Okay"),
            TranscriptChunk(start=6.0, end=9.0, text="Bad"),
        ]
        result = await score_transcript(chunks, MockLLMClient(responses=responses))
        assert len(result.chunks) == 3

    async def test_overall_is_duration_weighted(self):
        # Chunk 1: score=8, duration=6s → weight 6
        # Chunk 2: score=2, duration=2s → weight 2
        # Weighted avg = (8*6 + 2*2) / (6+2) = (48+4)/8 = 6.5
        responses = [
            json.dumps({"tone": "POSITIVE",  "score": 8}),
            json.dumps({"tone": "NEGATIVE",  "score": 2}),
        ]
        chunks = [
            TranscriptChunk(start=0.0, end=6.0, text="Good"),
            TranscriptChunk(start=6.0, end=8.0, text="Bad"),
        ]
        result = await score_transcript(chunks, MockLLMClient(responses=responses))
        assert result.overall.score == 6.5

    async def test_overall_tone_derived_from_score(self):
        responses = [json.dumps({"tone": "NEUTRAL", "score": 5})]
        chunks = [TranscriptChunk(start=0.0, end=1.0, text="OK")]
        result = await score_transcript(chunks, MockLLMClient(responses=responses))
        assert result.overall.tone == Tone.NEUTRAL

    async def test_result_contains_required_fields(self):
        responses = [json.dumps({"tone": "SLIGHTLY_POSITIVE", "score": 6})]
        chunks = [TranscriptChunk(start=0.0, end=3.0, text="Pretty good")]
        result = await score_transcript(chunks, MockLLMClient(responses=responses))
        chunk = result.chunks[0]
        assert chunk.color.startswith("#")
        assert chunk.text == "Pretty good"
        assert 0 <= result.overall.score <= 10
