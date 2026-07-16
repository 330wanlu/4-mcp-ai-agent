"""Chat / Embedding Provider 协议。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class ChatMessage:
    role: str
    content: str


class ChatProvider(ABC):
    """聊天模型抽象；阶段 2 才会真正调用方舟。"""

    @abstractmethod
    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    """向量模型抽象；阶段 1 ingest 时使用。"""

    @abstractmethod
    async def embed(self, texts: Sequence[str], **kwargs: Any) -> list[list[float]]:
        raise NotImplementedError
