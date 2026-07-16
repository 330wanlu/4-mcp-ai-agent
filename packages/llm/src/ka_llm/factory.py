"""按配置创建 LLM Provider（换模型名主要改 .env）。"""

from __future__ import annotations

from ka_common.config import Settings, get_settings
from ka_llm.base import ChatProvider, EmbeddingProvider
from ka_llm.volcengine import VolcengineDoubaoProvider


def get_llm_provider(settings: Settings | None = None) -> VolcengineDoubaoProvider:
    """当前唯一实现：火山豆包；日后可按 settings 切换。"""
    return VolcengineDoubaoProvider(settings or get_settings())


def get_chat_provider(settings: Settings | None = None) -> ChatProvider:
    return get_llm_provider(settings)


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    return get_llm_provider(settings)
