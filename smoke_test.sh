#!/usr/bin/env bash
# smoke_test.sh — end-to-end smoke test against running services.
#
# Usage:
#   ./smoke_test.sh                        # assumes services up on localhost
#   FFMPEG_URL=http://localhost:8001 \
#   SCORING_URL=http://localhost:8002 \
#   ./smoke_test.sh
#
# Requires: curl, jq
set -euo pipefail

FFMPEG_URL="${FFMPEG_URL:-http://localhost:8001}"
SCORING_URL="${SCORING_URL:-http://localhost:8002}"

RED='\033[0;31m'; GREEN='\033[0;32m'; RESET='\033[0m'
pass() { echo -e "${GREEN}✓ $1${RESET}"; }
fail() { echo -e "${RED}✗ $1${RESET}"; exit 1; }

echo "=== Smoke test: FFmpeg Overlay ($FFMPEG_URL) ==="

# Health check
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "$FFMPEG_URL/health")
[[ "$STATUS" == "200" ]] && pass "GET /health → 200" || fail "GET /health returned $STATUS"

# Preview endpoint with sample timeline
PREVIEW=$(curl -sf -X POST "$FFMPEG_URL/preview" \
  -H "Content-Type: application/json" \
  -d @examples/sample_timeline.json)
echo "$PREVIEW" | jq -e '.filter_chain | type == "string"' > /dev/null \
  && pass "POST /preview → filter_chain string" \
  || fail "POST /preview returned unexpected body: $PREVIEW"


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
echo "=== Smoke test: Dashboard (http://localhost:3000) ==="
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:3000/")
[[ "$STATUS" == "200" ]] && pass "GET / → 200 (nginx serving SPA)" || fail "GET / returned $STATUS"


echo ""
echo -e "${GREEN}All smoke tests passed.${RESET}"
