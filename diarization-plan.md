## Plan: Two-Speaker Video Sentiment Pipeline

This is a real feature spanning 4 codebases (this repo + your two host-based STT/diarization services). Good news: the sentiment-scoring `/score` endpoint is already speaker-agnostic (just takes `{start,end,text}[]`), so per-speaker scoring needs **zero backend changes** — it's just 3 calls. The main new surface area is a merge step and a 3-position overlay renderer.

**Steps** (phases, each independently verifiable; do in order per your priority)

1. **`media-ingest` service (new)** — the hard part, build/verify first in isolation.
   - New FastAPI service in `services/media-ingest/`: extracts 16kHz mono WAV via ffmpeg, calls Whisper (`/stt`) and Pyannote (`/diarize`) in parallel over LAN (192.168.1.188), merges Whisper segments with diarization turns by max time-overlap (nearest-turn fallback for gaps), and tracks `speaker_order` by first-appearance.
   - Returns `{chunks: [{start,end,text,speaker}], speaker_order: [...], meta: {...}}`.
   - Add to docker-compose.yml (port 8003) and .env.example with `WHISPER_URL`/`PYANNOTE_URL`.
   - Verify with unit tests (merge logic on fixtures) + API tests (mocked httpx) before ever touching a live GPU service.

2. **Pyannote change** *(depends on 1 informing the contract)* — modify `/diarize` in main.py to accept optional `num_speakers` form field so we can force exactly 2 speakers.

3. **ffmpeg-overlay 3-position overlay** *(parallel with 1-2, independent)* — new `build_multi_speaker_filter_graph()` in filter_generator.py placing sentiment-only emoji at bottom-middle (overall), top-left (speaker 1), top-right (speaker 2). New `POST /render-multi` endpoint in main.py; existing `/render`/`/preview` untouched.

4. **Dashboard integration** *(depends on 1, 3)* — new `VideoUpload.tsx`: drop one video → `media-ingest` → split chunks by `speaker_order` → 3× `/score` calls → `/render-multi` → 3 timelines + video. App.tsx gets 3-timeline state; ChunkTimeline.tsx gets an optional `title` prop for the 3 labeled charts.

5. **Docs/smoke test** — update README, smoke_test.sh, .env.example.

**Relevant files**
- `services/media-ingest/**` (new) — main.py, merge.py, Dockerfile, tests
- main.py — add `num_speakers` param
- filter_generator.py, main.py — 3-position overlay + `/render-multi`
- `services/dashboard/src/components/VideoUpload.tsx` (new), App.tsx, ChunkTimeline.tsx
- docker-compose.yml, .env.example, README.md, smoke_test.sh

**Verification**
1. media-ingest: pytest unit tests on merge fixtures + mocked API test; manual curl against live Whisper/Pyannote with a real clip.
2. pyaudio: manual curl with `num_speakers=2`.
3. ffmpeg-overlay: `make test-unit` (position math) + `make test` (real render, inspect frames).
4. dashboard: `npx vitest run` + manual drag-drop.
5. Full e2e: `docker compose up --build`, drop a real 2-speaker video, confirm overlay positions + 3 timelines.

**Decisions**
- Whisper/Pyannote stay host-based (no GPU containerization); reached via LAN like `OLLAMA_HOST`.
- Orchestration lives in new `media-ingest` backend service, not the browser.
- Exactly 2 speakers enforced via `num_speakers=2`.
- Anger/frustration rows excluded from the new 3-position overlays (sentiment emoji only), to avoid clutter.
- Existing single-timeline `PipelineUpload` flow stays as-is; new flow is additive.

**Further Considerations**
1. Whisper segment↔speaker assignment can be wrong at boundaries (max-overlap heuristic) — acceptable for MVP, but flagging as a known limitation rather than doing word-level re-alignment.
2. Left/right position assignment = whoever speaks first. If you'd rather assign by total talk-time or let the user pick, let me know before implementation.
