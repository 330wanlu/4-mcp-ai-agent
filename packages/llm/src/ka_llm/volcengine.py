"""火山引擎豆包 Provider：chat + embed。"""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

import httpx

from ka_common.config import Settings, get_settings
from ka_common.db.models import EMBEDDING_DIM
from ka_llm.base import ChatMessage, ChatProvider, EmbeddingProvider


class VolcengineDoubaoProvider(ChatProvider, EmbeddingProvider):
    """Chat（/chat/completions）+ Embedding（/embeddings/multimodal）。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        timeout: float = 120.0,
        concurrency: int = 4,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.concurrency = concurrency

    def _headers(self) -> dict[str, str]:
        key = self.settings.ark_api_key
        if not key:
            raise RuntimeError("ARK_API_KEY 未配置，无法调用方舟 API")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _chat_url(self) -> str:
        return f"{self.settings.ark_base_url.rstrip('/')}/chat/completions"

    def _multimodal_url(self) -> str:
        return f"{self.settings.ark_base_url.rstrip('/')}/embeddings/multimodal"

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """方舟 OpenAI 兼容 Chat Completions。"""
        max_tokens = int(kwargs.get("max_tokens", 2048))
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # 部分推理模型支持关闭思考以降低延迟；忽略不支持时的错误由下方 HTTP 处理
        if kwargs.get("thinking") is False:
            payload["thinking"] = {"type": "disabled"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._chat_url(), headers=self._headers(), json=payload
            )
            if resp.status_code >= 400 and "thinking" in payload:
                # 模型不支持 thinking 字段时回退
                payload.pop("thinking", None)
                resp = await client.post(
                    self._chat_url(), headers=self._headers(), json=payload
                )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Chat 失败 HTTP {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Chat 响应无 choices: {str(data)[:300]}")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            # 少数情况下内容可能在 reasoning 后为空
            raise RuntimeError(f"Chat 响应 content 为空: {str(data)[:300]}")
        return content.strip()

    async def _embed_one(self, client: httpx.AsyncClient, text: str) -> list[float]:
        dims = self.settings.embedding_dimensions or EMBEDDING_DIM
        payload = {
            "model": self.settings.embedding_model,
            "input": [{"type": "text", "text": text}],
            "dimensions": dims,
            "encoding_format": "float",
        }
        resp = await client.post(self._multimodal_url(), headers=self._headers(), json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Embedding 失败 HTTP {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        # multimodal 单条：{"data": {"embedding": [...]}}
        block = data.get("data")
        if isinstance(block, dict) and "embedding" in block:
            vec = block["embedding"]
        elif isinstance(block, list) and block:
            first = block[0]
            vec = first.get("embedding") if isinstance(first, dict) else None
        else:
            vec = None
        if not isinstance(vec, list):
            raise RuntimeError(f"Embedding 响应格式异常: {str(data)[:300]}")
        if len(vec) != dims:
            raise RuntimeError(f"Embedding 维度不符: got={len(vec)} expected={dims}")
        return [float(x) for x in vec]

    async def embed(self, texts: Sequence[str], **kwargs: Any) -> list[list[float]]:
        if not texts:
            return []
        sem = asyncio.Semaphore(self.concurrency)

        async with httpx.AsyncClient(timeout=self.timeout) as client:

            async def _run(t: str) -> list[float]:
                async with sem:
                    return await self._embed_one(client, t)

            return list(await asyncio.gather(*[_run(t) for t in texts]))
