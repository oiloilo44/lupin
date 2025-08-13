"""게임 이벤트 정의"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import GameType, Player, Room


@dataclass
class GameEvent(ABC):
    """게임 이벤트 기본 클래스
    
    모든 게임 이벤트는 이 클래스를 상속받아야 합니다.
    """
    room_id: str
    timestamp: datetime
    
    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now()


# =========================
# 플레이어 관련 이벤트들
# =========================

@dataclass
class PlayerJoinedEvent(GameEvent):
    """플레이어가 방에 입장했을 때 발생하는 이벤트"""
    player: Player
    room: Room
    is_rejoining: bool = False  # 재접속 여부


@dataclass 
class PlayerLeftEvent(GameEvent):
    """플레이어가 방에서 나갔을 때 발생하는 이벤트"""
    player: Player
    room: Room
    reason: str = "manual"  # manual, disconnect, kicked


@dataclass
class PlayerDisconnectedEvent(GameEvent):
    """플레이어 연결이 끊어졌을 때 발생하는 이벤트"""
    player: Player
    room: Room
    session_id: str


@dataclass
class PlayerReconnectedEvent(GameEvent):
    """플레이어가 재접속했을 때 발생하는 이벤트"""
    player: Player
    room: Room
    session_id: str
    was_disconnected_duration: float  # 초 단위


# =========================
# 게임 플로우 이벤트들
# =========================

@dataclass
class GameStartedEvent(GameEvent):
    """게임이 시작되었을 때 발생하는 이벤트"""
    room: Room
    players: List[Player]
    game_type: GameType


@dataclass
class GameEndedEvent(GameEvent):
    """게임이 종료되었을 때 발생하는 이벤트"""
    room: Room
    winner: Optional[int]
    final_game_state: Dict[str, Any]
    game_duration: float  # 초 단위
    reason: str = "normal"  # normal, forfeit, disconnect


@dataclass
class GameResetEvent(GameEvent):
    """게임이 재시작되었을 때 발생하는 이벤트"""
    room: Room
    previous_winner: Optional[int]
    games_played_count: int


# =========================
# 게임 액션 이벤트들
# =========================

@dataclass
class MoveCompletedEvent(GameEvent):
    """플레이어의 수가 완료되었을 때 발생하는 이벤트"""
    room: Room
    player: Player
    move_data: Dict[str, Any]  # 게임별 이동 데이터 (x, y 등)
    game_state_after: Dict[str, Any]
    next_player: Optional[int]


@dataclass
class MoveRequestedEvent(GameEvent):
    """플레이어가 수를 요청했을 때 발생하는 이벤트 (검증 전)"""
    room: Room
    player: Player
    move_data: Dict[str, Any]


@dataclass
class InvalidMoveAttemptedEvent(GameEvent):
    """유효하지 않은 수를 시도했을 때 발생하는 이벤트"""
    room: Room
    player: Player
    move_data: Dict[str, Any]
    error_reason: str


# =========================
# 게임 관리 이벤트들
# =========================

@dataclass
class RestartRequestedEvent(GameEvent):
    """재시작이 요청되었을 때 발생하는 이벤트"""
    room: Room
    requesting_player: Player
    current_game_state: Dict[str, Any]


@dataclass
class RestartAcceptedEvent(GameEvent):
    """재시작이 승인되었을 때 발생하는 이벤트"""
    room: Room
    accepting_player: Player


@dataclass
class RestartRejectedEvent(GameEvent):
    """재시작이 거부되었을 때 발생하는 이벤트"""
    room: Room
    rejecting_player: Player


@dataclass
class UndoRequestedEvent(GameEvent):
    """무르기가 요청되었을 때 발생하는 이벤트"""
    room: Room
    requesting_player: Player
    moves_to_undo: int = 1


@dataclass
class UndoAcceptedEvent(GameEvent):
    """무르기가 승인되었을 때 발생하는 이벤트"""
    room: Room
    accepting_player: Player
    moves_undone: int
    game_state_after: Dict[str, Any]


@dataclass
class UndoRejectedEvent(GameEvent):
    """무르기가 거부되었을 때 발생하는 이벤트"""
    room: Room
    rejecting_player: Player


# =========================
# 방 관리 이벤트들
# =========================

@dataclass
class RoomCreatedEvent(GameEvent):
    """방이 생성되었을 때 발생하는 이벤트"""
    room: Room
    game_type: GameType


@dataclass
class RoomDeletedEvent(GameEvent):
    """방이 삭제되었을 때 발생하는 이벤트"""
    room_id: str
    reason: str = "empty"  # empty, expired, manual
    final_room_state: Optional[Dict[str, Any]] = None


@dataclass
class RoomCleanupScheduledEvent(GameEvent):
    """방 정리가 예약되었을 때 발생하는 이벤트"""
    delay_minutes: int
    reason: str = "no_connections"


# =========================
# 채팅 이벤트들
# =========================

@dataclass
class ChatMessageEvent(GameEvent):
    """채팅 메시지가 전송되었을 때 발생하는 이벤트"""
    room: Room
    player: Player
    message: str
    message_id: Optional[str] = None


# =========================
# 시스템 이벤트들
# =========================

@dataclass
class ConnectionEstablishedEvent(GameEvent):
    """WebSocket 연결이 설정되었을 때 발생하는 이벤트"""
    session_id: Optional[str] = None


@dataclass
class ConnectionClosedEvent(GameEvent):
    """WebSocket 연결이 종료되었을 때 발생하는 이벤트"""
    session_id: Optional[str] = None
    reason: str = "unknown"


@dataclass
class ErrorEvent(GameEvent):
    """오류가 발생했을 때 발생하는 이벤트"""
    error_type: str
    error_message: str
    error_data: Optional[Dict[str, Any]] = None
    player: Optional[Player] = None