"""설정 기반 상수 정의."""
from typing import Any, Dict

from .config_loader import get_config, get_game_config


class GameConstants:
    """게임 관련 상수들."""

    def __init__(self, game_name: str):
        self._game_name = game_name
        self._config = get_game_config(game_name)

    @property
    def board_size(self) -> int:
        """보드 크기."""
        value = self._config.get("board_size", 15)
        return int(value) if value is not None else 15

    @property
    def win_condition(self) -> int:
        """승리 조건 (연속 돌 개수)."""
        value = self._config.get("win_condition", 5)
        return int(value) if value is not None else 5

    @property
    def max_players(self) -> int:
        """최대 플레이어 수."""
        value = self._config.get("max_players", 2)
        return int(value) if value is not None else 2

    @property
    def colors(self) -> Dict[str, int]:
        """플레이어 색상 매핑."""
        colors = self._config.get("colors", {"black": 1, "white": 2})
        if isinstance(colors, dict):
            return {k: int(v) for k, v in colors.items()}
        return {"black": 1, "white": 2}

    @property
    def move_timeout(self) -> int:
        """한 수당 제한 시간 (초)."""
        timeouts = self._config.get("timeouts", {})
        if isinstance(timeouts, dict):
            value = timeouts.get("move_timeout", 30)
            return int(value) if value is not None else 30
        return 30

    @property
    def reconnect_timeout(self) -> int:
        """재접속 허용 시간 (초)."""
        timeouts = self._config.get("timeouts", {})
        if isinstance(timeouts, dict):
            value = timeouts.get("reconnect_timeout", 1800)
            return int(value) if value is not None else 1800
        return 1800

    @property
    def cleanup_delay(self) -> int:
        """빈 방 정리 지연 시간 (초)."""
        timeouts = self._config.get("timeouts", {})
        if isinstance(timeouts, dict):
            value = timeouts.get("cleanup_delay", 1800)
            return int(value) if value is not None else 1800
        return 1800

    @property
    def max_chat_history(self) -> int:
        """채팅 히스토리 최대 개수."""
        chat = self._config.get("chat", {})
        if isinstance(chat, dict):
            value = chat.get("max_history", 50)
            return int(value) if value is not None else 50
        return 50

    @property
    def max_message_length(self) -> int:
        """메시지 최대 길이."""
        chat = self._config.get("chat", {})
        if isinstance(chat, dict):
            value = chat.get("max_message_length", 200)
            return int(value) if value is not None else 200
        return 200

    @property
    def features_enabled(self) -> Dict[str, bool]:
        """활성화된 기능들."""
        features = self._config.get("features", {})
        if isinstance(features, dict):
            return {
                "undo_enabled": bool(features.get("undo_enabled", True)),
                "restart_enabled": bool(features.get("restart_enabled", True)),
                "spectator_enabled": bool(features.get("spectator_enabled", True)),
                "chat_enabled": bool(features.get("chat_enabled", True)),
            }
        return {
            "undo_enabled": True,
            "restart_enabled": True,
            "spectator_enabled": True,
            "chat_enabled": True,
        }

    @property
    def metadata(self) -> Dict[str, Any]:
        """게임 메타데이터."""
        metadata = self._config.get("metadata", {})
        if isinstance(metadata, dict):
            return {
                "display_name": str(
                    metadata.get("display_name", self._game_name.title())
                ),
                "description": str(
                    metadata.get("description", f"{self._game_name} 게임")
                ),
                "category": str(metadata.get("category", "게임")),
                "difficulty": str(metadata.get("difficulty", "보통")),
                "estimated_duration": str(metadata.get("estimated_duration", "15-30분")),
                "min_age": int(metadata.get("min_age", 8)),
            }
        return {
            "display_name": self._game_name.title(),
            "description": f"{self._game_name} 게임",
            "category": "게임",
            "difficulty": "보통",
            "estimated_duration": "15-30분",
            "min_age": 8,
        }


class ServerConstants:
    """서버 관련 상수들."""

    def __init__(self) -> None:
        self._config = get_config("default")

    @property
    def server_config(self) -> Dict[str, Any]:
        """서버 설정."""
        server = self._config.get("server", {})
        if isinstance(server, dict):
            return {
                "host": str(server.get("host", "0.0.0.0")),
                "port": int(server.get("port", 8002)),
                "debug": bool(server.get("debug", False)),
            }
        return {"host": "0.0.0.0", "port": 8002, "debug": False}

    @property
    def websocket_config(self) -> Dict[str, Any]:
        """WebSocket 설정."""
        websocket = self._config.get("websocket", {})
        if isinstance(websocket, dict):
            return {
                "ping_interval": int(websocket.get("ping_interval", 20)),
                "ping_timeout": int(websocket.get("ping_timeout", 10)),
                "max_connections": int(websocket.get("max_connections", 1000)),
            }
        return {"ping_interval": 20, "ping_timeout": 10, "max_connections": 1000}

    @property
    def room_config(self) -> Dict[str, Any]:
        """방 관리 설정."""
        room = self._config.get("room", {})
        if isinstance(room, dict):
            return {
                "max_rooms": int(room.get("max_rooms", 500)),
                "default_cleanup_delay": int(room.get("default_cleanup_delay", 1800)),
                "inactive_threshold": int(room.get("inactive_threshold", 3600)),
            }
        return {
            "max_rooms": 500,
            "default_cleanup_delay": 1800,
            "inactive_threshold": 3600,
        }

    @property
    def events_config(self) -> Dict[str, Any]:
        """이벤트 시스템 설정."""
        events = self._config.get("events", {})
        if isinstance(events, dict):
            return {
                "max_queue_size": int(events.get("max_queue_size", 10000)),
                "default_priority": int(events.get("default_priority", 100)),
                "timeout": int(events.get("timeout", 5)),
            }
        return {"max_queue_size": 10000, "default_priority": 100, "timeout": 5}

    @property
    def logging_config(self) -> Dict[str, Any]:
        """로깅 설정."""
        logging_cfg = self._config.get("logging", {})
        if isinstance(logging_cfg, dict):
            return {
                "level": str(logging_cfg.get("level", "INFO")),
                "format": str(
                    logging_cfg.get(
                        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    )
                ),
                "max_log_length": int(logging_cfg.get("max_log_length", 100)),
            }
        return {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "max_log_length": 100,
        }

    @property
    def security_config(self) -> Dict[str, Any]:
        """보안 설정."""
        security = self._config.get("security", {})
        if isinstance(security, dict):
            rate_limit = security.get("rate_limit", {})
            if isinstance(rate_limit, dict):
                rate_limit_config = {
                    "requests_per_minute": int(
                        rate_limit.get("requests_per_minute", 60)
                    ),
                    "burst_size": int(rate_limit.get("burst_size", 10)),
                }
            else:
                rate_limit_config = {"requests_per_minute": 60, "burst_size": 10}

            return {
                "session_timeout": int(security.get("session_timeout", 86400)),
                "max_message_size": int(security.get("max_message_size", 1024)),
                "rate_limit": rate_limit_config,
            }
        return {
            "session_timeout": 86400,
            "max_message_size": 1024,
            "rate_limit": {"requests_per_minute": 60, "burst_size": 10},
        }


# 게임별 상수 인스턴스들
OMOK_CONSTANTS = GameConstants("omok")
SERVER_CONSTANTS = ServerConstants()
