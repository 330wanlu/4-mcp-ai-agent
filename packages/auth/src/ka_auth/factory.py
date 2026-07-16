"""按配置选择 AuthProvider。"""

from __future__ import annotations

from ka_auth.base import AuthProvider
from ka_auth.dev_header import DevHeaderAuthProvider
from ka_auth.none import NoAuthProvider
from ka_common.config import Settings, get_settings


def get_auth_provider(settings: Settings | None = None) -> AuthProvider:
    settings = settings or get_settings()
    mapping: dict[str, type[AuthProvider]] = {
        "none": NoAuthProvider,
        "dev_header": DevHeaderAuthProvider,
    }
    cls = mapping.get(settings.auth_provider.lower())
    if cls is None:
        raise ValueError(
            f"未知 AUTH_PROVIDER={settings.auth_provider!r}；可选: {sorted(mapping)}"
        )
    return cls()
