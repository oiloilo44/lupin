import json
from typing import Any, Dict

from fastapi import WebSocket

from .models import MessageType, WebSocketMessage
from .room_manager import room_manager
from .services.game_service import game_service


class WebSocketHandler:
    """WebSocket 메시지 처리 및 GameService로 위임"""

    def __init__(self):
        self.game_service = game_service

    async def handle_message(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """메시지 처리 메인 함수."""
        message_type = MessageType(message["type"])

        if message_type == MessageType.JOIN:
            await self._handle_join(websocket, room_id, message)
        elif message_type == MessageType.RECONNECT:
            await self._handle_reconnect(websocket, room_id, message)
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
        elif message_type == MessageType.CHAT_MESSAGE:
            await self._handle_chat_message(websocket, room_id, message)

    async def _handle_join(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """플레이어 참여 처리"""
        nickname = message.get("nickname")
        session_id = message.get("session_id")

        result = await self.game_service.handle_join(
            websocket, room_id, nickname, session_id
        )

        if result["success"]:
            await self._broadcast_room_update(room_id, result["room"])
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_reconnect(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재접속 처리"""
        session_id = message.get("session_id")

        result = await self.game_service.handle_reconnect(
            websocket, room_id, session_id
        )

        if result["success"]:
            await self._send_reconnect_success(
                websocket, result["room"], result["player"]
            )
            await self._notify_player_reconnected(room_id, result["player"].nickname)
            await self._broadcast_room_update(room_id, result["room"])
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_move(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """게임 이동 처리"""
        move = message.get("move")
        session_id = room_manager.get_session_id_by_websocket(websocket)

        if not session_id:
            await self._send_error(
                websocket, "세션 정보를 찾을 수 없습니다", "validation"
            )
            return

        result = await self.game_service.handle_move(
            websocket, room_id, move, session_id
        )

        if result["success"]:
            if result.get("game_ended"):
                # 게임 종료
                await self._broadcast_game_end(
                    room_id, result["last_move"], result.get("winning_line", []), result
                )
            else:
                # 일반 이동 업데이트
                await self._broadcast_game_update(
                    room_id, result["game_state"], result["last_move"]
                )
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _broadcast_game_end(
        self,
        room_id: str,
        last_move: Dict[str, Any],
        winning_line: list,
        result: Dict[str, Any],
    ):
        """게임 종료 브로드캐스트"""
        response = WebSocketMessage(
            type=MessageType.GAME_END,
            data={
                "winner": result.get("winner"),
                "game_state": result.get("game_state"),
                "last_move": last_move,
                "winning_line": winning_line,
            },
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _handle_game_end(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """게임 종료 처리 (클라이언트 직접 알림용 - 보안상 권장하지 않음)."""
        # 이 메서드는 하위 호환성을 위해 유지하지만,
        # 실제로는 _handle_move에서 게임 매니저를 통해 승리 조건을 검증해야 함
        room = room_manager.get_room(room_id)
        if not room:
            return

        # 이미 게임이 종료된 경우에만 브로드캐스트
        if room.game_ended:
            await self._broadcast_game_end(
                room_id,
                message.get("last_move", {}),
                message.get("winning_line", []),
                {"winner": room.winner, "game_state": room.game_state},
            )

    async def _handle_restart_request(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재시작 요청 처리"""
        from_player = message.get("from")

        result = await self.game_service.handle_restart_request(
            websocket, room_id, from_player
        )

        if result["success"]:
            await self._broadcast_restart_request(room_id, websocket, from_player or 0)
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_restart_response(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재시작 응답 처리"""
        accepted = message.get("accepted", False)

        result = await self.game_service.handle_restart_response(
            websocket, room_id, accepted
        )

        if result["success"]:
            if result["accepted"]:
                # 재시작 승인
                response = WebSocketMessage(
                    type=MessageType.RESTART_ACCEPTED,
                    data={
                        "game_state": result["game_state"],
                        "players": result["players"],
                        "games_played": result["games_played"],
                    },
                )
                await self._broadcast_to_room(room_id, response.to_json())
            else:
                # 재시작 거부
                await self._broadcast_restart_rejection(room_id, websocket)
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_undo_request(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """무르기 요청 처리"""
        from_player = message.get("from")
        session_id = room_manager.get_session_id_by_websocket(websocket)

        if not session_id:
            await self._send_error(
                websocket, "세션 정보를 찾을 수 없습니다", "validation"
            )
            return

        result = await self.game_service.handle_undo_request(
            websocket, room_id, from_player, session_id
        )

        if result["success"]:
            await self._broadcast_undo_request(
                room_id, websocket, from_player or 0, session_id
            )
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_undo_response(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """무르기 응답 처리"""
        accepted = message.get("accepted", False)
        session_id = room_manager.get_session_id_by_websocket(websocket)

        if not session_id:
            await self._send_error(
                websocket, "세션 정보를 찾을 수 없습니다", "validation"
            )
            return

        result = await self.game_service.handle_undo_response(
            websocket, room_id, accepted, session_id
        )

        if result["success"]:
            if result["accepted"]:
                # 무르기 승인
                response = WebSocketMessage(
                    type=MessageType.UNDO_ACCEPTED,
                    data={"game_state": result["game_state"]},
                )
                await self._broadcast_to_room(room_id, response.to_json())
            else:
                # 무르기 거부 - 요청자에게 알림
                await self._notify_undo_rejection(room_id)
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _handle_chat_message(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """채팅 메시지 처리"""
        chat_message = message.get("message")
        session_id = message.get("session_id")

        if not session_id:
            await self._send_error(websocket, "세션 정보가 필요합니다", "validation")
            return

        result = await self.game_service.handle_chat_message(
            websocket, room_id, chat_message, session_id
        )

        if result["success"]:
            # 채팅 메시지 브로드캐스트
            response = WebSocketMessage(
                type=MessageType.CHAT_BROADCAST,
                data=result["chat_message"],
            )
            await self._broadcast_to_room(room_id, response.to_json())
        else:
            await self._send_error(
                websocket, result["error"], result.get("error_type", "general")
            )

    async def _broadcast_room_update(self, room_id: str, room):
        """방 상태 업데이트 브로드캐스트."""
        response = WebSocketMessage(
            type=MessageType.ROOM_UPDATE,
            data={
                "room": {
                    "game_type": room.game_type.value,
                    "players": [
                        {
                            "nickname": p.nickname,
                            "player_number": p.player_number,
                            "color": p.color,
                        }
                        for p in room.players
                    ],
                    "game_state": room.game_state,
                    "status": room.status.value,
                    "game_ended": room.game_ended,
                    "winner": room.winner,
                    "games_played": room.games_played,
                    "chat_history": [
                        {
                            "nickname": msg.nickname,
                            "message": msg.message,
                            "timestamp": msg.timestamp,
                            "player_number": msg.player_number,
                        }
                        for msg in room.chat_history
                    ],
                }
            },
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _broadcast_game_update(
        self, room_id: str, game_state: Dict, last_move=None
    ):
        """게임 상태 업데이트 브로드캐스트."""
        response = WebSocketMessage(
            type=MessageType.GAME_UPDATE,
            data={
                "game_state": {
                    "board": game_state["board"],
                    "current_player": game_state["current_player"],
                },
                "last_move": last_move,
            },
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _send_error(
        self, websocket: WebSocket, message: str, error_type: str = "general"
    ):
        """통합 오류 메시지 전송 메서드."""
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "error_type": error_type,
                    "message": message,
                }
            )
        except Exception as e:
            import logging

            logging.error(f"오류 메시지 전송 실패: {e}")

    async def _send_reconnect_success(self, websocket: WebSocket, room, player):
        """재접속 성공 메시지 전송."""
        response = WebSocketMessage(
            type=MessageType.RECONNECT_SUCCESS,
            data={
                "player": {
                    "nickname": player.nickname,
                    "player_number": player.player_number,
                    "color": player.color,
                },
                "room": {
                    "game_type": room.game_type.value,
                    "players": [
                        {
                            "nickname": p.nickname,
                            "player_number": p.player_number,
                            "is_connected": p.is_connected,
                            "color": p.color,
                        }
                        for p in room.players
                    ],
                    "game_state": {
                        "board": room.game_state["board"],
                        "current_player": room.game_state["current_player"],
                    },
                    "status": room.status.value,
                    "game_ended": room.game_ended,
                    "winner": room.winner,
                    "games_played": room.games_played,
                    "chat_history": [
                        {
                            "nickname": msg.nickname,
                            "message": msg.message,
                            "timestamp": msg.timestamp,
                            "player_number": msg.player_number,
                        }
                        for msg in room.chat_history
                    ],
                },
                "move_history": [
                    {
                        "move": {
                            "x": entry.move.x,
                            "y": entry.move.y,
                            "player": entry.move.player,
                        },
                        "player": entry.player,
                    }
                    for entry in room.move_history
                ],
            },
        )
        try:
            await websocket.send_text(json.dumps(response.to_json()))
        except Exception:
            pass

    async def _notify_player_reconnected(self, room_id: str, nickname: str):
        """상대방에게 재접속 알림."""
        response = WebSocketMessage(
            type=MessageType.PLAYER_RECONNECTED, data={"nickname": nickname}
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _notify_player_disconnected(self, room_id: str, nickname: str):
        """상대방에게 연결 끊김 알림"""
        response = WebSocketMessage(
            type=MessageType.PLAYER_DISCONNECTED, data={"nickname": nickname}
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _broadcast_restart_request(
        self, room_id: str, requester_ws: WebSocket, from_player: int
    ):
        """재시작 요청 브로드캐스트"""
        connections = room_manager.get_room_connections(room_id)

        for ws in connections:
            try:
                if ws == requester_ws:  # 요청자
                    waiting_response = WebSocketMessage(
                        type=MessageType.RESTART_REQUEST,
                        data={
                            "from": from_player,
                            "is_requester": True,
                        },
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방
                    confirm_response = WebSocketMessage(
                        type=MessageType.RESTART_REQUEST,
                        data={
                            "from": from_player,
                            "is_requester": False,
                        },
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except Exception:
                pass

    async def _broadcast_restart_rejection(self, room_id: str, rejector_ws: WebSocket):
        """재시작 거부 브로드캐스트"""
        connections = room_manager.get_room_connections(room_id)
        rejection_response = WebSocketMessage(
            type=MessageType.RESTART_REJECTED, data={}
        )

        for ws in connections:
            if ws != rejector_ws:  # 거부한 사람은 제외
                try:
                    await ws.send_text(json.dumps(rejection_response.to_json()))
                except Exception:
                    pass

    async def _broadcast_undo_request(
        self,
        room_id: str,
        requester_ws: WebSocket,
        from_player: int,
        requester_session_id: str,
    ):
        """무르기 요청 브로드캐스트"""
        connections = room_manager.get_room_connections(room_id)

        for ws in connections:
            try:
                ws_session_id = room_manager.get_session_id_by_websocket(ws)

                if ws_session_id == requester_session_id:  # 요청자
                    waiting_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": from_player,
                            "is_requester": True,
                        },
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방
                    confirm_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": from_player,
                            "is_requester": False,
                        },
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except Exception:
                pass

    async def _notify_undo_rejection(self, room_id: str):
        """무르기 거부 알림"""
        room = room_manager.get_room(room_id)
        if room:
            requester_ws = room.undo_requests.get("requester_websocket")
            if requester_ws:
                response = WebSocketMessage(type=MessageType.UNDO_REJECTED, data={})
                try:
                    await requester_ws.send_text(json.dumps(response.to_json()))
                except Exception:
                    pass

    async def _broadcast_to_room(self, room_id: str, message: Dict):
        """방의 모든 연결에 메시지 브로드캐스트."""
        connections = room_manager.get_room_connections(room_id)
        for websocket in connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception:
                # 연결이 끊어진 경우 무시
                pass


# 전역 핸들러 인스턴스
websocket_handler = WebSocketHandler()
