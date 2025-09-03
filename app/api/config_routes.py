"""설정 관리 API 라우트."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..config import get_config, get_game_config
from ..config.runtime_config import (
    clear_runtime_overrides,
    get_runtime_config_manager,
    set_game_config,
    set_server_config,
)
from ..monitoring.config_metrics import get_config_metrics

router = APIRouter(prefix="/api/config", tags=["config"])

config_metrics = get_config_metrics()


class ConfigUpdateRequest(BaseModel):
    """설정 업데이트 요청 모델."""

    path: str
    value: Any


class GameConfigUpdateRequest(BaseModel):
    """게임 설정 업데이트 요청 모델."""

    game_name: str
    path: str
    value: Any


@router.get("/")
async def get_all_configs() -> Dict[str, Any]:
    """모든 설정 조회."""
    server_config = get_config("default")
    omok_config = get_game_config("omok")

    return {"server": server_config, "games": {"omok": omok_config}}


@router.get("/server")
async def get_server_config() -> Dict[str, Any]:
    """서버 설정 조회."""
    return get_config("default")


@router.get("/games/{game_name}")
async def get_game_config_by_name(game_name: str) -> Dict[str, Any]:
    """게임별 설정 조회 (런타임 오버라이드 적용)."""
    runtime_manager = get_runtime_config_manager()
    base_config = get_game_config(game_name)
    # 런타임 오버라이드 적용
    return runtime_manager.apply_overrides_to_config(base_config, game_name)


@router.post("/server/update")
async def update_server_config(request: ConfigUpdateRequest) -> Dict[str, str]:
    """서버 설정 업데이트."""
    # 이전 값 저장 (변경 추적용)
    old_value = None
    try:
        config = get_config()
        path_parts = request.path.split(".")
        old_value = config
        for part in path_parts:
            if isinstance(old_value, dict):
                old_value = old_value.get(part)
                if old_value is None:
                    break
            else:
                old_value = None
                break
    except Exception:
        old_value = None

    success = set_server_config(request.path, request.value)

    if success:
        # 설정 변경 메트릭 기록
        config_metrics.record_config_change(
            config_name="server",
            path=request.path,
            old_value=old_value,
            new_value=request.value,
            source="api",
        )
        return {
            "message": (f"서버 설정 업데이트 성공: {request.path} = {request.value}")
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"서버 설정 업데이트 실패: {request.path}",
        )


@router.post("/games/update")
async def update_game_config(
    request: GameConfigUpdateRequest,
) -> Dict[str, str]:
    """게임 설정 업데이트."""
    # 이전 값 저장 (변경 추적용)
    old_value = None
    try:
        game_config = get_game_config(request.game_name)
        path_parts = request.path.split(".")
        old_value = game_config
        for part in path_parts:
            if isinstance(old_value, dict):
                old_value = old_value.get(part)
                if old_value is None:
                    break
            else:
                old_value = None
                break
    except Exception:
        old_value = None

    success = set_game_config(request.game_name, request.path, request.value)

    if success:
        # 설정 변경 메트릭 기록
        config_metrics.record_config_change(
            config_name=f"game.{request.game_name}",
            path=request.path,
            old_value=old_value,
            new_value=request.value,
            source="api",
        )
        return {
            "message": (
                f"게임 설정 업데이트 성공: "
                f"{request.game_name}.{request.path} = {request.value}"
            )
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"게임 설정 업데이트 실패: " f"{request.game_name}.{request.path}"),
        )


@router.get("/runtime-overrides")
async def get_runtime_overrides() -> Dict[str, Any]:
    """현재 런타임 오버라이드 조회."""
    runtime_manager = get_runtime_config_manager()
    return runtime_manager.get_runtime_overrides()


@router.delete("/runtime-overrides")
async def clear_all_runtime_overrides() -> Dict[str, str]:
    """모든 런타임 오버라이드 제거."""
    clear_runtime_overrides()
    return {"message": "모든 런타임 오버라이드가 제거되었습니다"}


@router.delete("/runtime-overrides/{config_name}")
async def clear_config_runtime_overrides(config_name: str) -> Dict[str, str]:
    """특정 설정의 런타임 오버라이드 제거."""
    clear_runtime_overrides(config_name)
    return {"message": f"{config_name} 런타임 오버라이드가 제거되었습니다"}
