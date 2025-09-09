"""게임별 커스텀 예외 클래스들"""

from typing import Any, Dict, Optional


class GameError(Exception):
    """기본 게임 에러 클래스"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """에러를 딕셔너리로 변환 (클라이언트 전송용)"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class InvalidMoveError(GameError):
    """잘못된 게임 수 에러"""

    def __init__(
        self,
        message: str = "잘못된 수입니다",
        x: Optional[int] = None,
        y: Optional[int] = None,
    ):
        details = {}
        if x is not None and y is not None:
            details.update({"x": x, "y": y})
        super().__init__(message, "INVALID_MOVE", details)


class RoomFullError(GameError):
    """방 만원 에러"""

    def __init__(self, room_id: str, max_players: int = 2):
        message = "방이 가득 찼습니다"
        details = {"room_id": room_id, "max_players": max_players}
        super().__init__(message, "ROOM_FULL", details)


class SessionExpiredError(GameError):
    """세션 만료 에러"""

    def __init__(self, session_id: Optional[str] = None):
        message = "세션이 만료되었습니다"
        details = {"session_id": session_id} if session_id else {}
        super().__init__(message, "SESSION_EXPIRED", details)


class PlayerNotFoundError(GameError):
    """플레이어를 찾을 수 없음 에러"""

    def __init__(
        self, session_id: Optional[str] = None, player_number: Optional[int] = None
    ):
        message = "플레이어를 찾을 수 없습니다"
        details = {}
        if session_id:
            details["session_id"] = session_id
        if player_number is not None:
            details["player_number"] = str(player_number)
        super().__init__(message, "PLAYER_NOT_FOUND", details)


class RoomNotFoundError(GameError):
    """방을 찾을 수 없음 에러"""

    def __init__(self, room_id: str):
        message = "방을 찾을 수 없습니다"
        details = {"room_id": room_id}
        super().__init__(message, "ROOM_NOT_FOUND", details)


class UnauthorizedPlayerError(GameError):
    """인증되지 않은 플레이어 에러"""

    def __init__(self, message: str = "인증되지 않은 사용자입니다"):
        super().__init__(message, "UNAUTHORIZED_PLAYER")


class GameAlreadyEndedError(GameError):
    """이미 종료된 게임 에러"""

    def __init__(self, winner: Optional[int] = None):
        message = "게임이 이미 종료되었습니다"
        details = {"winner": winner} if winner else {}
        super().__init__(message, "GAME_ALREADY_ENDED", details)


class InvalidTurnError(GameError):
    """잘못된 턴 에러"""

    def __init__(self, current_player: int, attempted_player: int):
        message = "당신의 턴이 아닙니다"
        details = {
            "current_player": current_player,
            "attempted_player": attempted_player,
        }
        super().__init__(message, "INVALID_TURN", details)


class InvalidCoordinateError(GameError):
    """잘못된 좌표 에러"""

    def __init__(self, x: int, y: int, board_size: int = 15):
        message = "유효하지 않은 좌표입니다"
        details = {
            "x": x,
            "y": y,
            "board_size": board_size,
            "valid_range": f"0-{board_size-1}",
        }
        super().__init__(message, "INVALID_COORDINATE", details)


class WebSocketConnectionError(GameError):
    """WebSocket 연결 에러"""

    def __init__(self, message: str = "WebSocket 연결 오류가 발생했습니다"):
        super().__init__(message, "WEBSOCKET_CONNECTION_ERROR")


class ValidationError(GameError):
    """입력 검증 에러"""

    def __init__(self, field: str, value: Any, expected: str):
        message = f"잘못된 입력입니다: {field}"
        details = {"field": field, "value": str(value), "expected": expected}
        super().__init__(message, "VALIDATION_ERROR", details)


class ServerError(GameError):
    """서버 내부 에러"""

    def __init__(
        self,
        message: str = "서버 오류가 발생했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "SERVER_ERROR", details or {})


class RateLimitError(GameError):
    """요청 속도 제한 에러"""

    def __init__(self, limit: int, window: str = "minute"):
        message = f"요청이 너무 많습니다. {window}당 {limit}회로 제한됩니다"
        details = {"limit": limit, "window": window}
        super().__init__(message, "RATE_LIMIT_EXCEEDED", details)


# 오목 게임 전용 예외들
class OmokInvalidMoveError(InvalidMoveError):
    """오목 전용 잘못된 수 에러"""

    def __init__(
        self, x: int, y: int, reason: str = "해당 위치에 돌을 놓을 수 없습니다"
    ):
        details = {"x": x, "y": y, "reason": reason, "game_type": "omok"}
        super().__init__(reason, x, y)
        self.details.update(details)


class OmokPositionOccupiedError(OmokInvalidMoveError):
    """오목 위치 이미 점유됨 에러"""

    def __init__(self, x: int, y: int, occupied_by: int):
        reason = "이미 돌이 놓여진 자리입니다"
        super().__init__(x, y, reason)
        self.details.update(
            {
                "occupied_by": occupied_by,
                "player_color": "흑돌" if occupied_by == 1 else "백돌",
            }
        )
