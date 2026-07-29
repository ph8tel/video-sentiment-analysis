import asyncio
import json
import os
import shutil
import tempfile
from typing import List
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from filter_generator import TimelineEntry, build_filter_chain, build_filter_graph

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

app = FastAPI(title="FFmpeg Overlay Service", version="0.1.0")

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


@app.post("/preview")
async def preview(timeline: List[TimelineEntry]):
    """Return filter strings for a given timeline without rendering."""
    if not timeline:
        raise HTTPException(status_code=422, detail="timeline must not be empty")

    result: dict = {"filter_chain": build_filter_chain(timeline)}
    try:
        _, filter_complex = build_filter_graph(timeline)
        result["filter_complex"] = filter_complex
    except FileNotFoundError:
        # Assets not present in this environment (e.g. bare dev checkout
        # without the emoji directory); degrade gracefully for preview only.
        pass
    return result      

@app.post("/render")
async def render(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Source MP4 video file."),
    timeline: str = Form(..., description="JSON array of TimelineEntry objects."),
):
    """
    Render a video with sentiment color overlays baked in.

    Accepts a multipart/form-data request with:
    - ``video``: the source MP4 file
    - ``timeline``: a JSON string (array of TimelineEntry objects)

    Returns the rendered MP4 as a file download.
    """
    # --- upload size guard ---
    video_bytes = await video.read()
    if len(video_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Video size exceeds maximum of {MAX_UPLOAD_SIZE_MB} MB.",
        )

    # --- validate timeline ---
    try:
        raw = json.loads(timeline)
        if not isinstance(raw, list):
            raise TypeError("timeline must be a JSON array")
        entries: List[TimelineEntry] = [TimelineEntry(**e) for e in raw]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid timeline: {exc}") from exc

    if not entries:
        raise HTTPException(status_code=422, detail="timeline must not be empty")

    filter_chain = build_filter_chain(entries)

    # --- run FFmpeg in a subprocess (non-blocking) ---
    tmpdir = tempfile.mkdtemp()
    # clean up the temp dir after the response is sent
    background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)

    input_path = os.path.join(tmpdir, "input.mp4")
    output_path = os.path.join(tmpdir, "output.mp4")

    with open(input_path, "wb") as fh:
        fh.write(video_bytes)

    emoji_paths, filter_complex = build_filter_graph(entries)
    # Copy emoji PNGs into tmpdir so subprocess paths are simple and safe
    local_emoji: list[str] = []

    for idx , src in enumerate(emoji_paths):
        dst = os.path.join(tmpdir, f"emoji_{idx}.png")
        shutil.copy2(src, dst)
        local_emoji.append(dst)
    # Build FFmpeg command with multiple inputs and filter_complex
    cmd = ["ffmpeg", "-y", "-i", input_path]
    for ep in local_emoji:
        cmd += ["-i", ep]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "copy",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg error: {stderr.decode(errors='replace')[-500:]}",
        )

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="video_with_overlay.mp4",
    )
