from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json

from .room_manager import room_manager
from .websocket_handler import websocket_handler

# 라우터 설정
router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/slither", response_class=HTMLResponse)
async def slither_game(request: Request):
    """슬리더 게임 페이지"""
    return templates.TemplateResponse("slither.html", {"request": request})


# 오목 게임 라우트
@router.get("/omok/create")
async def create_omok_room():
    """오목 방 생성"""
    room_id, url = room_manager.create_omok_room()
    return {"room_id": room_id, "url": url}


@router.get("/omok/{room_id}", response_class=HTMLResponse)
async def omok_room(request: Request, room_id: str):
    """오목 게임 방"""
    if not room_manager.room_exists(room_id):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_title": "게임 방을 찾을 수 없습니다",
            "error_message": "요청하신 오목 게임 방이 존재하지 않거나 이미 종료되었습니다."
        }, status_code=404)
    return templates.TemplateResponse("omok.html", {"request": request, "room_id": room_id})


# 장기 게임 라우트
@router.get("/janggi/create")
async def create_janggi_room():
    """장기 방 생성"""
    room_id, url = room_manager.create_janggi_room()
    return {"room_id": room_id, "url": url}


@router.get("/janggi/{room_id}", response_class=HTMLResponse)
async def janggi_room(request: Request, room_id: str):
    """장기 게임 방"""
    if not room_manager.room_exists(room_id):
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_title": "게임 방을 찾을 수 없습니다",
            "error_message": "요청하신 장기 게임 방이 존재하지 않거나 이미 종료되었습니다."
        }, status_code=404)
    return templates.TemplateResponse("janggi.html", {"request": request, "room_id": room_id})


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket 엔드포인트"""
    await websocket.accept()
    
    # 방이 존재하지 않는 경우 연결 종료
    if not room_manager.room_exists(room_id):
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "방을 찾을 수 없습니다."
        }))
        await websocket.close()
        return
    
    # 연결 추가
    room_manager.add_connection(room_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "잘못된 메시지 형식입니다."
                }))
                continue
            
            # 메시지 처리
            await websocket_handler.handle_message(websocket, room_id, message)
            
    except WebSocketDisconnect:
        room_manager.remove_connection(room_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        room_manager.remove_connection(room_id, websocket)