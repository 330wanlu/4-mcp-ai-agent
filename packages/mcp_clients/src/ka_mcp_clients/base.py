"""通用 MCP HTTP 客户端骨架。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class McpClient:
    """阶段 0 仅保存 base_url；阶段 1 起对接各 MCP Server。"""

    name: str
    base_url: str

    def describe(self) -> str:
        return f"McpClient(name={self.name}, base_url={self.base_url})"
