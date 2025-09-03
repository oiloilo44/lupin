"""Lupin - 월급루팡 게임 사이트의 메인 진입점."""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from app.api.health_routes import router as health_router
from app.api.version_routes import router as version_router
from app.config import get_config
from app.exceptions.game_exceptions import (
    GameError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from app.routes import router

# FastAPI 앱 생성
app = FastAPI(title="Lupin - 월급루팡 게임 사이트")


class CustomStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        # 정적 파일에 대해 긴 캐시 유효기간 설정 (버전 관리와 함께 사용)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.mount("/static", CustomStaticFiles(directory="static"), name="static")


# Exception handlers 등록
@app.exception_handler(GameError)
async def game_error_handler(request: Request, exc: GameError):
    """게임 에러 핸들러"""
    return JSONResponse(status_code=400, content=exc.to_dict())


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """검증 에러 핸들러"""
    return JSONResponse(status_code=422, content=exc.to_dict())


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """속도 제한 에러 핸들러"""
    return JSONResponse(status_code=429, content=exc.to_dict())


@app.exception_handler(ServerError)
async def server_error_handler(request: Request, exc: ServerError):
    """서버 에러 핸들러"""
    import logging

    logging.error(f"Server error: {exc.message}", exc_info=True)
    return JSONResponse(status_code=500, content=exc.to_dict())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    import logging

    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다",
            "details": {},
        },
    )


# 라우터 등록
app.include_router(router)
app.include_router(health_router)
app.include_router(version_router)

if __name__ == "__main__":
    import sys

    # 설정 로드
    config = get_config("default")
    server_config = config.get("server", {})

    # 커맨드라인 인자 우선, 없으면 설정 파일, 최종적으로 기본값
    port = int(sys.argv[1]) if len(sys.argv) > 1 else server_config.get("port", 8000)
    host = server_config.get("host", "0.0.0.0")
    debug = server_config.get("debug", False)

    print(f"서버 시작: {host}: {port} (debug={debug})")
    uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")
