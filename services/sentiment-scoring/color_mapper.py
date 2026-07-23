from enum import Enum
from typing import NamedTuple


class Tone(str, Enum):
    VERY_NEGATIVE     = "VERY_NEGATIVE"
    NEGATIVE          = "NEGATIVE"
    SLIGHTLY_NEGATIVE = "SLIGHTLY_NEGATIVE"
    NEUTRAL           = "NEUTRAL"
    SLIGHTLY_POSITIVE = "SLIGHTLY_POSITIVE"
    POSITIVE          = "POSITIVE"
    VERY_POSITIVE     = "VERY_POSITIVE"


class ToneInfo(NamedTuple):
    score: int
    hex_color: str


# Canonical score and color for each tone level.
TONE_MAP: dict[Tone, ToneInfo] = {
    Tone.VERY_NEGATIVE:     ToneInfo(score=0,  hex_color="#FF0000"),
    Tone.NEGATIVE:          ToneInfo(score=2,  hex_color="#FF4500"),
    Tone.SLIGHTLY_NEGATIVE: ToneInfo(score=3,  hex_color="#FFA500"),
    Tone.NEUTRAL:           ToneInfo(score=5,  hex_color="#CCCCCC"),
    Tone.SLIGHTLY_POSITIVE: ToneInfo(score=6,  hex_color="#90EE90"),
    Tone.POSITIVE:          ToneInfo(score=8,  hex_color="#32CD32"),
    Tone.VERY_POSITIVE:     ToneInfo(score=10, hex_color="#008000"),
}


def tone_to_color(tone: Tone) -> str:
    """Return the hex color string for a given tone."""
    return TONE_MAP[tone].hex_color


def resolve_tie(candidates: list["Tone"], score: float) -> "Tone":
    """
    Choose one tone when two candidates are equidistant from *score*.

    Currently returns the lower-scoring tone. This is the designated hook
    for future correction logic, e.g.:
      - re-scoring with a larger model
      - averaging multiple model samples
      - applying contextual window bias
    """
    return min(candidates, key=lambda t: TONE_MAP[t].score)


def score_to_tone(score: float) -> Tone:
    """
    Map a numeric score (0–10) to the nearest tone label.

    When the score falls exactly midway between two tones, ``resolve_tie``
    is called so that the tie-breaking strategy can be swapped independently.
    """
    min_diff = min(abs(TONE_MAP[t].score - score) for t in TONE_MAP)
    candidates = [t for t in TONE_MAP if abs(TONE_MAP[t].score - score) == min_diff]
    if len(candidates) == 1:
        return candidates[0]
    return resolve_tie(candidates, score)
