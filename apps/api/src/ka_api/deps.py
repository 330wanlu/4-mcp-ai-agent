"""依赖注入：Auth / Settings / Orchestrator 客户端。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request

from ka_auth import AuthProvider, UserContext, get_auth_provider
from ka_common.config import Settings, get_settings
from ka_api.orchestrator_client import OrchestratorClient


def settings_dep() -> Settings:
    return get_settings()


def auth_provider_dep(settings: Annotated[Settings, Depends(settings_dep)]) -> AuthProvider:
    return get_auth_provider(settings)


async def get_current_user(
    request: Request,
    auth: Annotated[AuthProvider, Depends(auth_provider_dep)],
) -> UserContext:
    """预留 Depends(get_current_user)；切换 AuthProvider 无需大改路由。"""
    return await auth.resolve_user(dict(request.headers))


async def orchestrator_client_dep(
    settings: Annotated[Settings, Depends(settings_dep)],
) -> AsyncIterator[OrchestratorClient]:
    client = OrchestratorClient(settings)
    try:
        yield client
    finally:
        await client.close()


CurrentUser = Annotated[UserContext, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(settings_dep)]
OrchestratorDep = Annotated[OrchestratorClient, Depends(orchestrator_client_dep)]
AuthDep = Annotated[AuthProvider, Depends(auth_provider_dep)]
