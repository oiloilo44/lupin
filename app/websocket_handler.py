import json
from datetime import datetime
from typing import Any, Dict

from fastapi import WebSocket

from .games.omok import OmokGame
from .models import (
    ChatMessage,
    GameMove,
    MessageType,
    OmokGameState,
    WebSocketMessage,
)
from .room_manager import room_manager
from .session_manager import session_manager


class WebSocketHandler:
    """WebSocket 메시지 처리."""

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
        """플레이어 참여 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        session_id = message.get("session_id")
        nickname = message["nickname"]

        # 세션이 있으면 해당 세션으로 플레이어 추가
        if session_id:
            player = room_manager.add_player_to_room(
                room_id, nickname, session_id
            )
        else:
            # 세션이 없는 경우에도 session_id를 생성해서 플레이어 추가
            temp_session_id = session_manager.generate_session_id()
            player = room_manager.add_player_to_room(
                room_id, nickname, temp_session_id
            )
            session_id = temp_session_id  # WebSocket 연결 시 사용하기 위해

        if player:
            # 플레이어 연결 상태 업데이트
            room_manager.update_player_connection_status(
                room_id, str(player.player_number), True
            )

            # WebSocket 연결 추가 (세션 ID와 함께)
            room_manager.add_connection(room_id, websocket, session_id)

            # 두 번째 플레이어 참여 시 색상 배정
            if len(room.players) == 2:
                room_manager.assign_colors(room)

            await self._broadcast_room_update(room_id, room)

    async def _handle_reconnect(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재접속 처리."""
        session_id = message.get("session_id")
        if not session_id:
            await self._send_error(websocket, "세션 정보가 없습니다.")
            return

        # 세션으로 플레이어 찾기
        result = room_manager.find_player_by_session(session_id)
        if not result:
            await self._send_error(websocket, "재접속할 게임을 찾을 수 없습니다.")
            return

        player, room = result
        if not player or not room:
            await self._send_error(websocket, "재접속할 게임을 찾을 수 없습니다.")
            return

        # 다른 방에 접속 시도하는 경우
        if room.room_id != room_id:
            await self._send_error(
                websocket, f"다른 게임 방({room.room_id})에 참여 중입니다."
            )
            return

        # 재접속 처리
        success = room_manager.handle_reconnection(
            room_id, session_id, websocket
        )
        if not success:
            await self._send_error(websocket, "재접속에 실패했습니다.")
            return

        # 성공적인 재접속 알림
        await self._send_reconnect_success(websocket, room, player)

        # 상대방에게 재접속 알림
        await self._notify_player_reconnected(room_id, player.nickname)

        # 방 상태 업데이트
        await self._broadcast_room_update(room_id, room)

    async def _handle_move(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """게임 이동 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        # 이동 기록 저장
        if "last_move" in message:
            move = GameMove(
                x=message["last_move"]["x"],
                y=message["last_move"]["y"],
                player=room.game_state["current_player"],
            )

            history_entry = OmokGame.create_move_history_entry(
                move=move,
                board_state=room.game_state["board"],
                player=room.game_state["current_player"],
            )
            room.move_history.append(history_entry)

        # 게임 상태 업데이트
        client_game_state = message["game_state"]
        room.game_state = {
            "board": client_game_state["board"],
            "current_player": client_game_state["currentPlayer"],
        }

        await self._broadcast_game_update(
            room_id, room.game_state, message.get("last_move")
        )

    async def _handle_game_end(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """게임 종료 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        room.game_ended = True
        room.winner = message["winner"]
        room.last_winner = message["winner"]  # 다음 게임 색상 배정을 위해 저장

        # 게임 상태 업데이트
        client_game_state = message["game_state"]
        room.game_state = {
            "board": client_game_state["board"],
            "current_player": client_game_state["currentPlayer"],
        }

        response = WebSocketMessage(
            type=MessageType.GAME_END,
            data={
                "winner": message["winner"],
                "game_state": {
                    "board": room.game_state["board"],
                    "currentPlayer": room.game_state["current_player"],
                },
                "last_move": message.get("last_move"),
                "winning_line": message.get("winning_line"),
            },
        )

        await self._broadcast_to_room(room_id, response.to_json())

    async def _handle_restart_request(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재시작 요청 처리."""
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
                            "is_requester": True,
                        },
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방에게는 동의 여부 확인
                    confirm_response = WebSocketMessage(
                        type=MessageType.RESTART_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": False,
                        },
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except Exception:
                # 연결이 끊어진 경우 무시
                pass

    async def _handle_restart_response(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """재시작 응답 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        if message["accepted"]:
            # 재시작 승인 - 모든 플레이어에게 알림
            room_manager.reset_omok_game(room_id)

            response = WebSocketMessage(
                type=MessageType.RESTART_ACCEPTED,
                data={
                    "game_state": {
                        "board": room.game_state["board"],
                        "currentPlayer": room.game_state["current_player"],
                    },
                    "players": [
                        {
                            "nickname": p.nickname,
                            "player_number": p.player_number,
                            "color": p.color,
                        }
                        for p in room.players
                    ],
                    "games_played": room.games_played,
                },
            )
            await self._broadcast_to_room(room_id, response.to_json())
        else:
            # 재시작 거부 - 요청자에게만 알림
            connections = room_manager.get_room_connections(room_id)
            rejection_response = WebSocketMessage(
                type=MessageType.RESTART_REJECTED, data={}
            )

            # 현재 웹소켓(거부한 사람)을 제외하고 다른 모든 연결에 전송
            for ws in connections:
                if ws != websocket:  # 거부한 사람은 제외
                    try:
                        await ws.send_text(
                            json.dumps(rejection_response.to_json())
                        )
                    except Exception:
                        # 연결이 끊어진 경우 무시
                        pass

    async def _handle_undo_request(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """무르기 요청 처리."""
        room = room_manager.get_room(room_id)
        if not room or len(room.move_history) == 0 or room.game_ended:
            return

        requester_player_number = message["from"]
        connections = room_manager.get_room_connections(room_id)

        # 무르기 요청자 정보를 방에 저장 (응답 처리 시 사용)
        room.undo_requests["requester"] = requester_player_number
        room.undo_requests["requester_websocket"] = websocket

        # 각 플레이어에게 다른 메시지 전송
        for ws in connections:
            try:
                # 요청자에게는 대기 메시지
                if ws == websocket:  # 요청자
                    waiting_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": True,
                        },
                    )
                    await ws.send_text(json.dumps(waiting_response.to_json()))
                else:  # 상대방에게는 동의 여부 확인
                    confirm_response = WebSocketMessage(
                        type=MessageType.UNDO_REQUEST,
                        data={
                            "from": requester_player_number,
                            "is_requester": False,
                        },
                    )
                    await ws.send_text(json.dumps(confirm_response.to_json()))
            except Exception:
                # 연결이 끊어진 경우 무시
                pass

    async def _handle_undo_response(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """무르기 응답 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        if message["accepted"] and len(room.move_history) > 0:
            # 무르기 승인 - 모든 플레이어에게 알림
            game_state = OmokGameState(
                board=room.game_state["board"],
                current_player=room.game_state["current_player"],
            )

            if OmokGame.undo_last_move(game_state, room.move_history):
                room.game_state = {
                    "board": game_state.board,
                    "current_player": game_state.current_player,
                }

                response = WebSocketMessage(
                    type=MessageType.UNDO_ACCEPTED,
                    data={
                        "game_state": {
                            "board": room.game_state["board"],
                            "currentPlayer": room.game_state["current_player"],
                        }
                    },
                )
                await self._broadcast_to_room(room_id, response.to_json())
            else:
                # 무르기 실패 - 요청자에게만 알림
                requester_ws = room.undo_requests.get("requester_websocket")
                if requester_ws:
                    response = WebSocketMessage(
                        type=MessageType.UNDO_REJECTED, data={}
                    )
                    try:
                        await requester_ws.send_text(
                            json.dumps(response.to_json())
                        )
                    except Exception:
                        pass
        else:
            # 무르기 거부 - 요청자에게만 알림
            requester_ws = room.undo_requests.get("requester_websocket")
            if requester_ws:
                response = WebSocketMessage(
                    type=MessageType.UNDO_REJECTED, data={}
                )
                try:
                    await requester_ws.send_text(
                        json.dumps(response.to_json())
                    )
                except Exception:
                    # 연결이 끊어진 경우 무시
                    pass

        # 무르기 요청 정보 초기화
        room.undo_requests.clear()

    async def _handle_chat_message(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """채팅 메시지 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        # 발신자 확인
        sender_nickname = message.get("nickname", "")
        sender = None
        for player in room.players:
            if player.nickname == sender_nickname:
                sender = player
                break

        if not sender:
            return

        # 채팅 메시지 생성
        chat_message = ChatMessage(
            nickname=sender.nickname,
            message=message.get("message", ""),
            timestamp=datetime.now().strftime("%H:%M:%S"),
            player_number=sender.player_number,
        )

        # 채팅 히스토리에 추가 (최근 50개만 유지)
        room.chat_history.append(chat_message)
        if len(room.chat_history) > 50:
            room.chat_history.pop(0)

        # 모든 플레이어에게 브로드캐스트
        response = WebSocketMessage(
            type=MessageType.CHAT_BROADCAST,
            data={
                "nickname": chat_message.nickname,
                "message": chat_message.message,
                "timestamp": chat_message.timestamp,
                "player_number": chat_message.player_number,
            },
        )

        await self._broadcast_to_room(room_id, response.to_json())

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
                    "currentPlayer": game_state["current_player"],
                },
                "last_move": last_move,
            },
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _send_error(self, websocket: WebSocket, error_message: str):
        """에러 메시지 전송."""
        response = WebSocketMessage(
            type=MessageType.ERROR, data={"message": error_message}
        )
        try:
            await websocket.send_text(json.dumps(response.to_json()))
        except Exception:
            pass

    async def _send_reconnect_success(
        self, websocket: WebSocket, room, player
    ):
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
                        "currentPlayer": room.game_state["current_player"],
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
        """상대방에게 연결 끊김 알림."""
        response = WebSocketMessage(
            type=MessageType.PLAYER_DISCONNECTED, data={"nickname": nickname}
        )
        await self._broadcast_to_room(room_id, response.to_json())

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
