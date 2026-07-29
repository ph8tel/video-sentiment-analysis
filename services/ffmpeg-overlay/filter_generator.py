import re
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
EMOJI_ASSET_DIR = Path(__file__).parent / 'assets' / 'emoji'

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

# Anger level → emoji file stem  (😐=0, 😠=1, 😡=2, 💥=3)
_ANGER_LEVELS: list[tuple[int, str]] = [
    (0, "anger_0"),
    (1, "anger_1"),
    (2, "anger_2"),
    (3, "anger_3"),
]

# Frustration level → emoji file stem  (😐=0, 😤=1, 😣=2, 🤬=3)
_FRUSTRATION_LEVELS: list[tuple[int, str]] = [
    (0, "frustration_0"),
    (1, "frustration_1"),
    (2, "frustration_2"),
    (3, "frustration_3"),
]


def score_to_tone(score: int) -> str:
    """Return the tone name (emoji file stem) for a sentiment score 0–10."""
    for lo, hi, tone in _SCORE_RANGES:
        if lo <= score <= hi:
            return tone
    raise ValueError(f"score must be 0–10, got {score}")


def anger_level_to_emoji(level: int) -> str:
    """Return the emoji file stem for an anger level 0–3."""
    for lvl, stem in _ANGER_LEVELS:
        if level == lvl:
            return stem
    raise ValueError(f"anger_level must be 0–3, got {level}")


def frustration_level_to_emoji(level: int) -> str:
    """Return the emoji file stem for a frustration level 0–3."""
    for lvl, stem in _FRUSTRATION_LEVELS:
        if level == lvl:
            return stem
    raise ValueError(f"frustration_level must be 0–3, got {level}")


class TimelineEntry(BaseModel):
    start:             float = Field(..., ge=0, description="Chunk start time in seconds.")
    end:               float = Field(..., ge=0, description="Chunk end time in seconds.")
    score:             int   = Field(..., ge=0, le=10, description="Sentiment score (0–10).")
    color:             str   = Field(..., description="Hex color, e.g. #FF4500.")
    anger_level:       int   = Field(0, ge=0, le=3, description="Anger intensity (0–3).")
    frustration_level: int   = Field(0, ge=0, le=3, description="Frustration intensity (0–3).")

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
    emoji_dir: Path | None = None,
    emoji_x: int = 68,
    emoji_y: int = 68,
    anger_x: int = 2,
    anger_y: int = 202,
    frustration_x: int = 2,
    frustration_y: int = 270,
) -> tuple[list[Path], str]:
    """
    Build a full FFmpeg -filter_complex graph combining drawbox colour bands
    with three rows of per-chunk emoji overlays:

      Row 1 (sentiment):    positioned at (emoji_x, emoji_y)
      Row 2 (anger):        positioned at (anger_x, anger_y)
      Row 3 (frustration):  positioned at (frustration_x, frustration_y)

    Returns
    -------
    emoji_paths : list[Path]
        3 × N paths (N = len(entries)), ordered as all sentiment paths,
        then all anger paths, then all frustration paths.  The caller must
        pass each as a separate ``-i`` argument to FFmpeg starting at index 1.
    filter_complex : str
        Semicolon-separated filter_complex string ready for
        ``ffmpeg -filter_complex``.  Final output stream is labelled ``[out]``.

    Raises
    ------
    FileNotFoundError
        If any required emoji PNG is missing from *emoji_dir*.
    ValueError
        If *entries* is empty.
    """
    if emoji_dir is None:
        emoji_dir = EMOJI_ASSET_DIR
    if not entries:
        raise ValueError("entries must not be empty")

    sentiment_paths: list[Path] = []
    anger_paths:     list[Path] = []
    frustration_paths: list[Path] = []

    for entry in entries:
        tone = score_to_tone(entry.score)
        png = emoji_dir / f"{tone}.png"
        if not png.exists():
            raise FileNotFoundError(
                f"Emoji asset missing: {png}. "
                "Ensure assets/emoji/ is present in the deployment image."
            )
        sentiment_paths.append(png)

        anger_stem = anger_level_to_emoji(entry.anger_level)
        anger_png = emoji_dir / f"{anger_stem}.png"
        if not anger_png.exists():
            raise FileNotFoundError(
                f"Emoji asset missing: {anger_png}. "
                "Ensure assets/emoji/ is present in the deployment image."
            )
        anger_paths.append(anger_png)

        frust_stem = frustration_level_to_emoji(entry.frustration_level)
        frust_png = emoji_dir / f"{frust_stem}.png"
        if not frust_png.exists():
            raise FileNotFoundError(
                f"Emoji asset missing: {frust_png}. "
                "Ensure assets/emoji/ is present in the deployment image."
            )
        frustration_paths.append(frust_png)

    # Emoji inputs are ordered: all sentiment, then all anger, then all frustration.
    # FFmpeg input indices: 0=video, 1..N=sentiment, N+1..2N=anger, 2N+1..3N=frustration
    all_emoji_paths = sentiment_paths + anger_paths + frustration_paths
    n = len(entries)
    total_overlays = n * 3  # 3 rows per chunk

    # Part 1: apply all drawboxes to [0:v] → [boxed]
    drawbox_chain = build_filter_chain(entries)
    parts = [f"[0:v]{drawbox_chain}[boxed]"]

    # Parts 2-4: chain overlay filters for each row.
    # Intermediate stream labels: p0, p1, … p{total_overlays-2}, then [out].
    prev_label = "boxed"
    label_idx  = 0  # counter for intermediate labels

    def _overlay_part(input_idx: int, x: int, y: int, entry: TimelineEntry) -> str:
        nonlocal prev_label, label_idx
        is_last  = (label_idx == total_overlays - 1)
        out_label = "out" if is_last else f"p{label_idx}"
        part = (
            f"[{prev_label}][{input_idx}:v]"
            f"overlay={x}:{y}:"
            f"enable='between(t,{entry.start},{entry.end})'"
            f"[{out_label}]"
        )
        prev_label = out_label
        label_idx += 1
        return part

    # Row 1 — sentiment emoji (input indices 1..N)
    for i, entry in enumerate(entries):
        parts.append(_overlay_part(i + 1, emoji_x, emoji_y, entry))

    # Row 2 — anger emoji (input indices N+1..2N)
    for i, entry in enumerate(entries):
        parts.append(_overlay_part(n + i + 1, anger_x, anger_y, entry))

    # Row 3 — frustration emoji (input indices 2N+1..3N)
    for i, entry in enumerate(entries):
        parts.append(_overlay_part(2 * n + i + 1, frustration_x, frustration_y, entry))

    return all_emoji_paths, ";".join(parts)

