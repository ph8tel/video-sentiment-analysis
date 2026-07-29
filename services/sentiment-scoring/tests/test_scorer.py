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
    _EmotionResponse,
    _LLMResponse,
    build_emotion_prompt,
    build_prompt,
    parse_emotion_response,
    parse_llm_response,
    score_chunk,
    score_emotions,
    score_transcript,
)
from tests.conftest import MockLLMClient, NEUTRAL_EMOTION_RESPONSE, make_emotion_mock


# ---------------------------------------------------------------------------
# Sentiment tone prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Emotion prompt
# ---------------------------------------------------------------------------

class TestBuildEmotionPrompt:
    def test_includes_chunk_text(self):
        prompt = build_emotion_prompt("Hello world")
        assert "Hello world" in prompt

    def test_mentions_anger_level(self):
        assert "anger_level" in build_emotion_prompt("test")

    def test_mentions_frustration_level(self):
        assert "frustration_level" in build_emotion_prompt("test")

    def test_mentions_sarcasm_flag(self):
        assert "sarcasm_flag" in build_emotion_prompt("test")

    def test_mentions_scale_0_to_3(self):
        prompt = build_emotion_prompt("test")
        assert "0" in prompt and "3" in prompt

    def test_instructs_json_only_output(self):
        assert "JSON" in build_emotion_prompt("test").upper()


class TestParseEmotionResponse:
    def test_valid_response_returns_model(self):
        raw = json.dumps({"anger_level": 1, "frustration_level": 2, "sarcasm_flag": False})
        result = parse_emotion_response(raw)
        assert result.anger_level == 1
        assert result.frustration_level == 2
        assert result.sarcasm_flag is False

    def test_sarcasm_true_accepted(self):
        raw = json.dumps({"anger_level": 0, "frustration_level": 0, "sarcasm_flag": True})
        assert parse_emotion_response(raw).sarcasm_flag is True

    def test_boundary_values_zero(self):
        raw = json.dumps({"anger_level": 0, "frustration_level": 0, "sarcasm_flag": False})
        result = parse_emotion_response(raw)
        assert result.anger_level == 0
        assert result.frustration_level == 0

    def test_boundary_values_three(self):
        raw = json.dumps({"anger_level": 3, "frustration_level": 3, "sarcasm_flag": True})
        result = parse_emotion_response(raw)
        assert result.anger_level == 3
        assert result.frustration_level == 3

    def test_extra_fields_are_ignored(self):
        raw = json.dumps({"anger_level": 0, "frustration_level": 0, "sarcasm_flag": False, "extra": "x"})
        result = parse_emotion_response(raw)
        assert result.anger_level == 0

    def test_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_emotion_response("not json")

    def test_anger_level_above_3_raises_value_error(self):
        raw = json.dumps({"anger_level": 4, "frustration_level": 0, "sarcasm_flag": False})
        with pytest.raises(ValueError):
            parse_emotion_response(raw)

    def test_frustration_level_below_0_raises_value_error(self):
        raw = json.dumps({"anger_level": 0, "frustration_level": -1, "sarcasm_flag": False})
        with pytest.raises(ValueError):
            parse_emotion_response(raw)

    def test_missing_anger_level_raises_value_error(self):
        raw = json.dumps({"frustration_level": 0, "sarcasm_flag": False})
        with pytest.raises(ValueError):
            parse_emotion_response(raw)

    def test_missing_sarcasm_flag_raises_value_error(self):
        raw = json.dumps({"anger_level": 0, "frustration_level": 0})
        with pytest.raises(ValueError):
            parse_emotion_response(raw)


# ---------------------------------------------------------------------------
# score_emotions()
# ---------------------------------------------------------------------------

class TestScoreEmotions:
    async def test_calls_client_complete(self):
        calls = []

        class TrackingClient(MockLLMClient):
            async def complete(self, prompt: str) -> str:
                calls.append(prompt)
                return NEUTRAL_EMOTION_RESPONSE

        chunk = TranscriptChunk(start=0.0, end=3.0, text="Hello world")
        await score_emotions(chunk, TrackingClient())
        assert len(calls) == 1
        assert "Hello world" in calls[0]

    async def test_returns_emotion_response(self):
        raw = json.dumps({"anger_level": 2, "frustration_level": 1, "sarcasm_flag": True})
        chunk = TranscriptChunk(start=0.0, end=3.0, text="test")
        result = await score_emotions(chunk, MockLLMClient(responses=[raw]))
        assert isinstance(result, _EmotionResponse)
        assert result.anger_level == 2
        assert result.sarcasm_flag is True

    async def test_propagates_llm_error(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(RuntimeError, match="timeout"):
            await score_emotions(chunk, MockLLMClient(raises=RuntimeError("timeout")))


# ---------------------------------------------------------------------------
# score_chunk()
# ---------------------------------------------------------------------------

class TestScoreChunk:
    async def test_calls_tone_client(self):
        calls = []

        class TrackingClient(MockLLMClient):
            async def complete(self, prompt: str) -> str:
                calls.append(prompt)
                return json.dumps({"tone": "NEUTRAL", "score": 5})

        chunk = TranscriptChunk(start=0.0, end=3.0, text="Hello world")
        await score_chunk(chunk, TrackingClient(), make_emotion_mock())
        assert len(calls) == 1
        assert "Hello world" in calls[0]

    async def test_calls_emotion_client(self):
        emotion_calls = []

        class TrackingEmotionClient(MockLLMClient):
            async def complete(self, prompt: str) -> str:
                emotion_calls.append(prompt)
                return NEUTRAL_EMOTION_RESPONSE

        chunk = TranscriptChunk(start=0.0, end=3.0, text="Angry text!")
        tone_client = MockLLMClient(responses=[json.dumps({"tone": "NEUTRAL", "score": 5})])
        await score_chunk(chunk, tone_client, TrackingEmotionClient())
        assert len(emotion_calls) == 1
        assert "Angry text!" in emotion_calls[0]

    async def test_returns_scored_chunk_with_all_fields(self):
        tone_resp    = json.dumps({"tone": "POSITIVE", "score": 8})
        emotion_resp = json.dumps({"anger_level": 1, "frustration_level": 0, "sarcasm_flag": True})
        chunk = TranscriptChunk(start=1.0, end=4.0, text="Great job")
        result = await score_chunk(
            chunk,
            MockLLMClient(responses=[tone_resp]),
            MockLLMClient(responses=[emotion_resp], fallback=NEUTRAL_EMOTION_RESPONSE),
        )
        assert isinstance(result, ScoredChunk)
        assert result.tone == Tone.POSITIVE
        assert result.score == 8
        assert result.anger_level == 1
        assert result.frustration_level == 0
        assert result.sarcasm_flag is True

    async def test_color_matches_tone(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="Bad news")
        result = await score_chunk(
            chunk,
            MockLLMClient(responses=[json.dumps({"tone": "NEGATIVE", "score": 2})]),
            make_emotion_mock(),
        )
        assert result.color == tone_to_color(Tone.NEGATIVE)

    async def test_propagates_tone_llm_error(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(RuntimeError, match="timeout"):
            await score_chunk(
                chunk,
                MockLLMClient(raises=RuntimeError("timeout")),
                make_emotion_mock(),
            )

    async def test_propagates_emotion_llm_error(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(RuntimeError, match="emotion fail"):
            await score_chunk(
                chunk,
                MockLLMClient(responses=[json.dumps({"tone": "NEUTRAL", "score": 5})]),
                MockLLMClient(raises=RuntimeError("emotion fail")),
            )

    async def test_raises_on_invalid_tone_response(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(ValueError, match="invalid JSON"):
            await score_chunk(chunk, MockLLMClient(responses=["not valid json"]), make_emotion_mock())

    async def test_raises_on_invalid_emotion_response(self):
        chunk = TranscriptChunk(start=0.0, end=2.0, text="test")
        with pytest.raises(ValueError, match="invalid JSON"):
            await score_chunk(
                chunk,
                MockLLMClient(responses=[json.dumps({"tone": "NEUTRAL", "score": 5})]),
                MockLLMClient(responses=["not valid emotion json"]),
            )


# ---------------------------------------------------------------------------
# score_transcript()
# ---------------------------------------------------------------------------

class TestScoreTranscript:
    async def test_scores_all_chunks(self):
        tone_responses = [
            json.dumps({"tone": "POSITIVE",  "score": 8}),
            json.dumps({"tone": "NEUTRAL",   "score": 5}),
            json.dumps({"tone": "NEGATIVE",  "score": 2}),
        ]
        chunks = [
            TranscriptChunk(start=0.0, end=3.0, text="Great"),
            TranscriptChunk(start=3.0, end=6.0, text="Okay"),
            TranscriptChunk(start=6.0, end=9.0, text="Bad"),
        ]
        result = await score_transcript(
            chunks,
            MockLLMClient(responses=tone_responses),
            make_emotion_mock(),
        )
        assert len(result.chunks) == 3

    async def test_chunks_include_emotion_fields(self):
        chunks = [TranscriptChunk(start=0.0, end=3.0, text="test")]
        emotion_resp = json.dumps({"anger_level": 2, "frustration_level": 1, "sarcasm_flag": True})
        result = await score_transcript(
            chunks,
            MockLLMClient(),
            MockLLMClient(responses=[emotion_resp], fallback=NEUTRAL_EMOTION_RESPONSE),
        )
        chunk = result.chunks[0]
        assert chunk.anger_level == 2
        assert chunk.frustration_level == 1
        assert chunk.sarcasm_flag is True

    async def test_overall_is_duration_weighted(self):
        # Chunk 1: score=8, duration=6s → weight 6
        # Chunk 2: score=2, duration=2s → weight 2
        # Weighted avg = (8*6 + 2*2) / (6+2) = 52/8 = 6.5
        tone_responses = [
            json.dumps({"tone": "POSITIVE",  "score": 8}),
            json.dumps({"tone": "NEGATIVE",  "score": 2}),
        ]
        chunks = [
            TranscriptChunk(start=0.0, end=6.0, text="Good"),
            TranscriptChunk(start=6.0, end=8.0, text="Bad"),
        ]
        result = await score_transcript(
            chunks,
            MockLLMClient(responses=tone_responses),
            make_emotion_mock(),
        )
        assert result.overall.score == 6.5

    async def test_overall_tone_derived_from_score(self):
        chunks = [TranscriptChunk(start=0.0, end=1.0, text="OK")]
        result = await score_transcript(chunks, MockLLMClient(), make_emotion_mock())
        assert result.overall.tone == Tone.NEUTRAL

    async def test_result_contains_required_fields(self):
        chunks = [TranscriptChunk(start=0.0, end=3.0, text="Pretty good")]
        result = await score_transcript(
            chunks,
            MockLLMClient(responses=[json.dumps({"tone": "SLIGHTLY_POSITIVE", "score": 6})]),
            make_emotion_mock(),
        )
        chunk = result.chunks[0]
        assert chunk.color.startswith("#")
        assert chunk.text == "Pretty good"
        assert hasattr(chunk, "anger_level")
        assert hasattr(chunk, "frustration_level")
        assert hasattr(chunk, "sarcasm_flag")
        assert 0 <= result.overall.score <= 10

