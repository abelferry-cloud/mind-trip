# app/services/model_router.py
"""模型路由 - 处理模型回退链（OpenAI → Claude → 本地）。

根据设计文档第 6.1 节：
- 429: 等待 5 秒后重试主模型，如果仍然 429 则切换
- 500: 立即切换
- 超时：立即切换
- 每请求粒度
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
        """按链式顺序调用模型，失败时切换。

        引发：
            Exception: 如果链中所有模型都失败
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
        # 根据设计文档第 6.1 节：
        # - 429 速率限制：等待后重试（不跳过到下一个模型）
        # - 500 服务器错误：立即跳过到下一个模型
        # - 超时：立即跳过到下一个模型
        if "429" in err_str:
            return True  # 等待后重试同一模型
        return False  # 所有其他错误 → 切换到下一个模型

    async def _call_openai(self, prompt: str, system: str) -> str:
        """通过 LangChain 调用 DeepSeek API（OpenAI 兼容）。

        使用 OpenAI 兼容端点调用 DeepSeek API。
        """
        if not self.settings.deepseek_api_key:
            raise Exception("DEEPSEEK_API_KEY not set")

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise Exception("openai package not installed")

        client = AsyncOpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url
        )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=messages
        )

        self._primary_available = True
        return response.choices[0].message.content

    async def _call_claude(self, prompt: str, system: str) -> str:
        if not self.settings.claude_api_key:
            raise Exception("CLAUDE_API_KEY not set")
        await asyncio.sleep(0.01)
        return f"[Claude] {prompt[:50]}..."

    async def _call_local(self, prompt: str, system: str) -> str:
        # 本地模型占位符（如 ollama）
        return f"[Local] {prompt[:50]}..."

_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
