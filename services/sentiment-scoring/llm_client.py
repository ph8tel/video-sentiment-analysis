"""
LLM provider abstraction.

The active provider is selected at runtime via the LLM_PROVIDER environment
variable. Adding a new provider means implementing LLMClient and registering
it in get_llm_client() — no changes to scoring logic required.

Supported providers
───────────────────
  ollama  — local / LAN Ollama instance (default)
  groq    — Groq cloud API (post-MVP)
"""

import abc
import os

import httpx


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def complete(self, prompt: str) -> str:
        """Send a prompt and return the raw response string (JSON expected)."""


class OllamaClient(LLMClient):
    def __init__(self) -> None:
        self.host  = os.getenv("OLLAMA_HOST",  "http://host.docker.internal:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model":  self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            return resp.json()["response"]


class GroqClient(LLMClient):
    """
    Groq cloud LLM client (OpenAI-compatible API).

    Requires:
      GROQ_API_KEY  — your Groq API key
      GROQ_MODEL    — Groq model name (default: llama-3.1-8b-instant)
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Set it or switch LLM_PROVIDER back to 'ollama'."
            )

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model":           self.model,
                    "messages":        [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


def get_llm_client() -> LLMClient:
    """Factory: return the correct LLMClient based on LLM_PROVIDER env var."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        return OllamaClient()
    if provider == "groq":
        return GroqClient()
    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r}. Expected 'ollama' or 'groq'."
    )
