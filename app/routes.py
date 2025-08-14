"""FastAPI routes for the Lupin game website."""
import json

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .room_manager import room_manager
from .session_manager import session_manager
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
@router.post("/omok/create")
async def create_omok_room():
    """오목 방 생성"""
    room_id, url = room_manager.create_omok_room()
    return {"room_id": room_id, "url": url}


@router.get("/omok/{room_id}", response_class=HTMLResponse)
async def omok_room(request: Request, response: Response, room_id: str):
    """오목 게임 방"""
    # 방 존재 여부 확인
    if not room_manager.room_exists(room_id):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "게임 방을 찾을 수 없습니다",
                "error_message": "요청하신 오목 게임 방이 존재하지 않거나 이미 종료되었습니다.",
            },
            status_code=404,
        )

    # 세션 관리
    session_id = session_manager.get_session_id(request)
    current_room_id = None
    player_data = {}

    if session_id:
        # 기존 세션이 있는 경우
        session_data = session_manager.get_session_data(session_id)
        if session_data:
            current_room_id = session_data.get("room_id")
            player_data = session_data.get("player_data", {})

            # 다른 방에 접속 중인지 확인
            if current_room_id and current_room_id != room_id:
                # 기존 방이 여전히 존재하는지 확인
                if room_manager.room_exists(current_room_id):
                    return templates.TemplateResponse(
                        "error.html",
                        {
                            "request": request,
                            "error_title": "이미 다른 게임에 참여 중입니다",
                            "error_message": (
                                f"현재 방 {current_room_id}에서 게임 중입니다. "
                                "먼저 해당 게임을 종료해주세요."
                            ),
                        },
                        status_code=409,
                    )
                else:
                    # 기존 방이 삭제되었다면 세션의 room_id 초기화
                    session_manager.update_session(session_id, {"room_id": None})
            # 세션의 room_id 업데이트
            session_manager.set_room_id(session_id, room_id)
        else:
            # 세션이 만료된 경우 새로 생성
            session_id = session_manager.create_session(response)
            session_manager.set_room_id(session_id, room_id)
    else:
        # 세션이 없는 경우 새로 생성
        session_id = session_manager.create_session(response)
        session_manager.set_room_id(session_id, room_id)

    # 방 정보 조회
    room = room_manager.get_room(room_id)

    # 템플릿에 전달할 컨텍스트 준비
    context = {
        "request": request,
        "room_id": room_id,
        "session_id": session_id,
        "player_data": player_data,
        "room_status": room.status.value if room else "waiting",
        "game_state": room.game_state if room else None,
    }

    return templates.TemplateResponse("omok.html", context)


# 장기 게임 라우트
@router.post("/janggi/create")
async def create_janggi_room():
    """장기 방 생성"""
    room_id, url = room_manager.create_janggi_room()
    return {"room_id": room_id, "url": url}


@router.get("/janggi/{room_id}", response_class=HTMLResponse)
async def janggi_room(request: Request, room_id: str):
    """장기 게임 방"""
    if not room_manager.room_exists(room_id):
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "게임 방을 찾을 수 없습니다",
                "error_message": "요청하신 장기 게임 방이 존재하지 않거나 이미 종료되었습니다.",
            },
            status_code=404,
        )
    return templates.TemplateResponse(
        "janggi.html", {"request": request, "room_id": room_id}
    )


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket 엔드포인트"""
    await websocket.accept()

    # 방이 존재하지 않는 경우 연결 종료
    if not room_manager.room_exists(room_id):
        await websocket.send_text(
            json.dumps({"type": "error", "message": "방을 찾을 수 없습니다."})
        )
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "잘못된 메시지 형식입니다."})
                )
                continue

            # 메시지 처리
            await websocket_handler.handle_message(websocket, room_id, message)

    except WebSocketDisconnect:
        await _handle_disconnect(room_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await _handle_disconnect(room_id, websocket)


async def _handle_disconnect(room_id: str, websocket: WebSocket):
    """WebSocket 연결 해제 처리"""
    # WebSocket에서 세션 ID 찾기
    session_id = room_manager.get_session_id_by_websocket(websocket)

    # 연결이 끊어진 플레이어 찾기
    disconnected_player = None
    room = room_manager.get_room(room_id)

    if room and session_id:
        # 세션 ID로 플레이어 찾기
        for player in room.players:
            if player.session_id == session_id:
                disconnected_player = player
                break

    # 연결 제거 (세션 ID와 함께)
    room_manager.remove_connection(room_id, websocket, session_id)

    # 연결 끊김 알림 (상대방에게)
    if disconnected_player and room:
        from .websocket_handler import websocket_handler

        await websocket_handler._notify_player_disconnected(
            room_id, disconnected_player.nickname
        )
