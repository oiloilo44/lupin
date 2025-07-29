from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import uuid
import json
from typing import Dict, Set

app = FastAPI(title="Lupin - 월급루팡 게임 사이트")

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 방 관리 시스템
rooms: Dict[str, Dict] = {}
connections: Dict[str, Set[WebSocket]] = {}

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/slither", response_class=HTMLResponse)
async def slither_game(request: Request):
    return templates.TemplateResponse("slither.html", {"request": request})

@app.get("/omok/create")
async def create_omok_room():
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {
        "game_type": "omok",
        "players": [],
        "game_state": {"board": [[0 for _ in range(15)] for _ in range(15)], "current_player": 1},
        "status": "waiting",
        "game_ended": False,
        "winner": None,
        "move_history": [],
        "undo_requests": {}
    }
    connections[room_id] = set()
    return {"room_id": room_id, "url": f"/omok/{room_id}"}

@app.get("/omok/{room_id}", response_class=HTMLResponse)
async def omok_room(request: Request, room_id: str):
    if room_id not in rooms:
        return HTMLResponse("<h1>방을 찾을 수 없습니다.</h1>", status_code=404)
    return templates.TemplateResponse("omok.html", {"request": request, "room_id": room_id})

@app.get("/janggi/create")
async def create_janggi_room():
    room_id = str(uuid.uuid4())[:8]
    rooms[room_id] = {
        "game_type": "janggi",
        "players": [],
        "game_state": {"board": None, "current_player": "red"},
        "status": "waiting"
    }
    connections[room_id] = set()
    return {"room_id": room_id, "url": f"/janggi/{room_id}"}

@app.get("/janggi/{room_id}", response_class=HTMLResponse)
async def janggi_room(request: Request, room_id: str):
    if room_id not in rooms:
        return HTMLResponse("<h1>방을 찾을 수 없습니다.</h1>", status_code=404)
    return templates.TemplateResponse("janggi.html", {"request": request, "room_id": room_id})

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    # 방이 존재하지 않는 경우 연결 종료
    if room_id not in rooms:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "방을 찾을 수 없습니다."
        }))
        await websocket.close()
        return
    
    if room_id not in connections:
        connections[room_id] = set()
    
    connections[room_id].add(websocket)
    
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
            
            if message["type"] == "join":
                if room_id in rooms:
                    room = rooms[room_id]
                    if len(room["players"]) < 2:
                        player_info = {
                            "nickname": message["nickname"],
                            "player_number": len(room["players"]) + 1
                        }
                        room["players"].append(player_info)
                        
                        if len(room["players"]) == 2:
                            room["status"] = "playing"
                        
                        # 모든 연결된 클라이언트에게 방 상태 전송
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "room_update",
                                "room": room
                            }))
            
            elif message["type"] == "move":
                if room_id in rooms:
                    room = rooms[room_id]
                    # 이동 기록 저장 (이동하기 전 상태를 기록)
                    if "last_move" in message:
                        # 이동하기 전의 보드 상태와 플레이어 정보를 저장
                        room["move_history"].append({
                            "move": message["last_move"],
                            "board_state": [row[:] for row in room["game_state"]["board"]],
                            "player": room["game_state"]["current_player"]
                        })
                    
                    # 게임별 이동 처리 로직 - 클라이언트 형식을 서버 형식으로 변환
                    client_game_state = message["game_state"]
                    room["game_state"] = {
                        "board": client_game_state["board"],
                        "current_player": client_game_state["currentPlayer"]
                    }
                    
                    for ws in connections[room_id]:
                        await ws.send_text(json.dumps({
                            "type": "game_update",
                            "game_state": {
                                "board": room["game_state"]["board"],
                                "currentPlayer": room["game_state"]["current_player"]
                            },
                            "last_move": message.get("last_move")
                        }))
            
            elif message["type"] == "game_end":
                if room_id in rooms:
                    room = rooms[room_id]
                    room["game_ended"] = True
                    room["winner"] = message["winner"]
                    # 클라이언트 형식을 서버 형식으로 변환
                    client_game_state = message["game_state"]
                    room["game_state"] = {
                        "board": client_game_state["board"],
                        "current_player": client_game_state["currentPlayer"]
                    }
                    
                    for ws in connections[room_id]:
                        await ws.send_text(json.dumps({
                            "type": "game_end",
                            "winner": message["winner"],
                            "game_state": {
                                "board": room["game_state"]["board"],
                                "currentPlayer": room["game_state"]["current_player"]
                            },
                            "last_move": message.get("last_move"),
                            "winning_line": message.get("winning_line")
                        }))
            
            elif message["type"] == "restart_request":
                if room_id in rooms:
                    room = rooms[room_id]
                    # 요청자가 아닌 다른 플레이어에게 재시작 요청 전송
                    for ws in connections[room_id]:
                        await ws.send_text(json.dumps({
                            "type": "restart_request",
                            "from": message["from"]
                        }))
            
            elif message["type"] == "restart_response":
                if room_id in rooms:
                    room = rooms[room_id]
                    if message["accepted"]:
                        # 재시작 승인
                        room["game_ended"] = False
                        room["winner"] = None
                        room["game_state"] = {"board": [[0 for _ in range(15)] for _ in range(15)], "current_player": 1}
                        room["move_history"] = []
                        room["undo_requests"] = {}
                        
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "restart_accepted",
                                "game_state": {
                                    "board": room["game_state"]["board"],
                                    "currentPlayer": room["game_state"]["current_player"]
                                }
                            }))
                    else:
                        # 재시작 거부
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "restart_rejected"
                            }))
            
            elif message["type"] == "undo_request":
                if room_id in rooms:
                    room = rooms[room_id]
                    if len(room["move_history"]) > 0 and not room["game_ended"]:
                        # 상대방에게 무르기 요청 전송
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "undo_request",
                                "from": message["from"]
                            }))
            
            elif message["type"] == "undo_response":
                if room_id in rooms:
                    room = rooms[room_id]
                    if message["accepted"] and len(room["move_history"]) > 0:
                        # 마지막 수 되돌리기
                        last_move = room["move_history"].pop()
                        
                        if len(room["move_history"]) > 0:
                            # 이전 상태로 복원
                            prev_state = room["move_history"][-1]
                            room["game_state"]["board"] = [row[:] for row in prev_state["board_state"]]
                            # 다음 플레이어 턴으로 설정 (마지막 이동한 플레이어의 다음 턴)
                            room["game_state"]["current_player"] = prev_state["player"]
                        else:
                            # 처음 상태로 복원
                            room["game_state"] = {"board": [[0 for _ in range(15)] for _ in range(15)], "current_player": 1}
                        
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "undo_accepted",
                                "game_state": {
                                    "board": room["game_state"]["board"],
                                    "currentPlayer": room["game_state"]["current_player"]
                                }
                            }))
                    else:
                        # 무르기 거부
                        for ws in connections[room_id]:
                            await ws.send_text(json.dumps({
                                "type": "undo_rejected"
                            }))
                        
    except WebSocketDisconnect:
        connections[room_id].discard(websocket)
        if not connections[room_id]:
            # 방에 아무도 없으면 방 삭제
            if room_id in rooms:
                del rooms[room_id]
            del connections[room_id]

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
