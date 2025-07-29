import json
from typing import Dict, Any
from fastapi import WebSocket

from .models import MessageType, WebSocketMessage, GameMove, OmokGameState
from .room_manager import room_manager
from .games.omok import OmokGame


class WebSocketHandler:
    """WebSocket 메시지 처리"""
    
    async def handle_message(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """메시지 처리 메인 함수"""
        message_type = MessageType(message["type"])
        
        if message_type == MessageType.JOIN:
            await self._handle_join(websocket, room_id, message)
        elif message_type == MessageType.MOVE:
            await self._handle_move(websocket, room_id, message)
        elif message_type == MessageType.GAME_END:
            await self._handle_game_end(websocket, room_id, message)
        elif message_type == MessageType.RESTART_REQUEST:
            await self._handle_restart_request(websocket, room_id, message)
        elif message_type == MessageType.RESTART_RESPONSE:
            await self._handle_restart_response(websocket, room_id, message)
        elif message_type == MessageType.UNDO_REQUEST:
            await self._handle_undo_request(websocket, room_id, message)
        elif message_type == MessageType.UNDO_RESPONSE:
            await self._handle_undo_response(websocket, room_id, message)
    
    async def _handle_join(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """플레이어 참여 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        player = room.add_player(message["nickname"])
        if player:
            await self._broadcast_room_update(room_id, room)
    
    async def _handle_move(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """게임 이동 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        # 이동 기록 저장
        if "last_move" in message:
            move = GameMove(
                x=message["last_move"]["x"],
                y=message["last_move"]["y"],
                player=room.game_state["current_player"]
            )
            
            history_entry = OmokGame.create_move_history_entry(
                move=move,
                board_state=room.game_state["board"],
                player=room.game_state["current_player"]
            )
            room.move_history.append(history_entry)
        
        # 게임 상태 업데이트
        client_game_state = message["game_state"]
        room.game_state = {
            "board": client_game_state["board"],
            "current_player": client_game_state["currentPlayer"]
        }
        
        await self._broadcast_game_update(room_id, room.game_state, message.get("last_move"))
    
    async def _handle_game_end(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """게임 종료 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        room.game_ended = True
        room.winner = message["winner"]
        
        # 게임 상태 업데이트
        client_game_state = message["game_state"]
        room.game_state = {
            "board": client_game_state["board"],
            "current_player": client_game_state["currentPlayer"]
        }
        
        response = WebSocketMessage(
            type=MessageType.GAME_END,
            data={
                "winner": message["winner"],
                "game_state": {
                    "board": room.game_state["board"],
                    "currentPlayer": room.game_state["current_player"]
                },
                "last_move": message.get("last_move"),
                "winning_line": message.get("winning_line")
            }
        )
        
        await self._broadcast_to_room(room_id, response.to_json())
    
    async def _handle_restart_request(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """재시작 요청 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        requester_player_number = message["from"]
        connections = room_manager.get_room_connections(room_id)
        
        # 각 플레이어에게 다른 메시지 전송
        for ws in connections:
            try:
                # 요청자에게는 대기 메시지
                if ws == websocket:  # 요청자
                    waiting_response = WebSocketMessage(
                        type=MessageType.RESTART_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": True
                        }
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방에게는 동의 여부 확인
                    confirm_response = WebSocketMessage(
                        type=MessageType.RESTART_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": False
                        }
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except:
                # 연결이 끊어진 경우 무시
                pass
    
    async def _handle_restart_response(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """재시작 응답 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        if message["accepted"]:
            # 재시작 승인
            room_manager.reset_omok_game(room_id)
            
            response = WebSocketMessage(
                type=MessageType.RESTART_ACCEPTED,
                data={
                    "game_state": {
                        "board": room.game_state["board"],
                        "currentPlayer": room.game_state["current_player"]
                    }
                }
            )
        else:
            # 재시작 거부
            response = WebSocketMessage(
                type=MessageType.RESTART_REJECTED,
                data={}
            )
        
        await self._broadcast_to_room(room_id, response.to_json())
    
    async def _handle_undo_request(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """무르기 요청 처리"""
        room = room_manager.get_room(room_id)
        if not room or len(room.move_history) == 0 or room.game_ended:
            return
        
        requester_player_number = message["from"]
        connections = room_manager.get_room_connections(room_id)
        
        # 각 플레이어에게 다른 메시지 전송
        for ws in connections:
            try:
                # 요청자에게는 대기 메시지
                if ws == websocket:  # 요청자
                    waiting_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": True
                        }
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방에게는 동의 여부 확인
                    confirm_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": False
                        }
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except:
                # 연결이 끊어진 경우 무시
                pass
    
    async def _handle_undo_response(self, websocket: WebSocket, room_id: str, message: Dict[str, Any]):
        """무르기 응답 처리"""
        room = room_manager.get_room(room_id)
        if not room:
            return
        
        if message["accepted"] and len(room.move_history) > 0:
            # 무르기 승인
            game_state = OmokGameState(
                board=room.game_state["board"],
                current_player=room.game_state["current_player"]
            )
            
            if OmokGame.undo_last_move(game_state, room.move_history):
                room.game_state = {
                    "board": game_state.board,
                    "current_player": game_state.current_player
                }
                
                response = WebSocketMessage(
                    type=MessageType.UNDO_ACCEPTED,
                    data={
                        "game_state": {
                            "board": room.game_state["board"],
                            "currentPlayer": room.game_state["current_player"]
                        }
                    }
                )
            else:
                response = WebSocketMessage(
                    type=MessageType.UNDO_REJECTED,
                    data={}
                )
        else:
            # 무르기 거부
            response = WebSocketMessage(
                type=MessageType.UNDO_REJECTED,
                data={}
            )
        
        await self._broadcast_to_room(room_id, response.to_json())
    
    async def _broadcast_room_update(self, room_id: str, room):
        """방 상태 업데이트 브로드캐스트"""
        response = WebSocketMessage(
            type=MessageType.ROOM_UPDATE,
            data={
                "room": {
                    "game_type": room.game_type.value,
                    "players": [
                        {"nickname": p.nickname, "player_number": p.player_number}
                        for p in room.players
                    ],
                    "game_state": room.game_state,
                    "status": room.status.value,
                    "game_ended": room.game_ended,
                    "winner": room.winner
                }
            }
        )
        await self._broadcast_to_room(room_id, response.to_json())
    
    async def _broadcast_game_update(self, room_id: str, game_state: Dict, last_move=None):
        """게임 상태 업데이트 브로드캐스트"""
        response = WebSocketMessage(
            type=MessageType.GAME_UPDATE,
            data={
                "game_state": {
                    "board": game_state["board"],
                    "currentPlayer": game_state["current_player"]
                },
                "last_move": last_move
            }
        )
        await self._broadcast_to_room(room_id, response.to_json())
    
    async def _broadcast_to_room(self, room_id: str, message: Dict):
        """방의 모든 연결에 메시지 브로드캐스트"""
        connections = room_manager.get_room_connections(room_id)
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                # 연결이 끊어진 경우 무시
                pass


# 전역 핸들러 인스턴스
websocket_handler = WebSocketHandler()