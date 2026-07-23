# FFmpeg Overlay Service

Accepts a video file and a sentiment timeline, generates a drawbox filter chain, and returns a rendered MP4 with colored sentiment overlays baked in.

Port: **8001**

---

## API

### `GET /health`
Returns `{"status": "ok"}`. Use this to confirm the service is running.

---

### `POST /preview`
Returns the FFmpeg filter chain string without rendering anything. Useful for debugging and for testing your timeline JSON before committing to a full render.

**Request** — `application/json`
```json
[
  {"start": 0.0,  "end": 3.2,  "score": 6, "color": "#90EE90"},
  {"start": 3.2,  "end": 7.5,  "score": 8, "color": "#32CD32"},
  {"start": 7.5,  "end": 12.1, "score": 2, "color": "#FF4500"}
]
```

**Response**
```json
{
  "filter_chain": "drawbox=x=0:y=0:w=200:h=200:color=0x90EE90@0.70:t=fill:enable='between(t,0.0,3.2)',drawbox=..."
}
```

---

### `POST /render`
Renders a new MP4 with sentiment overlays. Accepts `multipart/form-data`.

| Field | Type | Description |
|---|---|---|
| `video` | file | Source `.mp4` video |
| `timeline` | string | JSON array of `TimelineEntry` objects (same shape as `/preview`) |

**Example with curl:**
```bash
curl -X POST http://localhost:8001/render \
  -F "video=@my_video.mp4" \
  -F 'timeline=[{"start":0,"end":3.2,"score":6,"color":"#90EE90"}]' \
  -o video_with_overlay.mp4
```

**Response** — `video/mp4` file download

---

## Timeline entry fields

| Field | Type | Constraints | Description |
|---|---|---|---|
| `start` | float | ≥ 0 | Chunk start time in seconds |
| `end` | float | > `start` | Chunk end time in seconds |
| `score` | int | 0–10 | Sentiment score |
| `color` | string | `#RRGGBB` | Hex color for the overlay box |

The `sentiment_timeline.json` produced by the scoring service includes additional fields (`tone`, `text`) which are silently ignored by this service — you can pass `chunks` from the timeline directly.

---

## How the overlay works

Each timeline entry becomes a single FFmpeg `drawbox` filter segment:

```
drawbox=x=0:y=0:w=200:h=200:color=0xFF4500@0.70:t=fill:enable='between(t,12.4,15.8)'
```

All segments are joined with commas and passed to `ffmpeg -vf`. FFmpeg applies each box only during its time window, so the overlay color changes in real time as the video plays.

Note: FFmpeg requires `0x` prefix for hex colors — the service converts `#RRGGBB` automatically.

---

## Development setup

This service uses the shared `video-overlay` conda environment (Python 3.11, matching the Docker image).

```bash
# One-time: create the conda env from the repo root
conda create -n video-overlay python=3.11 -y
conda activate video-overlay

# Install dev dependencies
cd services/ffmpeg-overlay
pip install -r requirements-dev.txt
```

### Run the service locally

```bash
uvicorn main:app --reload --port 8001
```

---

## Tests

```bash
conda activate video-overlay
cd services/ffmpeg-overlay

# Unit + API tests — no FFmpeg or video files required
make test-unit

# All tests including render (requires FFmpeg installed: `sudo apt install ffmpeg`)
make test
```

### Test structure

| File | What it tests | Requires FFmpeg? |
|---|---|---|
| `tests/test_filter_generator.py` | `hex_to_ffmpeg_color`, `build_filter_chain`, Pydantic validation | No |
| `tests/test_preview.py` | `/health`, `/preview` endpoints | No |
| `tests/test_render.py` | `/render` endpoint (valid video, error cases) | Yes (auto-skipped if absent) |

The render tests generate a 1-second 320×240 black H.264 MP4 at test-session scope using FFmpeg's `lavfi` source — no binary test fixture is committed to the repo.

---

## Docker

```bash
# Build
docker build -t ffmpeg-overlay .

# Run standalone
docker run -p 8001:8001 -e MAX_UPLOAD_SIZE_MB=500 ffmpeg-overlay

# Or via Docker Compose from the repo root
docker compose up ffmpeg-overlay
```

The image is based on `python:3.11-slim` with `ffmpeg` installed via `apt`.
