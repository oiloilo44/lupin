import json
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket

from .models import ChatMessage, GameType, MessageType, OmokGameState, WebSocketMessage
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
        try:
            # 필수 필드 검증
            if not message.get("nickname"):
                raise ValueError("닉네임이 필요합니다")
            if not isinstance(message.get("nickname"), str):
                raise ValueError("닉네임은 문자열이어야 합니다")

            room = room_manager.get_room(room_id)
            if not room:
                await self._send_error(websocket, "방을 찾을 수 없습니다", "validation")
                return

            session_id = message.get("session_id")
            nickname = message["nickname"]

            # 닉네임 유효성 검증 추가
            nickname = nickname.strip()
            if not nickname or len(nickname) > 20:
                raise ValueError("닉네임은 1-20자 사이여야 합니다")
            if any(char in nickname for char in ["<", ">", "&", '"', "'"]):
                raise ValueError("닉네임에 특수문자(<, >, &, \", ')는 사용할 수 없습니다")

            # 세션이 있으면 해당 세션으로 플레이어 추가
            if session_id:
                # 세션 ID 유효성 검증
                if not self._validate_session_id(session_id):
                    raise ValueError("유효하지 않은 세션 ID입니다")
                player = room_manager.add_player_to_room(room_id, nickname, session_id)
            else:
                # 세션이 없는 경우에도 유일성이 보장된 session_id를 생성해서 플레이어 추가
                temp_session_id = session_manager.generate_unique_session_id()
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

                await self._broadcast_room_update(room_id, room)
            else:
                await self._send_error(websocket, "플레이어 추가에 실패했습니다", "game")

        except ValueError as e:
            await self._send_error(websocket, str(e), "validation")
            import logging

            logging.warning(f"입력 검증 실패 in room {room_id}: {e}")
        except Exception as e:
            await self._send_error(websocket, "서버 오류가 발생했습니다", "server")
            import logging

            logging.error(f"처리 중 오류 in room {room_id}: {e}", exc_info=True)

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
            await self._send_error(websocket, f"다른 게임 방({room.room_id})에 참여 중입니다.")
            return

        # 재접속 처리
        success = room_manager.handle_reconnection(room_id, session_id, websocket)
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
        try:
            # 필수 필드 검증
            if "move" not in message:
                raise ValueError("이동 정보가 필요합니다")

            move = message["move"]
            if not isinstance(move, dict) or "x" not in move or "y" not in move:
                raise ValueError("올바른 이동 좌표가 필요합니다")

            room = room_manager.get_room(room_id)
            if not room:
                await self._send_error(websocket, "방을 찾을 수 없습니다", "validation")
                return

            # 세션 ID로 플레이어 찾기
            session_id = room_manager.get_session_id_by_websocket(websocket)
            if not session_id:
                await self._send_error(websocket, "세션 정보를 찾을 수 없습니다", "validation")
                return

            # 게임별 매니저로 이동 처리
            if room.game_type == GameType.OMOK:
                await self._handle_omok_move(websocket, room_id, message, session_id)
            # 추후 다른 게임 타입 추가 가능

        except ValueError as e:
            await self._send_error(websocket, str(e), "validation")
            import logging

            logging.warning(f"입력 검증 실패 in room {room_id}: {e}")
        except Exception as e:
            await self._send_error(websocket, "서버 오류가 발생했습니다", "server")
            import logging

            logging.error(f"처리 중 오류 in room {room_id}: {e}", exc_info=True)

    async def _handle_omok_move(
        self,
        websocket: WebSocket,
        room_id: str,
        message: Dict[str, Any],
        session_id: str,
    ):
        """오목 이동 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        omok_manager = room_manager.get_game_manager(GameType.OMOK)
        player = omok_manager.find_player_by_session(room, session_id)
        if not player:
            await self._send_error(websocket, "플레이어 정보를 찾을 수 없습니다.")
            return

        # 클라이언트는 move: {x, y} 형식으로 보냄
        if "move" not in message:
            await self._send_error(websocket, "이동 정보가 없습니다.")
            return

        move = message["move"]
        x, y = move["x"], move["y"]

        # 게임 매니저를 통한 이동 검증 및 실행
        success, winning_line, error_msg = omok_manager.make_move(room, player, x, y)

        if not success:
            await self._send_error(websocket, error_msg)
            return

        # 승리 조건 확인
        if winning_line:
            # 게임 종료 처리
            await self._broadcast_game_end(
                room_id, room, {"x": x, "y": y}, winning_line
            )
        else:
            # 일반 이동 업데이트
            await self._broadcast_game_update(
                room_id, room.game_state, {"x": x, "y": y}
            )

    async def _broadcast_game_end(
        self,
        room_id: str,
        room: Any,
        last_move: Dict[str, Any],
        winning_line: List[int],
    ):
        """게임 종료 브로드캐스트."""
        response = WebSocketMessage(
            type=MessageType.GAME_END,
            data={
                "winner": room.winner,
                "game_state": {
                    "board": room.game_state["board"],
                    "current_player": room.game_state["current_player"],
                },
                "last_move": last_move,
                "winning_line": winning_line,
            },
        )
        await self._broadcast_to_room(room_id, response.to_json())

    async def _handle_omok_undo(self, room_id: str, room):
        """오목 무르기 처리."""
        from .games.omok import OmokGame  # 지역 import로 순환 참조 방지

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
                        "current_player": room.game_state["current_player"],
                    }
                },
            )
            await self._broadcast_to_room(room_id, response.to_json())
        else:
            # 무르기 실패 - 요청자에게만 알림
            requester_ws = room.undo_requests.get("requester_websocket")
            if requester_ws:
                response = WebSocketMessage(type=MessageType.UNDO_REJECTED, data={})
                try:
                    await requester_ws.send_text(json.dumps(response.to_json()))
                except Exception:
                    pass

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
                room,
                message.get("last_move", {}),
                message.get("winning_line", []),
            )

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
                        "current_player": room.game_state["current_player"],
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
                        await ws.send_text(json.dumps(rejection_response.to_json()))
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

        # 요청자의 세션 ID 확인
        requester_session_id = room_manager.get_session_id_by_websocket(websocket)
        if not requester_session_id:
            await self._send_error(websocket, "세션 정보를 찾을 수 없습니다.")
            return

        # 요청자 플레이어 정보 확인
        game_manager = room_manager.get_game_manager(room.game_type)
        requester_player = game_manager.find_player_by_session(
            room, requester_session_id
        )
        if not requester_player:
            await self._send_error(websocket, "플레이어 정보를 찾을 수 없습니다.")
            return

        # 무르기 요청 검증: 수가 있는지만 확인 (자신/상대방 수 모두 무르기 가능)
        # 케이스 1: 자신의 턴에 상대방 마지막 수 무르기 요청
        # 케이스 2: 상대방 턴에 자신의 마지막 수 무르기 요청

        connections = room_manager.get_room_connections(room_id)

        # 무르기 요청자 정보를 방에 저장 (응답 처리 시 사용)
        room.undo_requests["requester"] = requester_player_number
        room.undo_requests["requester_websocket"] = websocket
        room.undo_requests["requester_session_id"] = requester_session_id

        # 각 플레이어에게 다른 메시지 전송
        for ws in connections:
            try:
                # 각 웹소켓의 세션 ID 확인
                ws_session_id = room_manager.get_session_id_by_websocket(ws)

                if ws_session_id == requester_session_id:  # 요청자
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
            except Exception as e:
                # 연결이 끊어진 경우 로깅 후 무시
                import logging

                logging.warning(f"Failed to send undo request to websocket: {e}")
                pass

    async def _handle_undo_response(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """무르기 응답 처리."""
        room = room_manager.get_room(room_id)
        if not room:
            return

        # 응답자의 세션 ID 확인
        responder_session_id = room_manager.get_session_id_by_websocket(websocket)
        if not responder_session_id:
            await self._send_error(websocket, "세션 정보를 찾을 수 없습니다.")
            return

        # 요청자가 자신의 무르기 요청에 응답하는 것을 방지
        requester_session_id = room.undo_requests.get("requester_session_id")
        if responder_session_id == requester_session_id:
            await self._send_error(websocket, "자신의 무르기 요청에는 응답할 수 없습니다.")
            return

        if message["accepted"] and len(room.move_history) > 0:
            # 게임별 무르기 처리
            if room.game_type == GameType.OMOK:
                await self._handle_omok_undo(room_id, room)
            # 추후 다른 게임 타입 추가 가능
        else:
            # 무르기 거부 - 요청자에게만 알림
            requester_ws = room.undo_requests.get("requester_websocket")
            if requester_ws:
                response = WebSocketMessage(type=MessageType.UNDO_REJECTED, data={})
                try:
                    await requester_ws.send_text(json.dumps(response.to_json()))
                except Exception as e:
                    # 연결이 끊어진 경우 로깅 후 무시
                    import logging

                    logging.warning(f"Failed to send undo rejection to requester: {e}")
                    pass

        # 무르기 요청 정보 초기화
        room.undo_requests.clear()

    async def _handle_chat_message(
        self, websocket: WebSocket, room_id: str, message: Dict[str, Any]
    ):
        """채팅 메시지 처리."""
        try:
            # 필수 필드 검증
            if not message.get("message"):
                raise ValueError("메시지 내용이 필요합니다")
            if not isinstance(message.get("message"), str):
                raise ValueError("메시지는 문자열이어야 합니다")

            room = room_manager.get_room(room_id)
            if not room:
                await self._send_error(websocket, "방을 찾을 수 없습니다", "validation")
                return

            # 발신자 확인 (세션 ID 기반)
            session_id = message.get("session_id", "")
            if not session_id:
                await self._send_error(websocket, "세션 정보가 필요합니다", "validation")
                return

            sender = None
            for player in room.players:
                if player.session_id == session_id:
                    sender = player
                    break

            if not sender:
                await self._send_error(websocket, "플레이어 정보를 찾을 수 없습니다", "validation")
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

        except ValueError as e:
            await self._send_error(websocket, str(e), "validation")
            import logging

            logging.warning(f"입력 검증 실패 in room {room_id}: {e}")
        except Exception as e:
            await self._send_error(websocket, "서버 오류가 발생했습니다", "server")
            import logging

            logging.error(f"처리 중 오류 in room {room_id}: {e}", exc_info=True)

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
                    "timestamp": datetime.now().isoformat(),
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

    def _validate_session_id(self, session_id: str) -> bool:
        """세션 ID 유효성 검증."""
        if not session_id or not isinstance(session_id, str):
            return False
        # 세션 ID는 UUID 형식이어야 함
        if len(session_id) != 36:
            return False
        # UUID 패턴 검증 (간단한 체크)
        parts = session_id.split("-")
        if len(parts) != 5:
            return False
        # 각 부분의 길이 체크
        if (
            len(parts[0]) != 8
            or len(parts[1]) != 4
            or len(parts[2]) != 4
            or len(parts[3]) != 4
            or len(parts[4]) != 12
        ):
            return False
        # 16진수 문자만 포함하는지 체크
        try:
            for part in parts:
                int(part, 16)
        except ValueError:
            return False
        return True


# 전역 핸들러 인스턴스
websocket_handler = WebSocketHandler()
