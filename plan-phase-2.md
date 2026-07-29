
## Plan: Add Anger, Frustration & Sarcasm Detection

 A second LLM call per chunk (separate from the existing tone/score call) returns the three new fields. Anger and frustration get two new emoji rows in the video overlay; sarcasm is dashboard-only. The emotion model is configurable via a new `EMOTION_MODEL` env var. Both calls should go to the local qwen2.5:32b-instruct model for now. Future releases will use different external models

**Emoji mapping:**
- Anger: 😐=0, 😠=1, 😡=2, 💥=3
- Frustration: 😐=0, 😤=1, 😣=2, 🤬=3
- Sarcasm: shown in ChunkInspector only (✓/✗)

---

### Phase 1 — Schema & Types
1. Extend sentiment_timeline.schema.json with `anger_level` (int 0-3), `frustration_level` (int 0-3), `sarcasm_flag` (bool)
2. Update sample_timeline.json with example values
3. Update sentiment.ts `ScoredChunk` with new fields

### Phase 2 — Scoring Service
4. Add `_EMOTION_SYSTEM_PROMPT` + `_EmotionResponse` Pydantic model to scorer.py
5. Add `score_emotions(text, client)` function — mirrors `score_chunk()` pattern
6. Parameterize llm_client.py to support `EMOTION_MODEL` env var override
7. Update `score_transcript()` to call both per chunk and merge results
8. Add `EMOTION_MODEL` env var to docker-compose.yml

### Phase 3 — FFmpeg Overlay
9. Add 8 new emoji PNGs to emoji
10. Update `TimelineEntry` in ffmpeg-overlay/main.py with `anger_level` + `frustration_level`
11. Add `ANGER_EMOJI_MAP` + `FRUSTRATION_EMOJI_MAP` dicts in filter_generator.py
12. Update `build_filter_graph()` to add two more overlay rows below the existing emoji *(depends on step 11)*

### Phase 4 — Dashboard
13. Update ChunkInspector.tsx — new rows for anger, frustration, sarcasm
14. Add emotion trend visualization add a new `EmotionChart.tsx` component

### Phase 5 — Tests
15. test_scorer.py: emotion prompt, `_EmotionResponse` parsing, `score_emotions()`, merged output *(parallel with 16)*
16. test_api.py: update mock responses to include emotion fields *(parallel with 15)*
17. test_filter_generator.py: anger/frustration emoji selection, two-row positions
18. ChunkInspector.test.tsx: new field rendering

---

**Verification**
1. `make test` in sentiment-scoring — all scorer/API tests pass with emotion fields
2. `make test` in ffmpeg-overlay — filter tests cover two new rows
3. `npm test` in dashboard — ChunkInspector tests pass
4. Manual: POST sample transcript to `/score`, confirm `anger_level`, `frustration_level`, `sarcasm_flag` in response
5. Manual: POST to `/preview`, confirm filter_complex shows three emoji overlay rows per chunk
6. Visual: render a short clip, confirm three rows visible

---

