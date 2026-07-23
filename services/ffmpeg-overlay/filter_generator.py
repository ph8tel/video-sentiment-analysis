import re
from typing import List

from pydantic import BaseModel, Field, field_validator, model_validator

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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
        drawbox=x=0:y=0:w=200:h=200:color=0xFF4500@0.70:t=fill:enable='between(t,12.4,15.8)'

    The resulting string is safe to pass directly to ``ffmpeg -vf``.
    """
    if not entries:
        raise ValueError("entries must not be empty")

    filters = []
    for entry in entries:
        color = hex_to_ffmpeg_color(entry.color)
        filters.append(
            f"drawbox=x=0:y=0:w=200:h=200:"
            f"color={color}@{opacity:.2f}:t=fill:"
            f"enable='between(t,{entry.start},{entry.end})'"
        )

    return ",".join(filters)
