# Sentiment Scoring Service

Accepts a chunked transcript, scores each chunk's emotional tone with a local LLM (Ollama), and returns a `sentiment_timeline.json`-shaped object ready for the FFmpeg overlay service and the dashboard.

Port: **8002**

---

## API

### `GET /health`
Returns `{"status": "ok"}`.

---

### `POST /score`
Score a list of transcript chunks and return a full sentiment timeline.

**Request** — `application/json` — same array format as `transcript.json`:
```json
[
  {"start": 0.0,  "end": 3.2,  "text": "Hello everyone, welcome back."},
  {"start": 3.2,  "end": 7.5,  "text": "Today we have some exciting news."},
  {"start": 7.5,  "end": 12.1, "text": "Unfortunately there were some setbacks."}
]
```

You can POST a transcript file directly:
```bash
curl -X POST http://localhost:8002/score \
  -H "Content-Type: application/json" \
  -d @transcript.json \
  -o sentiment_timeline.json
```

**Response**
```json
{
  "chunks": [
    {
      "start": 0.0,
      "end": 3.2,
      "tone": "SLIGHTLY_POSITIVE",
      "score": 6,
      "color": "#90EE90",
      "text": "Hello everyone, welcome back."
    }
  ],
  "overall": {
    "score": 6.1,
    "tone": "SLIGHTLY_POSITIVE"
  }
}
```

**Error responses**

| Status | Cause |
|---|---|
| 422 | Missing fields, empty array, or invalid input |
| 502 | LLM returned unparseable output or network error reaching Ollama/Groq |

---

## Tone map

| Tone | Score | Color |
|---|---|---|
| VERY_NEGATIVE | 0 | `#FF0000` |
| NEGATIVE | 2 | `#FF4500` |
| SLIGHTLY_NEGATIVE | 3 | `#FFA500` |
| NEUTRAL | 5 | `#CCCCCC` |
| SLIGHTLY_POSITIVE | 6 | `#90EE90` |
| POSITIVE | 8 | `#32CD32` |
| VERY_POSITIVE | 10 | `#008000` |

The overall score is a **duration-weighted average** across all chunks. Longer chunks contribute proportionally more to the final score.

---

## LLM providers

The active provider is selected by the `LLM_PROVIDER` environment variable. No code changes are required to switch.

### Ollama (default)
```env
LLM_PROVIDER=ollama
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
```
The model must be pulled on the Ollama machine first:
```bash
ollama pull llama3.1:8b
```
When the scoring service runs in Docker on Linux and Ollama runs on the same host, use `http://host.docker.internal:11434`, not `http://0.0.0.0:11434` or `http://localhost:11434`.

### Groq (post-MVP)
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

---

## Tie-breaking / correction hook

When a numeric score falls exactly midway between two tone levels (e.g. 9.0 is equidistant between POSITIVE=8 and VERY_POSITIVE=10), `resolve_tie()` in `color_mapper.py` is called. Currently it returns the lower-scoring tone. This is the designated hook for future correction logic:

- Re-scoring with a larger model
- Averaging multiple model samples
- Applying contextual window bias

Replacing the stub is a one-function change that the existing `TestResolveTie` tests will verify.

---

## Development setup

Uses the shared `video-overlay` conda environment (Python 3.11).

```bash
# One-time: create the conda env from the repo root
conda create -n video-overlay python=3.11 -y
conda activate video-overlay

cd services/sentiment-scoring
pip install -r requirements-dev.txt
```

### Run locally
```bash
uvicorn main:app --reload --port 8002
```

---

## Tests

```bash
conda activate video-overlay
cd services/sentiment-scoring

# Unit tests — no LLM, no network
make test-unit

# API tests — LLM dependency injected with MockLLMClient
make test-api

# All tests
make test
```

### Test structure

| File | What it tests | Calls LLM? |
|---|---|---|
| `tests/test_color_mapper.py` | Tone map, `score_to_tone`, `resolve_tie` | No |
| `tests/test_llm_client.py` | `OllamaClient`, `GroqClient`, `get_llm_client` factory | No (respx mocks httpx) |
| `tests/test_scorer.py` | Prompt building, response parsing, scoring pipeline | No (MockLLMClient) |
| `tests/test_api.py` | `/health`, `/score` endpoints, error handling | No (FastAPI dependency override) |

The `MockLLMClient` in `tests/conftest.py` implements `LLMClient` with pre-canned responses. The FastAPI `get_client` dependency is overridden in `test_api.py` so the real Ollama/Groq clients are never instantiated during testing.

---

## Architecture

```
main.py
  └── Depends(get_client) → LLMClient
        ├── OllamaClient   (LLM_PROVIDER=ollama)
        └── GroqClient     (LLM_PROVIDER=groq)

scorer.py
  ├── build_prompt(text) → str
  ├── parse_llm_response(raw) → _LLMResponse
  ├── score_chunk(chunk, client) → ScoredChunk
  └── score_transcript(chunks, client) → SentimentResult

color_mapper.py
  ├── score_to_tone(score) → Tone
  │     └── resolve_tie(candidates, score)  ← correction hook
  └── tone_to_color(tone) → hex
```

---

## Docker

```bash
# Build
docker build -t sentiment-scoring .

# Run standalone (Ollama must be reachable at OLLAMA_HOST)
docker run -p 8002:8002 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -e OLLAMA_MODEL=llama3.1:8b \
  sentiment-scoring

# Via Docker Compose from the repo root
docker compose up sentiment-scoring
```
