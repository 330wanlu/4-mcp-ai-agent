"""开发态：从 X-User-Id 读取用户。"""

from __future__ import annotations

from typing import Mapping

from ka_auth.base import AuthProvider, UserContext


class DevHeaderAuthProvider(AuthProvider):
    name = "dev_header"

    async def resolve_user(self, headers: Mapping[str, str]) -> UserContext:
        # HTTP 头大小写不敏感；兼容常见写法
        lowered = {k.lower(): v for k, v in headers.items()}
        user_id = lowered.get("x-user-id", "demo")
        roles_raw = lowered.get("x-user-roles", "employee")
        roles = [r.strip() for r in roles_raw.split(",") if r.strip()]
        return UserContext(user_id=user_id, display_name=user_id, roles=roles or ["employee"])
