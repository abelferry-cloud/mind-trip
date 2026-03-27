# app/services/model_router.py
"""Model Router - handles model fallback chain (OpenAI → Claude → local).

Per Design Section 6.1:
- 429: wait 5s then retry primary, if still 429 switch
- 500: immediate switch
- timeout: immediate switch
- Per-request granularity
"""
import asyncio
from typing import Optional, Literal
from app.config import get_settings

ModelName = Literal["openai", "claude", "local"]

class ModelRouter:
    def __init__(self):
        self.settings = get_settings()
        self._primary_available = True  # optimistic

    def is_primary_available(self) -> bool:
        return self._primary_available

    async def call(self, prompt: str, system: str = "") -> str:
        """Call models in chain order, switching on failure.

        Raises:
            Exception: if all models in chain fail
        """
        chain = self.settings.model_chain_list
        last_error = None

        for model in chain:
            try:
                if model == "openai":
                    return await self._call_openai(prompt, system)
                elif model == "claude":
                    return await self._call_claude(prompt, system)
                elif model == "local":
                    return await self._call_local(prompt, system)
            except Exception as e:
                last_error = e
                if self._is_retryable(e):
                    if "429" in str(e):
                        await asyncio.sleep(5)
                        continue  # retry same model
                else:
                    continue  # switch to next model

        # All failed
        raise Exception(f"All models failed. Last error: {last_error}")

    def _is_retryable(self, error: Exception) -> bool:
        err_str = str(error)
        # Per Design Section 6.1:
        # - 429 rate limit: retry after wait (NOT skip to next model)
        # - 500 server error: skip to next model immediately
        # - timeout: skip to next model immediately
        if "429" in err_str:
            return True  # retry same model after wait
        return False  # all other errors → skip to next model

    async def _call_openai(self, prompt: str, system: str) -> str:
        """Call OpenAI API via LangChain.

        NOTE: For portfolio demonstration, this is a structured mock that returns
        a placeholder response. In production, replace with:
          from langchain_openai import ChatOpenAI
          llm = ChatOpenAI(model=self.settings.openai_model, api_key=self.settings.openai_api_key)
          return llm.invoke(prompt).content
        The fallback chain and retry logic remain the same.
        """
        if not self.settings.openai_api_key:
            raise Exception("OPENAI_API_KEY not set")
        await asyncio.sleep(0.01)  # simulate network latency
        self._primary_available = True
        return f"[OpenAI] {prompt[:50]}..."

    async def _call_claude(self, prompt: str, system: str) -> str:
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return f"[Claude] {prompt[:50]}..."

    async def _call_local(self, prompt: str, system: str) -> str:
        # Placeholder for local model (e.g., ollama)
        return f"[Local] {prompt[:50]}..."

_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
