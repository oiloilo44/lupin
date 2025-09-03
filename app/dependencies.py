"""FastAPI 의존성 주입 함수들"""

from typing import Generator

from .room_manager import room_manager
from .services.game_service import GameService
from .session_manager import session_manager
from .websocket_handler import websocket_handler


def get_room_manager():
    """RoomManager 의존성 주입 함수"""
    return room_manager


def get_session_manager():
    """SessionManager 의존성 주입 함수"""
    return session_manager


def get_websocket_handler():
    """WebSocketHandler 의존성 주입 함수"""
    return websocket_handler


def get_game_service() -> GameService:
    """GameService 의존성 주입 함수"""
    # GameService는 생성자에서 직접 room_manager를 가져온다
    return GameService()


# 테스트용 의존성 오버라이드를 위한 제너레이터 함수들
def get_room_manager_override() -> Generator:
    """테스트에서 RoomManager를 오버라이드하기 위한 제너레이터"""
    yield room_manager


def get_session_manager_override() -> Generator:
    """테스트에서 SessionManager를 오버라이드하기 위한 제너레이터"""
    yield session_manager


def get_websocket_handler_override() -> Generator:
    """테스트에서 WebSocketHandler를 오버라이드하기 위한 제너레이터"""
    yield websocket_handler
