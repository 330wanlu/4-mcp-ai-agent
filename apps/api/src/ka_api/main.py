"""API 入口：Chat / 审计 / Debug + Auth 扩展点（阶段 3）。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ka_api.deps import AuthDep, CurrentUser
from ka_api.errors import register_exception_handlers
from ka_api.routers import audit, chat, debug
from ka_common.config import get_settings
from ka_common.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    log = get_logger("ka_api")

    application = FastAPI(
        title="Knowledge Action Cluster API",
        version="0.3.0",
        description=(
            "阶段 3：Chat 会话/消息、审计查询、Debug；"
            "鉴权通过 AuthProvider + Depends(get_current_user) 挂载。"
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)

    application.include_router(chat.router)
    application.include_router(audit.router)
    application.include_router(debug.router)

    @application.get("/health")
    async def health(auth: AuthDep) -> dict[str, str]:
        return {
            "status": "ok",
            "service": "api",
            "phase": "3",
            "auth_provider": auth.name,
            "orchestrator_mode": settings.orchestrator_mode,
        }

    @application.get("/me")
    async def me(user: CurrentUser) -> dict[str, object]:
        return {
            "user_id": user.user_id,
            "display_name": user.display_name,
            "roles": user.roles,
        }

    log.info(
        "api_started",
        auth_provider=settings.auth_provider,
        orchestrator_mode=settings.orchestrator_mode,
    )
    return application


app = create_app()
