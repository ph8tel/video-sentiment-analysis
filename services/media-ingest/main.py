import asyncio
import os
import shutil
import tempfile

import httpx
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import clients
from merge import merge_transcript_with_speakers

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
NUM_SPEAKERS = int(os.getenv("NUM_SPEAKERS", "2"))

app = FastAPI(title="Media Ingest Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _extract_audio(video_path: str, audio_path: str) -> None:
    """Extract a 16kHz mono WAV track from the source video via FFmpeg."""
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", "16000", "-vn", audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg audio extraction failed: {stderr.decode(errors='replace')[-500:]}",
        )


@app.post("/ingest")
async def ingest(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Source video file (two speakers)."),
):
    """
    Extract audio from the uploaded video, transcribe it with Whisper, diarize
    it with Pyannote, and merge the two into speaker-labeled transcript chunks.
    """
    video_bytes = await video.read()
    if len(video_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Video size exceeds maximum of {MAX_UPLOAD_SIZE_MB} MB.",
        )

    tmpdir = tempfile.mkdtemp()
    background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)

    video_path = os.path.join(tmpdir, "input_video")
    audio_path = os.path.join(tmpdir, "audio.wav")
    with open(video_path, "wb") as fh:
        fh.write(video_bytes)

    await _extract_audio(video_path, audio_path)

    with open(audio_path, "rb") as fh:
        audio_bytes = fh.read()

    try:
        whisper_result, diarization_result = await asyncio.gather(
            clients.call_whisper(audio_bytes),
            clients.call_pyannote(audio_bytes, num_speakers=NUM_SPEAKERS),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream service error ({exc.request.url}): {exc.response.text[:500]}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream service unreachable: {exc}") from exc

    segments = whisper_result.get("segments", [])
    turns = diarization_result.get("complete", [])

    chunks, speaker_order = merge_transcript_with_speakers(segments, turns)

    return {
        "chunks": chunks,
        "speaker_order": speaker_order,
        "meta": diarization_result.get("meta", {}),
    }
