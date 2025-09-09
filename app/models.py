from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class GameType(str, Enum):
    OMOK = "omok"
    JANGGI = "janggi"
    SLITHER = "slither"


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    ENDED = "ended"


@dataclass
class Player:
    nickname: str
    player_number: int
    session_id: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_connected: bool = True
    color: Optional[int] = None  # 1: 흑돌, 2: 백돌


@dataclass
class GameMove:
    x: int
    y: int
    player: int


@dataclass
class OmokGameState:
    board: List[List[int]]
    current_player: int


@dataclass
class MoveHistoryEntry:
    move: GameMove
    board_state: List[List[int]]
    player: int


@dataclass
class ChatMessage:
    nickname: str
    message: str
    timestamp: str
    player_number: int


@dataclass
class Room:
    room_id: str
    game_type: GameType
    players: List[Player]
    game_state: Dict
    status: GameStatus
    game_ended: bool = False
    winner: Optional[int] = None
    move_history: List[MoveHistoryEntry] = field(default_factory=list)
    undo_requests: Dict = field(default_factory=dict)
    games_played: int = 0  # 게임 횟수
    last_winner: Optional[int] = None  # 마지막 게임 승자
    chat_history: List[ChatMessage] = field(default_factory=list)  # 채팅 히스토리

    def __post_init__(self):
        if self.players is None:
            self.players = []
        if self.move_history is None:
            self.move_history = []
        if self.undo_requests is None:
            self.undo_requests = {}
        if self.chat_history is None:
            self.chat_history = []

    def is_full(self) -> bool:
        """방이 가득 찬지 확인"""
        return len(self.players) >= 2

    def find_player_by_session(self, session_id: str) -> Optional[Player]:
        """세션 ID로 플레이어 찾기"""
        for player in self.players:
            if player.session_id == session_id:
                return player
        return None


# WebSocket 메시지 타입들
class MessageType(str, Enum):
    # 게임 플로우
    JOIN = "join"
    MOVE = "move"
    GAME_END = "game_end"
    RESTART_REQUEST = "restart_request"
    RESTART_RESPONSE = "restart_response"
    UNDO_REQUEST = "undo_request"
    UNDO_RESPONSE = "undo_response"

    # 재접속 관련
    RECONNECT = "reconnect"
    RECONNECT_SUCCESS = "reconnect_success"
    PLAYER_RECONNECTED = "player_reconnected"
    PLAYER_DISCONNECTED = "player_disconnected"

    # 상태 업데이트
    ROOM_UPDATE = "room_update"
    GAME_UPDATE = "game_update"
    RESTART_ACCEPTED = "restart_accepted"
    RESTART_REJECTED = "restart_rejected"
    UNDO_ACCEPTED = "undo_accepted"
    UNDO_REJECTED = "undo_rejected"

    # 채팅
    CHAT_MESSAGE = "chat_message"
    CHAT_BROADCAST = "chat_broadcast"

    # 에러
    ERROR = "error"


@dataclass
class WebSocketMessage:
    type: MessageType
    data: Dict

    def to_json(self) -> Dict:
        return {"type": self.type.value, **self.data}
