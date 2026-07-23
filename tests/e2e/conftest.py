"""
E2E test suite — added post-MVP once all three services are stable.

Strategy
────────
E2E tests call the live services over HTTP (Docker Compose must be running).
They test the full pipeline:

  sample_transcript.json
      → POST http://localhost:8002/score
      → sentiment_timeline.json
      → POST http://localhost:8001/render  (with a test video)
      → video_with_overlay.mp4

Required env vars (or defaults):
  FFMPEG_OVERLAY_URL  = http://localhost:8001
  SENTIMENT_SCORE_URL = http://localhost:8002
  DASHBOARD_URL       = http://localhost:3000

Run with:
  docker compose up -d
  pytest tests/e2e/ -v
"""
