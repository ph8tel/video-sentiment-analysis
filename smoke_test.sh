#!/usr/bin/env bash
# smoke_test.sh — end-to-end smoke test against running services.
#
# Usage:
#   ./smoke_test.sh                        # assumes services up on localhost
#   FFMPEG_URL=http://localhost:8001 \
#   SCORING_URL=http://localhost:8002 \
#   MEDIA_INGEST_URL=http://localhost:8003 \
#   ./smoke_test.sh
#
# The media-ingest test uploads examples/lil_brit_raw.mp4 and calls out to the
# live Whisper/Pyannote services (WHISPER_URL/PYANNOTE_URL, default LAN host
# 192.168.1.188) — it can take a couple of minutes and requires those services
# to be reachable.
#
# Requires: curl, jq
set -euo pipefail

FFMPEG_URL="${FFMPEG_URL:-http://localhost:8001}"
SCORING_URL="${SCORING_URL:-http://localhost:8002}"
MEDIA_INGEST_URL="${MEDIA_INGEST_URL:-http://localhost:8003}"
WHISPER_URL="${WHISPER_URL:-http://192.168.1.188:5000}"
PYANNOTE_URL="${PYANNOTE_URL:-http://192.168.1.188:3003}"

RED='\033[0;31m'; GREEN='\033[0;32m'; RESET='\033[0m'
pass() { echo -e "${GREEN}✓ $1${RESET}"; }
fail() { echo -e "${RED}✗ $1${RESET}"; exit 1; }

echo "=== Smoke test: FFmpeg Overlay ($FFMPEG_URL) ==="

# Health check
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$FFMPEG_URL/health")
[[ "$STATUS" == "200" ]] && pass "GET /health → 200" || fail "GET /health returned $STATUS"

# Preview endpoint — /preview expects a JSON array of TimelineEntry, not the full timeline object
PREVIEW=$(curl -sf -X POST "$FFMPEG_URL/preview" \
  -H "Content-Type: application/json" \
  -d "$(jq -c '.chunks' examples/sample_timeline.json)")
echo "$PREVIEW" | jq -e '.filter_chain | type == "string"' > /dev/null \
  && pass "POST /preview → filter_chain string" \
  || fail "POST /preview returned unexpected body: $PREVIEW"

# render-multi endpoint — 3-position overlay (overall/left/right) on a real clip
CHUNKS_JSON=$(jq -c '.chunks' examples/sample_timeline.json)
OVERALL_JSON="$CHUNKS_JSON"
LEFT_JSON=$(echo "$CHUNKS_JSON" | jq -c '.[0:1]')
RIGHT_JSON=$(echo "$CHUNKS_JSON" | jq -c '.[1:2]')

HTTP_CODE=$(curl -sf -X POST "$FFMPEG_URL/render-multi" \
  -F "video=@examples/lil_brit_raw.mp4;type=video/mp4" \
  -F "overall_timeline=$OVERALL_JSON" \
  -F "speaker_left_timeline=$LEFT_JSON" \
  -F "speaker_right_timeline=$RIGHT_JSON" \
  --max-time 60 \
  -o /tmp/render_multi_response.mp4 \
  -w "%{http_code}" || true)

if [[ "$HTTP_CODE" == "200" ]] && [[ -s /tmp/render_multi_response.mp4 ]]; then
  pass "POST /render-multi → rendered MP4 ($(stat -c%s /tmp/render_multi_response.mp4) bytes)"
else
  fail "POST /render-multi returned HTTP $HTTP_CODE: $(cat /tmp/render_multi_response.mp4 2>/dev/null)"
fi


echo ""
echo "=== Smoke test: Sentiment Scoring ($SCORING_URL) ==="

# Health check
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$SCORING_URL/health")
[[ "$STATUS" == "200" ]] && pass "GET /health → 200" || fail "GET /health returned $STATUS"

# Score endpoint with sample transcript (returns 200 or 502 if Ollama is unreachable)
HTTP_CODE=$(curl -sf -X POST "$SCORING_URL/score" \
  -H "Content-Type: application/json" \
  --max-time 60 \
  -o /tmp/score_response.json \
  -w "%{http_code}" \
  -d @examples/sample_transcript.json || true)

if [[ "$HTTP_CODE" == "200" ]]; then
  cat /tmp/score_response.json | jq -e '.chunks | length > 0' > /dev/null \
    && pass "POST /score → scored chunks returned" \
    || fail "POST /score returned 200 but no chunks"
elif [[ "$HTTP_CODE" == "502" ]]; then
  pass "POST /score → 502 (LLM unreachable, service itself is healthy)"
else
  fail "POST /score returned unexpected HTTP $HTTP_CODE"
fi


echo ""
echo "=== Smoke test: Media Ingest ($MEDIA_INGEST_URL) ==="

# Health check
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$MEDIA_INGEST_URL/health")
[[ "$STATUS" == "200" ]] && pass "GET /health → 200" || fail "GET /health returned $STATUS"

# Ingest endpoint — uploads a real 2-speaker clip and calls out to live
# Whisper + Pyannote, so this can take a couple of minutes.
HTTP_CODE=$(curl -sf -X POST "$MEDIA_INGEST_URL/ingest" \
  -F "video=@examples/lil_brit_raw.mp4;type=video/mp4" \
  --max-time 180 \
  -o /tmp/ingest_response.json \
  -w "%{http_code}" || true)

if [[ "$HTTP_CODE" == "200" ]]; then
  CHUNK_COUNT=$(jq '.chunks | length' /tmp/ingest_response.json)
  SPEAKERS=$(jq -c '.speaker_order' /tmp/ingest_response.json)
  jq -e '.chunks | length > 0' /tmp/ingest_response.json > /dev/null \
    && pass "POST /ingest → $CHUNK_COUNT speaker-labeled chunks (speakers: $SPEAKERS)" \
    || fail "POST /ingest returned 200 but no chunks"
else
  fail "POST /ingest returned HTTP $HTTP_CODE — check Whisper ($WHISPER_URL) and Pyannote ($PYANNOTE_URL) are reachable: $(cat /tmp/ingest_response.json 2>/dev/null)"
fi


echo ""
echo "=== Smoke test: Dashboard (http://localhost:3000) ==="
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:3000/")
[[ "$STATUS" == "200" ]] && pass "GET / → 200 (nginx serving SPA)" || fail "GET / returned $STATUS"


echo ""
echo -e "${GREEN}All smoke tests passed.${RESET}"
