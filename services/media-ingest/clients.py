"""
HTTP clients for the external Whisper STT and Pyannote diarization services.

Both services run on the host LAN (not in this Docker network) — see
WHISPER_URL / PYANNOTE_URL in main.py.
"""

import os

import httpx

WHISPER_URL = os.getenv("WHISPER_URL", "http://192.168.1.188:5000")
PYANNOTE_URL = os.getenv("PYANNOTE_URL", "http://192.168.1.188:3003")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("MEDIA_INGEST_TIMEOUT", "600"))


async def call_whisper(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    """POST audio to the Whisper /stt endpoint, return {text, segments}."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{WHISPER_URL}/stt",
            files={"audio": (filename, audio_bytes, "audio/wav")},
        )
        response.raise_for_status()
        return response.json()


async def call_pyannote(audio_bytes: bytes, num_speakers: int, filename: str = "audio.wav") -> dict:
    """POST audio to the Pyannote /diarize endpoint, return the diarization payload."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{PYANNOTE_URL}/diarize",
            files={"file": (filename, audio_bytes, "audio/wav")},
            data={"num_speakers": str(num_speakers)},
        )
        response.raise_for_status()
        return response.json()
