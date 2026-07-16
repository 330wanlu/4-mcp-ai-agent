"""火山引擎豆包 Provider：阶段 1 实现 embed；chat 阶段 2。"""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

import httpx

from ka_common.config import Settings, get_settings
from ka_common.db.models import EMBEDDING_DIM
from ka_llm.base import ChatMessage, ChatProvider, EmbeddingProvider


class VolcengineDoubaoProvider(ChatProvider, EmbeddingProvider):
    """Chat + Embedding；Embedding 走方舟 multimodal 接口。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        timeout: float = 60.0,
        concurrency: int = 4,
    ) -> None:
        self.settings = settings or get_settings()
        self.timeout = timeout
        self.concurrency = concurrency

    def _headers(self) -> dict[str, str]:
        key = self.settings.ark_api_key
        if not key:
            raise RuntimeError("ARK_API_KEY 未配置，无法调用方舟 Embedding")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _multimodal_url(self) -> str:
        base = self.settings.ark_base_url.rstrip("/")
        return f"{base}/embeddings/multimodal"

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError(
            "VolcengineDoubaoProvider.chat 将在阶段 2 对接方舟："
            f"model={self.settings.llm_model}"
        )

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
