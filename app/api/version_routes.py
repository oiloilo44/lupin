"""버전 API 라우트."""

from fastapi import APIRouter

from ..version import APP_VERSION

router = APIRouter(prefix="/api")


@router.get("/version")
async def get_version():
    """현재 애플리케이션 버전 반환."""
    return {"version": APP_VERSION}
