import re
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
EMOJI_ASSET_DIR = Path('services/ffmpeg-overlay/assets/emoji')

# Inclusive score ranges → tone file stem (matches filenames in EMOJI_ASSET_DIR)
_SCORE_RANGES: list[tuple[int, int, str]] = [
    (0,  1,  "very_negative"),
    (2,  2,  "negative"),
    (3,  4,  "slightly_negative"),
    (5,  5,  "neutral"),
    (6,  7,  "slightly_positive"),
    (8,  9,  "positive"),
    (10, 10, "very_positive"),
]


def score_to_tone(score: int) -> str:
    """Return the tone name (emoji file stem) for a sentiment score 0–10."""
    for lo, hi, tone in _SCORE_RANGES:
        if lo <= score <= hi:
            return tone
    raise ValueError(f"score must be 0–10, got {score}")


class TimelineEntry(BaseModel):
    start: float = Field(..., ge=0, description="Chunk start time in seconds.")
    end: float = Field(..., ge=0, description="Chunk end time in seconds.")
    score: int = Field(..., ge=0, le=10, description="Sentiment score (0–10).")
    color: str = Field(..., description="Hex color, e.g. #FF4500.")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_RE.match(v):
            raise ValueError(f"color must be a 6-digit hex string like #FF4500, got {v!r}")
        return v.upper()

    @model_validator(mode="after")
    def end_after_start(self) -> "TimelineEntry":
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be greater than start ({self.start})")
        return self


def hex_to_ffmpeg_color(hex_color: str) -> str:
    """Convert #RRGGBB to 0xRRGGBB (FFmpeg drawbox color syntax)."""
    return "0x" + hex_color.lstrip("#").upper()


def build_filter_chain(entries: List[TimelineEntry], opacity: float = 0.7) -> str:
    """
    Build a comma-separated FFmpeg drawbox filter chain.

    Each entry produces a filter segment:
        drawbox=x=0:y=0:w=200:h=200:color=0xFF4500@0.7:t=fill:enable='between(t,12.4,15.8)'

    The resulting string is safe to pass directly to ``ffmpeg -vf``.
    """
    if not entries:
        raise ValueError("entries must not be empty")

    filters = []
    for entry in entries:
        color = hex_to_ffmpeg_color(entry.color)
        filters.append(
            f"drawbox=x=0:y=0:w=200:h=200:"
            f"color={color}@{opacity:.1f}:t=fill:"
            f"enable='between(t,{entry.start},{entry.end})'"
        )

    return ",".join(filters)


def build_filter_graph(
    entries: List[TimelineEntry],
    emoji_dir: Path = EMOJI_ASSET_DIR,
    emoji_x: int = 68,
    emoji_y: int = 68,
) -> tuple[list[Path], str]:
    """
    Build a full FFmpeg -filter_complex graph that combines drawbox color bands
    with per-chunk emoji overlays.

    Returns
    -------
    emoji_paths : list[Path]
        One Path per timeline entry (may repeat tones). The caller must pass
        each path as a separate ``-i`` argument to FFmpeg, in order starting
        at input index 1. The last path corresponds to input ``[N:v]`` where
        N == len(entries).
    filter_complex : str
        A semicolon-separated filter_complex string ready for ``ffmpeg -filter_complex``.
        The final output stream is labeled ``[out]`` — the caller must pass
        ``-map [out]`` to FFmpeg.
    Raises
    ------
    FileNotFoundError
        If any required emoji PNG is not found in *emoji_dir*. This is a
        deployment error and should fail loudly.
    ValueError
        If *entries* is empty.
    """
    if not entries:
        raise ValueError("entries must not be empty")
    emoji_paths: list[Path] = []
    for entry in entries:
        tone = score_to_tone(entry.score)
        png = emoji_dir / f"{tone}.png"
        if not png.exists():
            raise FileNotFoundError(
                f"Emoji asset missing: {png}. "
                "Ensure assets/emoji/ is present in the deployment image."
            )
        emoji_paths.append(png)
    # Part 1: apply all drawboxes to [0:v] → [boxed]
    drawbox_chain = build_filter_chain(entries)
    parts = [f"[0:v]{drawbox_chain}[boxed]"]
    # Part 2: chain overlay filters, one per entry
    # Input indices: video=0, emoji[0]=1, emoji[1]=2, …
    prev_label = "boxed"
    for i, entry in enumerate(entries):
        out_label = "out" if i == len(entries) - 1 else f"s{i}"
        parts.append(
            f"[{prev_label}][{i + 1}:v]"
            f"overlay={emoji_x}:{emoji_y}:"
            f"enable='between(t,{entry.start},{entry.end})'"
            f"[{out_label}]"
        )
        prev_label = out_label
    return emoji_paths, ";".join(parts)
