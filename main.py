from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.routes import router

# FastAPI 앱 생성
app = FastAPI(title="Lupin - 월급루팡 게임 사이트")

# 정적 파일 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 라우터 등록
app.include_router(router)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
