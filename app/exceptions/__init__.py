"""예외 클래스 모듈"""

from .game_exceptions import (
    GameAlreadyEndedError,
    GameError,
    InvalidCoordinateError,
    InvalidMoveError,
    InvalidTurnError,
    OmokInvalidMoveError,
    OmokPositionOccupiedError,
    PlayerNotFoundError,
    RoomFullError,
    RoomNotFoundError,
    SessionExpiredError,
    UnauthorizedPlayerError,
    ValidationError,
    WebSocketConnectionError,
)

__all__ = [
    "GameError",
    "InvalidMoveError",
    "RoomFullError",
    "SessionExpiredError",
    "PlayerNotFoundError",
    "RoomNotFoundError",
    "UnauthorizedPlayerError",
    "GameAlreadyEndedError",
    "InvalidTurnError",
    "InvalidCoordinateError",
    "WebSocketConnectionError",
    "ValidationError",
    "OmokInvalidMoveError",
    "OmokPositionOccupiedError",
]
