"""开发调试：查看 Redis 会话完整状态。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ka_api.deps import CurrentUser, OrchestratorDep, SettingsDep
from ka_api.errors import ApiError

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/sessions/{session_id}")
async def debug_session(
    session_id: str,
    user: CurrentUser,
    orch: OrchestratorDep,
    settings: SettingsDep,
) -> dict[str, Any]:
    if not settings.debug_endpoints:
        raise ApiError("DEBUG_DISABLED", "调试接口已关闭", status_code=403)
    _ = user
    state = await orch.get_session(session_id)
    if not state.get("found"):
        raise ApiError(
            "SESSION_NOT_FOUND",
            f"会话不存在: {session_id}",
            status_code=404,
        )
    return {
        "found": True,
        "session_id": session_id,
        "orchestrator_mode": orch.mode,
        "state": {k: v for k, v in state.items() if k != "found"},
    }
