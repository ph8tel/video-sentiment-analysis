"""
Sentiment scoring pipeline.

Responsibilities
────────────────
  - Define the data models used across the service
  - Build the LLM prompts (sentiment tone + emotion analysis)
  - Parse and validate the LLM's JSON responses
  - Score individual chunks and aggregate an overall result
"""

import json

from pydantic import BaseModel, Field, ValidationError

from color_mapper import Tone, score_to_tone, tone_to_color
from llm_client import LLMClient

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class TranscriptChunk(BaseModel):
    start: float = Field(..., ge=0, description="Chunk start time in seconds.")
    end:   float = Field(..., ge=0, description="Chunk end time in seconds.")
    text:  str   = Field(..., min_length=1, description="Spoken text for this chunk.")


class ScoredChunk(BaseModel):
    start:             float
    end:               float
    tone:              Tone
    score:             int  = Field(..., ge=0, le=10)
    color:             str
    text:              str
    anger_level:       int  = Field(..., ge=0, le=3)
    frustration_level: int  = Field(..., ge=0, le=3)
    sarcasm_flag:      bool


class OverallScore(BaseModel):
    score: float = Field(..., ge=0, le=10)
    tone:  Tone


class SentimentResult(BaseModel):
    chunks:  list[ScoredChunk]
    overall: OverallScore


# ---------------------------------------------------------------------------
# Sentiment tone prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a sentiment analysis assistant. Analyze the emotional tone of the text.

Respond ONLY with a JSON object in exactly this format:
{"tone": "<TONE>", "score": <NUMBER>}

Rules:
- "tone" must be exactly one of: VERY_NEGATIVE, NEGATIVE, SLIGHTLY_NEGATIVE, NEUTRAL, SLIGHTLY_POSITIVE, POSITIVE, VERY_POSITIVE
- "score" must be an integer from 0 to 10
- Score guide: VERY_NEGATIVE=0, NEGATIVE=2, SLIGHTLY_NEGATIVE=3, NEUTRAL=5, SLIGHTLY_POSITIVE=6, POSITIVE=8, VERY_POSITIVE=10

No explanation. No extra fields. JSON only.\
"""


def build_prompt(text: str) -> str:
    return f"{_SYSTEM_PROMPT}\n\nText to analyze:\n{text}"


# ---------------------------------------------------------------------------
# Emotion prompt (anger, frustration, sarcasm)
# ---------------------------------------------------------------------------

_EMOTION_SYSTEM_PROMPT = """\
You are an emotion analysis assistant. Detect anger, frustration, and sarcasm in the text.

Respond ONLY with a JSON object in exactly this format:
{"anger_level": <NUMBER>, "frustration_level": <NUMBER>, "sarcasm_flag": <BOOLEAN>}

Rules:
- "anger_level" must be an integer from 0 to 3 (0=none, 1=mild, 2=strong, 3=intense)
- "frustration_level" must be an integer from 0 to 3 (0=none, 1=mild, 2=strong, 3=intense)
- "sarcasm_flag" must be true or false

No explanation. No extra fields. JSON only.\
"""


def build_emotion_prompt(text: str) -> str:
    return f"{_EMOTION_SYSTEM_PROMPT}\n\nText to analyze:\n{text}"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class _LLMResponse(BaseModel):
    tone:  Tone
    score: int = Field(..., ge=0, le=10)


def parse_llm_response(raw: str) -> _LLMResponse:
    """
    Parse and validate the LLM's JSON output for tone/score.

    Raises ValueError on invalid JSON or schema violations so the caller
    can return a clean HTTP error rather than an unhandled exception.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc!s}\nRaw: {raw!r}") from exc

    try:
        return _LLMResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"LLM response failed validation: {exc!s}\nRaw: {raw!r}"
        ) from exc


class _EmotionResponse(BaseModel):
    anger_level:       int  = Field(..., ge=0, le=3)
    frustration_level: int  = Field(..., ge=0, le=3)
    sarcasm_flag:      bool


def parse_emotion_response(raw: str) -> _EmotionResponse:
    """
    Parse and validate the LLM's JSON output for anger/frustration/sarcasm.

    Raises ValueError on invalid JSON or schema violations.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc!s}\nRaw: {raw!r}") from exc

    try:
        return _EmotionResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError(
            f"LLM emotion response failed validation: {exc!s}\nRaw: {raw!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

async def score_emotions(chunk: TranscriptChunk, client: LLMClient) -> _EmotionResponse:
    """Score anger, frustration, and sarcasm for a single chunk."""
    prompt = build_emotion_prompt(chunk.text)
    raw    = await client.complete(prompt)
    return parse_emotion_response(raw)


async def score_chunk(
    chunk: TranscriptChunk,
    client: LLMClient,
    emotion_client: LLMClient,
) -> ScoredChunk:
    """Score tone/sentiment and emotions for a single transcript chunk."""
    prompt = build_prompt(chunk.text)
    raw    = await client.complete(prompt)
    result = parse_llm_response(raw)

    emotion = await score_emotions(chunk, emotion_client)

    return ScoredChunk(
        start=chunk.start,
        end=chunk.end,
        tone=result.tone,
        score=result.score,
        color=tone_to_color(result.tone),
        text=chunk.text,
        anger_level=emotion.anger_level,
        frustration_level=emotion.frustration_level,
        sarcasm_flag=emotion.sarcasm_flag,
    )


async def score_transcript(
    chunks: list[TranscriptChunk],
    client: LLMClient,
    emotion_client: LLMClient,
) -> SentimentResult:
    """
    Score all chunks and compute a duration-weighted overall sentiment.

    Chunks are scored sequentially to respect Ollama's concurrency limits.
    Two LLM calls are made per chunk: one for tone/score, one for emotions.
    """
    scored: list[ScoredChunk] = []
    for chunk in chunks:
        scored.append(await score_chunk(chunk, client, emotion_client))

    # Duration-weighted average: longer chunks count for more
    total_duration = sum(c.end - c.start for c in scored)
    if total_duration > 0:
        overall_score = sum(
            c.score * (c.end - c.start) for c in scored
        ) / total_duration
    else:
        overall_score = sum(c.score for c in scored) / len(scored)

    overall_score = round(overall_score, 2)
    return SentimentResult(
        chunks=scored,
        overall=OverallScore(
            score=overall_score,
            tone=score_to_tone(overall_score),
        ),
    )
