import os
import sys
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from llm_client import LLMClient, get_llm_client
from scorer import SentimentResult, TranscriptChunk, score_transcript

app = FastAPI(title="Sentiment Scoring Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Dependency — override in tests via app.dependency_overrides[get_client]
# ---------------------------------------------------------------------------

def get_client() -> LLMClient:
    return get_llm_client()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/score", response_model=SentimentResult)
async def score(
    chunks: List[TranscriptChunk],
    client: LLMClient = Depends(get_client),
):
    """
    Score a list of transcript chunks with the configured LLM.

    Accepts the same array format as ``transcript.json`` — you can POST
    the file directly with ``curl -d @transcript.json``.

    Returns a ``sentiment_timeline.json``-shaped object.
    """
    if not chunks:
        raise HTTPException(status_code=422, detail="chunks must not be empty")

    try:
        return await score_transcript(chunks, client)
    except ValueError as exc:
        # LLM returned unparseable output
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        # Network / timeout errors reaching the LLM
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {exc!s}",
        ) from exc
