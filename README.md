# Video Sentiment Analysis

A pipeline that scores the emotional tone of video transcripts with a local LLM, then bakes colored sentiment overlays directly into the video — no cloud, no vendor lock-in.

---

## How it works

```
transcript.json
    │
    ▼
┌─────────────────────────┐
│  Sentiment Scoring      │  POST /score
│  (Ollama / llama3.1:8b) │  → sentiment_timeline.json
└─────────────────────────┘
    │                  │
    ▼                  ▼
┌──────────────┐  ┌──────────────────┐
│ FFmpeg       │  │ Dashboard UI     │
│ Overlay      │  │ (React / Vite)   │
│ POST /render │  │ localhost:3000   │
│ → video.mp4  │  └──────────────────┘
└──────────────┘
```

Three independent services share a single JSON contract (`sentiment_timeline.json`). Each is testable in isolation — you don't need a running LLM to test the video renderer, and you don't need a video to test the scoring pipeline.

---

## Services

| Service | Port | Input | Output |
|---|---|---|---|
| [ffmpeg-overlay](services/ffmpeg-overlay/) | 8001 | `video.mp4` + timeline JSON | `video_with_overlay.mp4` |
| [sentiment-scoring](services/sentiment-scoring/) | 8002 | `transcript.json` | `sentiment_timeline.json` |
| [dashboard](services/dashboard/) | 3000 | `sentiment_timeline.json` | Interactive visualization |

---

## Prerequisites

- **Docker + Docker Compose** — for running all services
- **Ollama** on your LAN with `llama3.1:8b` pulled:
  ```bash
  ollama pull llama3.1:8b
  ```
- **conda / miniforge** — for local development (avoids system Python conflicts on Ubuntu)

---

## Quick start

```bash
# 1. Copy and edit the env file
cp .env.example .env
# If Ollama runs on another machine, set OLLAMA_HOST to that machine's LAN IP.

# 2. Build and start all services
docker compose up --build

# Services are available at:
#   http://localhost:8001  — FFmpeg Overlay
#   http://localhost:8002  — Sentiment Scoring
#   http://localhost:3000  — Dashboard

# 3. Verify all services are healthy
./smoke_test.sh
```

---

## End-to-end usage

```bash
# 1. Score a transcript
curl -X POST http://localhost:8002/score \
  -H "Content-Type: application/json" \
  -d @examples/sample_transcript.json \
  -o sentiment_timeline.json

# 2. Render a video with overlays
curl -X POST http://localhost:8001/render \
  -F "video=@my_video.mp4" \
  -F "timeline=$(cat sentiment_timeline.json | jq -c '.chunks')" \
  -o video_with_overlay.mp4

# 3. Open the dashboard, drag-and-drop sentiment_timeline.json
open http://localhost:3000
```

---

## Development setup

Each service uses a shared conda environment to avoid conflicts with the system Python on Ubuntu.

```bash
# One-time setup
conda create -n video-overlay python=3.11 -y
conda activate video-overlay
```

Then follow the `README.md` inside each service directory for service-specific install and test commands.

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` for local, `groq` post-MVP |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Address the scoring container can reach; use a LAN IP if Ollama runs on another machine |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model to use for scoring |
| `GROQ_API_KEY` | *(empty)* | Set when switching to Groq |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max video upload size for the overlay service |

Switching from Ollama to Groq post-MVP requires only:
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

When running Docker on Linux, do not set `OLLAMA_HOST` to `http://0.0.0.0:11434` or `http://localhost:11434` for the scoring container. `0.0.0.0` is a bind address, not a destination, and `localhost` inside the container points to the container itself. Use `http://host.docker.internal:11434` when Ollama runs on the same host, or the host machine's LAN IP when Ollama runs elsewhere.

---

## Sentiment tone map


 Tone | Score | Color | Emoji |
|---|---|---|---|
| VERY_NEGATIVE | 0 | `#FF0000` | 😡 |
| NEGATIVE | 2 | `#FF4500` | 😞 |
| SLIGHTLY_NEGATIVE | 3 | `#FFA500` | 😕 |
| NEUTRAL | 5 | `#CCCCCC` | 😐 |
| SLIGHTLY_POSITIVE | 6 | `#90EE90` | 🙂 |
| POSITIVE | 8 | `#32CD32` | 😊 |
| VERY_POSITIVE | 10 | `#008000` | 😄 |
---

Emoji graphics provided by [Twemoji](https://github.com/twitter/twemoji), Copyright 2019 Twitter, Inc and other contributors. Licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## Data schemas

Schemas for both shared JSON contracts live in [`shared/schemas/`](shared/schemas/):

- [`transcript.schema.json`](shared/schemas/transcript.schema.json) — input to the scoring service
- [`sentiment_timeline.schema.json`](shared/schemas/sentiment_timeline.schema.json) — shared contract between all three services

Sample data is in [`examples/`](examples/).

If your source transcript arrives as repeated blocks like:

```text
0:03
3 seconds
okay so but will move against you first
0:10
10 seconds
you'll set up a meeting with someone
```

convert it with:

```bash
/usr/local/bin/python3.12 scripts/convert_transcript.py raw_transcript.txt -o transcript.json
```

The converter uses each timestamp as the chunk `start`, the next timestamp as the prior chunk `end`, and estimates the last chunk length from earlier chunks unless you pass `--last-end` explicitly.

---

## Testing

Each service has its own test suite. Unit and API tests run without any external services (no Ollama, no video files).

```bash
# FFmpeg Overlay — unit + API tests (no FFmpeg or video needed)
cd services/ffmpeg-overlay
make test-unit

# Run all tests including render integration (requires FFmpeg installed)
make test
```

```bash
# Dashboard — Vitest (89 tests, no build step needed)
cd services/dashboard
npm install --cache "$TMPDIR/.npm-cache"
npx vitest run
```

For a live sanity check against running services:
```bash
# Requires: docker compose up --build (see Quick start)
./smoke_test.sh
```
