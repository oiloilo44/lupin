"""게임 비즈니스 로직 서비스"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import WebSocket

from ..models import ChatMessage, GameType, OmokGameState, Room
from ..room_manager import room_manager
from ..session_manager import session_manager


class GameService:
    """게임 비즈니스 로직 오케스트레이션

    WebSocketHandler가 메시지 파싱만 하고, 실제 비즈니스 로직은 이 서비스가 담당
    """

    def __init__(self):
        self.room_manager = room_manager

    async def handle_join(
        self,
        websocket: WebSocket,
        room_id: str,
        nickname: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """플레이어 참여 처리"""
        try:
            # 닉네임 유효성 검증
            if not nickname:
                raise ValueError("닉네임이 필요합니다")
            if not isinstance(nickname, str):
                raise ValueError("닉네임은 문자열이어야 합니다")

            nickname = nickname.strip()
            if not nickname or len(nickname) > 20:
                raise ValueError("닉네임은 1-20자 사이여야 합니다")
            if any(char in nickname for char in ["<", ">", "&", '"', "'"]):
                raise ValueError(
                    "닉네임에 특수문자(<, >, &, \", ')는 사용할 수 없습니다"
                )

            # 방 존재 확인
            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            # 세션 ID 처리
            if session_id:
                if not self._validate_session_id(session_id):
                    raise ValueError("유효하지 않은 세션 ID입니다")
            else:
                session_id = session_manager.generate_unique_session_id()

            # 플레이어 추가
            player = self.room_manager.add_player_to_room(room_id, nickname, session_id)
            if not player:
                raise ValueError("플레이어 추가에 실패했습니다")

            # 연결 상태 업데이트
            self.room_manager.update_player_connection_status(
                room_id, str(player.player_number), True
            )

            # WebSocket 연결 추가
            self.room_manager.add_connection(room_id, websocket, session_id)

            return {"success": True, "player": player, "room": room}

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(f"Join 처리 중 오류 in room {room_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def handle_reconnect(
        self, websocket: WebSocket, room_id: str, session_id: str
    ) -> Dict[str, Any]:
        """재접속 처리"""
        try:
            if not session_id:
                raise ValueError("세션 정보가 없습니다")

            # 세션으로 플레이어 찾기
            result = self.room_manager.find_player_by_session(session_id)
            if not result:
                raise ValueError("재접속할 게임을 찾을 수 없습니다")

            player, room = result
            if not player or not room:
                raise ValueError("재접속할 게임을 찾을 수 없습니다")

            # 다른 방에 접속 시도하는 경우
            if room.room_id != room_id:
                raise ValueError(f"다른 게임 방({room.room_id})에 참여 중입니다")

            # 재접속 처리
            success = self.room_manager.handle_reconnection(
                room_id, session_id, websocket
            )
            if not success:
                raise ValueError("재접속에 실패했습니다")

            return {
                "success": True,
                "player": player,
                "room": room,
                "message": f"{player.nickname}님이 재접속했습니다",
            }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Reconnect 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def handle_move(
        self, websocket: WebSocket, room_id: str, move: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """게임 이동 처리"""
        try:
            # 이동 정보 검증
            if not isinstance(move, dict) or "x" not in move or "y" not in move:
                raise ValueError("올바른 이동 좌표가 필요합니다")

            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            # 게임별 이동 처리
            if room.game_type == GameType.OMOK:
                return await self._handle_omok_move(room_id, room, move, session_id)
            else:
                raise ValueError("지원하지 않는 게임 타입입니다")

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(f"Move 처리 중 오류 in room {room_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def _handle_omok_move(
        self, room_id: str, room: Room, move: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """오목 이동 처리"""
        omok_manager = self.room_manager.get_game_manager(GameType.OMOK)
        player = omok_manager.find_player_by_session(room, session_id)
        if not player:
            raise ValueError("플레이어 정보를 찾을 수 없습니다")

        x, y = move["x"], move["y"]

        # 게임 매니저를 통한 이동 검증 및 실행
        success, winning_line, error_msg = omok_manager.make_move(room, player, x, y)

        if not success:
            return {"success": False, "error": error_msg, "error_type": "game"}

        # 결과 반환
        result = {
            "success": True,
            "last_move": {"x": x, "y": y},
            "game_state": room.game_state,
        }

        if winning_line:
            result.update(
                {
                    "game_ended": True,
                    "winner": room.winner,
                    "winning_line": winning_line,
                }
            )

        return result

    async def handle_restart_request(
        self, websocket: WebSocket, room_id: str, from_player: int
    ) -> Dict[str, Any]:
        """재시작 요청 처리"""
        try:
            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            return {
                "success": True,
                "requester": from_player,
                "message": "재시작 요청이 전송되었습니다",
            }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Restart request 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def handle_restart_response(
        self, websocket: WebSocket, room_id: str, accepted: bool
    ) -> Dict[str, Any]:
        """재시작 응답 처리"""
        try:
            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            if accepted:
                # 재시작 승인
                self.room_manager.reset_omok_game(room_id)
                return {
                    "success": True,
                    "accepted": True,
                    "game_state": room.game_state,
                    "players": [
                        {
                            "nickname": p.nickname,
                            "player_number": p.player_number,
                            "color": p.color,
                        }
                        for p in room.players
                    ],
                    "games_played": room.games_played,
                }
            else:
                # 재시작 거부
                return {
                    "success": True,
                    "accepted": False,
                    "message": "재시작이 거부되었습니다",
                }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Restart response 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def handle_undo_request(
        self, websocket: WebSocket, room_id: str, from_player: int, session_id: str
    ) -> Dict[str, Any]:
        """무르기 요청 처리"""
        try:
            room = self.room_manager.get_room(room_id)
            if not room or len(room.move_history) == 0 or room.game_ended:
                raise ValueError("무르기를 할 수 없는 상태입니다")

            # 플레이어 검증
            game_manager = self.room_manager.get_game_manager(room.game_type)
            requester_player = game_manager.find_player_by_session(room, session_id)
            if not requester_player:
                raise ValueError("플레이어 정보를 찾을 수 없습니다")

            # 무르기 요청 정보 저장
            room.undo_requests["requester"] = from_player
            room.undo_requests["requester_websocket"] = websocket
            room.undo_requests["requester_session_id"] = session_id

            return {
                "success": True,
                "requester": from_player,
                "message": "무르기 요청이 전송되었습니다",
            }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Undo request 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def handle_undo_response(
        self, websocket: WebSocket, room_id: str, accepted: bool, session_id: str
    ) -> Dict[str, Any]:
        """무르기 응답 처리"""
        try:
            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            # 요청자가 자신의 무르기 요청에 응답하는 것을 방지
            requester_session_id = room.undo_requests.get("requester_session_id")
            if session_id == requester_session_id:
                raise ValueError("자신의 무르기 요청에는 응답할 수 없습니다")

            if accepted and len(room.move_history) > 0:
                # 게임별 무르기 처리
                if room.game_type == GameType.OMOK:
                    success = await self._handle_omok_undo(room_id, room)
                    if success:
                        room.undo_requests.clear()
                        return {
                            "success": True,
                            "accepted": True,
                            "game_state": room.game_state,
                            "message": "무르기가 승인되었습니다",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "무르기를 처리할 수 없습니다",
                            "error_type": "game",
                        }
                else:
                    return {
                        "success": False,
                        "error": "지원하지 않는 게임 타입입니다",
                        "error_type": "game",
                    }
            else:
                # 무르기 거부
                room.undo_requests.clear()
                return {
                    "success": True,
                    "accepted": False,
                    "message": "무르기가 거부되었습니다",
                }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Undo response 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    async def _handle_omok_undo(self, room_id: str, room: Room) -> bool:
        """오목 무르기 처리"""
        from ..games.omok import OmokGame

        game_state = OmokGameState(
            board=room.game_state["board"],
            current_player=room.game_state["current_player"],
        )

        if OmokGame.undo_last_move(game_state, room.move_history):
            room.game_state = {
                "board": game_state.board,
                "current_player": game_state.current_player,
            }
            return True
        return False

    async def handle_chat_message(
        self, websocket: WebSocket, room_id: str, message: str, session_id: str
    ) -> Dict[str, Any]:
        """채팅 메시지 처리"""
        try:
            # 메시지 검증
            if not message:
                raise ValueError("메시지 내용이 필요합니다")
            if not isinstance(message, str):
                raise ValueError("메시지는 문자열이어야 합니다")

            room = self.room_manager.get_room(room_id)
            if not room:
                raise ValueError("방을 찾을 수 없습니다")

            # 발신자 확인
            sender = None
            for player in room.players:
                if player.session_id == session_id:
                    sender = player
                    break

            if not sender:
                raise ValueError("플레이어 정보를 찾을 수 없습니다")

            # 채팅 메시지 생성
            chat_message = ChatMessage(
                nickname=sender.nickname,
                message=message,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                player_number=sender.player_number,
            )

            # 채팅 히스토리에 추가
            room.chat_history.append(chat_message)
            if len(room.chat_history) > 50:
                room.chat_history.pop(0)

            return {
                "success": True,
                "chat_message": {
                    "nickname": chat_message.nickname,
                    "message": chat_message.message,
                    "timestamp": chat_message.timestamp,
                    "player_number": chat_message.player_number,
                },
            }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            import logging

            logging.error(
                f"Chat message 처리 중 오류 in room {room_id}: {e}", exc_info=True
            )
            return {
                "success": False,
                "error": "서버 오류가 발생했습니다",
                "error_type": "server",
            }

    def _validate_session_id(self, session_id: str) -> bool:
        """세션 ID 유효성 검증"""
        if not session_id or not isinstance(session_id, str):
            return False
        # 세션 ID는 UUID 형식이어야 함
        if len(session_id) != 36:
            return False
        # UUID 패턴 검증
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


# 전역 서비스 인스턴스
game_service = GameService()
