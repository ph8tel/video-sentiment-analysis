"""
Merge Whisper transcript segments with Pyannote diarization turns.

Each Whisper segment is assigned the speaker label whose diarization turn(s)
overlap it the most. Segments with no overlapping turn (e.g. Whisper picked
up speech in a gap between diarization turns) fall back to the nearest turn
by midpoint distance.
"""

from typing import List, Optional, TypedDict


class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str


class DiarizationTurn(TypedDict):
    start: float
    end: float
    speaker: str


class SpeakerChunk(TypedDict):
    start: float
    end: float
    text: str
    speaker: str


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _distance(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    midpoint = (a_start + a_end) / 2
    if midpoint < b_start:
        return b_start - midpoint
    if midpoint > b_end:
        return midpoint - b_end
    return 0.0


def assign_speaker(segment: TranscriptSegment, turns: List[DiarizationTurn]) -> Optional[str]:
    """Return the speaker label for a transcript segment, or None if no turns exist."""
    if not turns:
        return None

    best_turn = max(
        turns,
        key=lambda t: _overlap(segment["start"], segment["end"], t["start"], t["end"]),
    )
    if _overlap(segment["start"], segment["end"], best_turn["start"], best_turn["end"]) > 0:
        return best_turn["speaker"]

    # No overlapping turn (gap) — fall back to the nearest turn by midpoint distance.
    nearest_turn = min(
        turns,
        key=lambda t: _distance(segment["start"], segment["end"], t["start"], t["end"]),
    )
    return nearest_turn["speaker"]


def merge_transcript_with_speakers(
    segments: List[TranscriptSegment],
    turns: List[DiarizationTurn],
) -> tuple[List[SpeakerChunk], List[str]]:
    """
    Assign a speaker label to each transcript segment and return the chunks
    alongside the speaker labels in order of first appearance.
    """
    chunks: List[SpeakerChunk] = []
    speaker_order: List[str] = []

    for segment in segments:
        speaker = assign_speaker(segment, turns) or "UNKNOWN"
        if speaker not in speaker_order:
            speaker_order.append(speaker)
        chunks.append(
            {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "speaker": speaker,
            }
        )

    return chunks, speaker_order
