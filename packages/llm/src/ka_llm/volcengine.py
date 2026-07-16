"""火山引擎豆包 Provider（阶段 0 仅落骨架，真实调用在阶段 1/2）。"""

from __future__ import annotations

from typing import Any, Sequence

from ka_common.config import Settings, get_settings
from ka_llm.base import ChatMessage, ChatProvider, EmbeddingProvider


class VolcengineDoubaoProvider(ChatProvider, EmbeddingProvider):
    """同时实现 Chat 与 Embedding；配置来自 Settings。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

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

    async def embed(self, texts: Sequence[str], **kwargs: Any) -> list[list[float]]:
        raise NotImplementedError(
            "VolcengineDoubaoProvider.embed 将在阶段 1 对接方舟："
            f"model={self.settings.embedding_model}"
        )
