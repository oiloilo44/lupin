"""전역 에러 핸들러 및 로깅 시스템"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import WebSocket

from ..exceptions.game_exceptions import GameError
from ..models import MessageType, WebSocketMessage

# 로거 설정
logger = logging.getLogger(__name__)


class ErrorHandler:
    """전역 에러 처리 및 로깅 클래스."""

    @staticmethod
    def setup_logging() -> None:
        """로깅 시스템 설정."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("game_errors.log", encoding="utf-8"),
            ],
        )

    @staticmethod
    async def handle_websocket_error(
        websocket: WebSocket,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        WebSocket 에러 처리

        Args:
            websocket: WebSocket 연결
            error: 발생한 예외
            context: 추가 컨텍스트 정보

        Returns:
            bool: 메시지 전송 성공 여부
        """
        context = context or {}

        # 에러 로깅
        ErrorHandler._log_error(error, "WebSocket", context)

        # 클라이언트에 전송할 에러 메시지 생성
        if isinstance(error, GameError):
            error_data = error.to_dict()
        else:
            error_data = {
                "error_code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다",
                "details": {},
            }

        # WebSocket 메시지 전송
        return await ErrorHandler._send_websocket_error(websocket, error_data)

    @staticmethod
    async def handle_http_error(
        error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        HTTP 에러 처리

        Args:
            error: 발생한 예외
            context: 추가 컨텍스트 정보

        Returns:
            Dict: HTTP 응답용 에러 데이터
        """
        context = context or {}

        # 에러 로깅
        ErrorHandler._log_error(error, "HTTP", context)

        # HTTP 응답용 에러 데이터 생성
        if isinstance(error, GameError):
            return {
                "success": False,
                "error": error.to_dict(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": {
                    "error_code": "INTERNAL_ERROR",
                    "message": "서버 내부 오류가 발생했습니다",
                    "details": {},
                },
                "timestamp": datetime.now().isoformat(),
            }

    @staticmethod
    def _log_error(
        error: Exception, error_type: str, context: Dict[str, Any]
    ) -> None:
        """에러 로깅."""
        error_info = {
            "error_type": error_type,
            "exception_class": error.__class__.__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }

        if isinstance(error, GameError):
            error_info.update(
                {"error_code": error.error_code, "details": error.details}
            )
            logger.warning(
                f"Game Error: {json.dumps(error_info, ensure_ascii=False)}"
            )
        else:
            logger.error(
                f"Unexpected Error: "
                f"{json.dumps(error_info, ensure_ascii=False)}",
                exc_info=True,
            )

    @staticmethod
    async def _send_websocket_error(
        websocket: WebSocket, error_data: Dict[str, Any]
    ) -> bool:
        """WebSocket 에러 메시지 전송."""
        try:
            response = WebSocketMessage(
                type=MessageType.ERROR, data=error_data
            )
            await websocket.send_text(json.dumps(response.to_json()))
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket error message: {e}")
            return False

    @staticmethod
    def create_user_friendly_message(error: Exception) -> str:
        """사용자 친화적 에러 메시지 생성."""
        if isinstance(error, GameError):
            return error.message

        # 일반적인 예외에 대한 사용자 친화적 메시지 매핑
        error_messages = {
            "JSONDecodeError": "잘못된 메시지 형식입니다",
            "ValueError": "입력 값이 올바르지 않습니다",
            "KeyError": "필수 정보가 누락되었습니다",
            "ConnectionError": "연결에 문제가 발생했습니다",
            "TimeoutError": "요청 시간이 초과되었습니다",
        }

        error_class = error.__class__.__name__
        return error_messages.get(error_class, "알 수 없는 오류가 발생했습니다")


class GameErrorContext:
    """게임 에러 컨텍스트 헬퍼 클래스."""

    @staticmethod
    def websocket_context(
        room_id: str,
        session_id: Optional[str] = None,
        message_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """WebSocket 컨텍스트 생성."""
        context = {"room_id": room_id}
        if session_id:
            context["session_id"] = session_id
        if message_type:
            context["message_type"] = message_type
        return context

    @staticmethod
    def game_move_context(
        room_id: str, x: int, y: int, player_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """게임 이동 컨텍스트 생성."""
        context = {"room_id": room_id, "move": {"x": x, "y": y}}
        if player_number is not None:
            context["player_number"] = str(player_number)
        return context

    @staticmethod
    def player_context(
        room_id: str,
        player_number: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """플레이어 컨텍스트 생성."""
        context = {"room_id": room_id}
        if player_number is not None:
            context["player_number"] = str(player_number)
        if session_id:
            context["session_id"] = session_id
        return context


# 전역 에러 핸들러 인스턴스
error_handler = ErrorHandler()

# 로깅 시스템 초기화
ErrorHandler.setup_logging()
