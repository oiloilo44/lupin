"""버전 API 라우트."""

from fastapi import APIRouter

from ..version import clear_version_cache, get_current_app_version

router = APIRouter(prefix="/api")


@router.get("/version")
async def get_version():
    """현재 애플리케이션 버전 반환 (동적 생성)."""
    return {"version": get_current_app_version()}


@router.post("/version/clear-cache")
async def clear_cache():
    """버전 캐시 클리어 (개발용)."""
    clear_version_cache()
    return {
        "message": "Version cache cleared",
        "new_version": get_current_app_version(),
    }
