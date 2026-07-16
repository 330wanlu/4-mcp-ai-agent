"""AuthProvider 协议。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class UserContext:
    user_id: str
    display_name: str = "dev"
    roles: list[str] = field(default_factory=lambda: ["employee"])
    extra: dict[str, Any] = field(default_factory=dict)


class AuthProvider(ABC):
    """可替换鉴权实现；路由层通过 Depends 注入。"""

    name: str

    @abstractmethod
    async def resolve_user(self, headers: Mapping[str, str]) -> UserContext:
        raise NotImplementedError
