"""无鉴权：固定本地开发用户。"""

from __future__ import annotations

from typing import Mapping

from ka_auth.base import AuthProvider, UserContext


class NoAuthProvider(AuthProvider):
    name = "none"

    async def resolve_user(self, headers: Mapping[str, str]) -> UserContext:
        return UserContext(user_id="local-dev", display_name="本地开发用户", roles=["admin"])
