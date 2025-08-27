"""버전 API 라우트."""

import os

from fastapi import APIRouter, HTTPException

from ..version import clear_version_cache, get_current_app_version

router = APIRouter(prefix="/api")


@router.get("/version")
async def get_version():
    """현재 애플리케이션 버전 반환 (동적 생성)."""
    return {"version": get_current_app_version()}


@router.post("/version/clear-cache")
async def clear_cache():
    """버전 캐시 클리어 (개발용)."""
    # 개발 환경에서만 허용
    if os.getenv("DEBUG", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")

    clear_version_cache()
    return {
        "message": "Version cache cleared",
        "new_version": get_current_app_version(),
    }
