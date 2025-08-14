"""Lupin - 월급루팡 게임 사이트의 메인 진입점."""
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.health_routes import router as health_router
from app.config import get_config
from app.routes import router

# FastAPI 앱 생성
app = FastAPI(title="Lupin - 월급루팡 게임 사이트")

# 정적 파일 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 라우터 등록
app.include_router(router)
app.include_router(health_router)

if __name__ == "__main__":
    import sys

    # 설정 로드
    config = get_config("default")
    server_config = config.get("server", {})

    # 커맨드라인 인자 우선, 없으면 설정 파일, 최종적으로 기본값
    port = (
        int(sys.argv[1])
        if len(sys.argv) > 1
        else server_config.get("port", 8000)
    )
    host = server_config.get("host", "0.0.0.0")
    debug = server_config.get("debug", False)

    print(f"서버 시작: {host}: {port} (debug={debug})")
    uvicorn.run(
        app, host=host, port=port, log_level="debug" if debug else "info"
    )
