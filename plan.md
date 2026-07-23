
# Video Sentiment Analysis — Build Plan

## Architecture
Three independent Docker Compose microservices sharing a `sentiment_timeline.json` contract:

| Service | Port | Input | Output |
|---|---|---|---|
| **A. FFmpeg Overlay** | 8001 | `video.mp4` + `sentiment_timeline.json` | `video_with_overlay.mp4` |
| **B. Sentiment Scoring** | 8002 | `transcript.json` | `sentiment_timeline.json` |
| **C. Dashboard UI** | 3000 | `sentiment_timeline.json` | Interactive visualization |

Build order: A → B → C (most deterministic first, UI last).

---

## Stack
- **Services A & B:** Python 3.11 + FastAPI + Uvicorn
- **Service C:** React 18 + TypeScript + Vite + Recharts → served by nginx
- **LLM:** Ollama at `192.168.1.108:11434`, model `llama3.1:8b` (default)
- **Deployment:** Docker Compose

---

## Directory Structure
```
video-sentiment-analysis/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── shared/
│   └── schemas/
│       ├── transcript.schema.json
│       └── sentiment_timeline.schema.json
├── services/
│   ├── ffmpeg-overlay/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py               # FastAPI: /health, /preview, /render
│   │   └── filter_generator.py   # drawbox filter chain builder
│   ├── sentiment-scoring/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py               # FastAPI: /health, /score
│   │   ├── llm_client.py         # provider abstraction (Ollama / Groq)
│   │   ├── scorer.py             # prompt template + chunk scoring
│   │   └── color_mapper.py       # tone enum → hex + score
│   └── dashboard/
│       ├── Dockerfile
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── types/sentiment.ts
│           └── components/
│               ├── FileUpload.tsx
│               ├── ChunkTimeline.tsx
│               ├── SentimentChart.tsx
│               └── ChunkInspector.tsx
└── examples/
    ├── sample_transcript.json
    └── sample_timeline.json
```

---

## Env Variables
| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | Set to `groq` post-MVP |
| `OLLAMA_HOST` | `http://192.168.1.108:11434` | LAN address of Ollama machine |
| `OLLAMA_MODEL` | `llama3.1:8b` | Fits in 20GB VRAM; matches Groq model family |
| `GROQ_API_KEY` | *(empty)* | Populated post-MVP |
| `MAX_UPLOAD_SIZE_MB` | `500` | Applies to video upload in ffmpeg-overlay |

---

## Color Map
| Tone | Score | Hex |
|---|---|---|
| VERY_NEGATIVE | 0 | #FF0000 |
| NEGATIVE | 2 | #FF4500 |
| SLIGHTLY_NEGATIVE | 3 | #FFA500 |
| NEUTRAL | 5 | #CCCCCC |
| SLIGHTLY_POSITIVE | 6 | #90EE90 |
| POSITIVE | 8 | #32CD32 |
| VERY_POSITIVE | 10 | #008000 |

---

## Build Phases

### ✅ Phase 1 — Foundation
- [x] Monorepo structure
- [x] JSON schemas (`transcript.schema.json`, `sentiment_timeline.schema.json`)
- [x] Sample data (`examples/`)
- [x] `docker-compose.yml` skeleton
- [x] `.env.example`
- [x] `.gitignore`

### ✅ Phase 2 — FFmpeg Overlay Service (port 8001)
- [x] FastAPI app + Pydantic models (`TimelineEntry`)
- [x] `filter_generator.py`: builds `drawbox` filter string (FFmpeg uses `0x` prefix, not `#`)
- [x] `POST /preview` → returns filter chain JSON (no FFmpeg or video needed)
- [x] `POST /render` → multipart upload → MP4 response via `asyncio.create_subprocess_exec`
- [x] `Dockerfile`: `python:3.11-slim` + `apt-get install ffmpeg`
- [x] Unit tests (`test_filter_generator.py`) — no FFmpeg required
- [x] API tests (`test_preview.py`) — no FFmpeg required
- [x] Render integration tests (`test_render.py`) — auto-skip if FFmpeg unavailable
- [x] Tiny video fixture generated at test time (not committed to git)

### ✅ Phase 3 — Sentiment Scoring Service (port 8002)
- [x] `color_mapper.py`: tone enum → hex + score + `score_to_tone()` mapper
- [x] `llm_client.py`: `OllamaClient` + `GroqClient` behind `LLMClient` ABC; `get_llm_client()` factory driven by `LLM_PROVIDER` env var
- [x] `scorer.py`: Pydantic models, prompt template, `parse_llm_response()`, duration-weighted `score_transcript()`
- [x] `POST /score` → `[{start, end, text}]` → full `sentiment_timeline.json`; 502 on LLM errors
- [x] `Dockerfile`: `python:3.11-slim`
- [x] Unit tests: `test_color_mapper.py`, `test_llm_client.py` (respx mocks), `test_scorer.py` (MockLLMClient)
- [x] API tests: `test_api.py` with FastAPI dependency override — zero real LLM calls

### 🔲 Phase 4 — Dashboard UI (port 3000) *(intentionally minimal — will be replaced)*
- [ ] Vite + React + TypeScript scaffold
- [ ] `FileUpload`: drag-and-drop `sentiment_timeline.json` (pure client-side)
- [ ] `ChunkTimeline`: Recharts `BarChart` — x=time, y=score, fill=tone hex
- [ ] `SentimentChart`: Recharts `LineChart` — rolling average trend
- [ ] `ChunkInspector`: click bar → side panel with text, tone, score, time range
- [ ] `Dockerfile`: node build → `nginx:alpine`

### 🔲 Phase 5 — Integration
- [ ] Complete `docker-compose.yml`
- [ ] End-to-end smoke test with sample data
- [ ] README with prerequisites (`ollama pull llama3.1:8b` on Ollama machine)

---

## API Contracts

### FFmpeg Overlay (8001)
```
GET  /health
POST /preview   body: { timeline: TimelineEntry[] }   → { filter_chain: string }
POST /render    multipart: video (file) + timeline (JSON string) → video/mp4
```

### Sentiment Scoring (8002)
```
GET  /health
POST /score     body: { chunks: [{ start, end, text }] }   → SentimentTimeline
```

---

## Out of Scope (MVP)
- Transcription / ASR (transcripts are pre-existing)
- Correction sentiment
- Auth / user accounts
- Persistent storage / database
- Real-time scoring

---

# **MVP Architecture Overview**
You’re building a pipeline with **three independent microservices**, each testable in isolation:

### **A. FFmpeg Overlay Service**  
**Input:**  
- `video.mp4`  
- `sentiment_timeline.json` (start, end, score, color)

**Output:**  
- `video_with_overlay.mp4`

### **B. Sentiment Scoring Service**  
**Input:**  
- `transcript.json` (chunked text + timestamps)

**Output:**  
- `sentiment_timeline.json` (chunk-level scores)

### **C. Color Mapping + Dashboard UI Service**  
**Input:**  
- `sentiment_timeline.json`  
- (optional) `correction_scores.json`  
- (optional) `overall_scores.json`

**Output:**  
- Interactive dashboard visualizing score evolution  
- No video processing  
- No FFmpeg  
- Pure telemetry visualization

---

# 🟥 **A. FFmpeg Overlay Service (Video + Scores → Video w/ Overlay)**

This is the first service you’ll build because it’s the most deterministic and easiest to test.

### **Responsibilities**
- Accept a video file  
- Accept a sentiment timeline (JSON)  
- Generate FFmpeg filter chains  
- Render a new video with colored overlays synced to timestamps  

### **Sentiment Timeline Format**
```json
[
  {
    "start": 12.4,
    "end": 15.8,
    "score": 2,
    "color": "#FF4500"
  }
]
```

### **FFmpeg Filter Generation**
For each entry:
```
drawbox=x=0:y=0:w=200:h=200:color=#FF4500@0.7:enable='between(t,12.4,15.8)'
```

Concatenate filters with commas.

### **Service API**
```
POST /render
{
  "video": <binary>,
  "timeline": <json>
}
```

### **Output**
- Rendered MP4  
- Optional: return the filter chain for debugging

### **Why this comes first**
- It’s deterministic  
- Easy to test with fake timelines  
- Lets you validate your overlay design before sentiment scoring exists  

---

# 🟦 **B. Sentiment Scoring Service (Chunk Text → Sentiment Score)**

This is your Llama 70B pipeline.

### **Responsibilities**
- Accept chunked transcript with timestamps  
- Send each chunk to Llama 70B  
- Produce:
  - chunk sentiment  
  - overall sentiment  
  - correction sentiment (if you want a second pass)  
- Output a unified timeline JSON

### **Input Format**
```json
[
  {
    "start": 0.0,
    "end": 2.5,
    "text": "Hello everyone..."
  }
]
```

### **Output Format**
```json
{
  "chunks": [
    {
      "start": 0.0,
      "end": 2.5,
      "tone": "SLIGHTLY_POSITIVE",
      "score": 6
    }
  ],
  "overall": {
    "score": 7.2
  },
  "correction": {
    "score": 6.8
  }
}
```

### **Pipeline**
1. Chunk transcript  
2. Score each chunk  
3. Compute overall sentiment (EMA or weighted average)  
4. Compute correction sentiment (optional second pass)  
5. Emit JSON for both video overlay and dashboard

### **Why this comes second**
- You can test it independently  
- You can feed fake transcripts to validate scoring  
- You can compare different chunking strategies without touching video

---

# 🟩 **C. Color Mapping + Dashboard UI Service (Scores → Visual Timeline)**

This is where you visually test how sentiment evolves — without video.

### **Responsibilities**
- Accept sentiment timeline JSON  
- Map scores → colors  
- Render:
  - Chunk sentiment graph  
  - Overall sentiment trend  
  - Correction sentiment trend  
  - Timeline scrubber  
  - Optional: overlay preview (no video)

### **Dashboard Views**
#### **1. Chunk Sentiment Timeline**
- Horizontal bar chart  
- Each bar = chunk  
- Color = mapped sentiment  
- Height = score  
- X-axis = time

#### **2. Overall Sentiment Evolution**
- Line chart  
- EMA curve  
- Shows drift over time

#### **3. Correction Sentiment**
- Second line chart  
- Compare against original scoring

#### **4. Chunk Inspector**
Click a chunk → show:
- Text  
- Score  
- Color  
- Time range  
- Model output  

### **Color Mapping**
Your 7-level enum → hex colors:

| Tone | Score | Color |
|------|--------|--------|
| VERY_NEGATIVE | 0 | #FF0000 |
| NEGATIVE | 2 | #FF4500 |
| SLIGHTLY_NEGATIVE | 3 | #FFA500 |
| NEUTRAL | 5 | #CCCCCC |
| SLIGHTLY_POSITIVE | 6 | #90EE90 |
| POSITIVE | 8 | #32CD32 |
| VERY_POSITIVE | 10 | #008000 |

### **Why this comes last**
- It depends on sentiment scoring  
- It consumes the same JSON as the FFmpeg service  
- It’s purely visual — no heavy processing  
- It becomes your main testing tool

---

# ⭐ **Final MVP Flow (End-to-End)**

### **Step 1 — Upload**
User uploads:
- `video.mp4`
- `transcript.json`

### **Step 2 — Sentiment Scoring Service**
Produces:
- `sentiment_timeline.json`

### **Step 3 — FFmpeg Overlay Service**
Consumes:
- `video.mp4`
- `sentiment_timeline.json`

Outputs:
- `video_with_overlay.mp4`

### **Step 4 — Dashboard UI Service**
Consumes:
- `sentiment_timeline.json`

Outputs:
- Interactive visualization of:
  - Chunk sentiment  
  - Overall sentiment  
  - Correction sentiment  
  - Color mapping  
  - Timeline inspector  

---

# 🎯 **This architecture gives you:**
- Perfect sync between audio → text → sentiment → color → video  
- A reusable sentiment timeline artifact  
- A dashboard that tests your scoring logic without touching video  
- A clean separation of concerns  
- A pipeline you can scale or swap components in  
- A foundation for future features (real-time scoring, multi-model comparison, etc.)

---

If you want, I can now produce:

- The full directory structure  
- The API contracts for each service  
- The JSON schemas  
- The FFmpeg filter generator  
- The chunking algorithm  
- The Llama prompt template  
- The dashboard layout  
