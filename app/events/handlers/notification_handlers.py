"""알림 이벤트 핸들러 - WebSocket 메시지 전송"""

import json
import logging
from typing import Any, Callable, Set

from fastapi import WebSocket

from ...models import MessageType, WebSocketMessage
from ..game_events import (
    GameEndedEvent,
    GameEvent,
    GameStartedEvent,
    MoveCompletedEvent,
    PlayerDisconnectedEvent,
    PlayerJoinedEvent,
    PlayerReconnectedEvent,
    RestartAcceptedEvent,
    RestartRequestedEvent,
    UndoAcceptedEvent,
    UndoRequestedEvent,
)

logger = logging.getLogger(__name__)


class NotificationEventHandler:
    """알림 이벤트 핸들러
    
    게임 이벤트를 WebSocket을 통해 클라이언트들에게 알림으로 전송합니다.
    """
    
    def __init__(self, get_connections_func: Callable[[str], Set[WebSocket]]) -> None:
        """핸들러 초기화
        
        Args:
            get_connections_func: 방 ID로 WebSocket 연결들을 가져오는 함수
        """
        self.get_connections = get_connections_func
    
    async def handle_player_joined(self, event: PlayerJoinedEvent) -> None:
        """플레이어 입장 알림"""
        if event.is_rejoining:
            message = WebSocketMessage(
                type=MessageType.PLAYER_RECONNECTED,
                data={
                    "player": {
                        "nickname": event.player.nickname,
                        "player_number": event.player.player_number,
                        "session_id": event.player.session_id,
                    },
                    "room_state": self._get_room_state(event.room),
                }
            )
        else:
            message = WebSocketMessage(
                type=MessageType.ROOM_UPDATE,
                data={
                    "room_state": self._get_room_state(event.room),
                    "joined_player": {
                        "nickname": event.player.nickname,
                        "player_number": event.player.player_number,
                    }
                }
            )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_player_disconnected(self, event: PlayerDisconnectedEvent) -> None:
        """플레이어 연결 끊김 알림"""
        message = WebSocketMessage(
            type=MessageType.PLAYER_DISCONNECTED,
            data={
                "player": {
                    "nickname": event.player.nickname,
                    "player_number": event.player.player_number,
                    "session_id": event.session_id,
                },
                "room_state": self._get_room_state(event.room),
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_player_reconnected(self, event: PlayerReconnectedEvent) -> None:
        """플레이어 재접속 알림"""
        message = WebSocketMessage(
            type=MessageType.PLAYER_RECONNECTED,
            data={
                "player": {
                    "nickname": event.player.nickname,
                    "player_number": event.player.player_number,
                    "session_id": event.session_id,
                },
                "room_state": self._get_room_state(event.room),
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_game_started(self, event: GameStartedEvent) -> None:
        """게임 시작 알림"""
        message = WebSocketMessage(
            type=MessageType.GAME_UPDATE,
            data={
                "game_state": event.room.game_state,
                "room_state": self._get_room_state(event.room),
                "message": "게임이 시작되었습니다!",
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_game_ended(self, event: GameEndedEvent) -> None:
        """게임 종료 알림"""
        message = WebSocketMessage(
            type=MessageType.GAME_END,
            data={
                "winner": event.winner,
                "reason": event.reason,
                "game_state": event.final_game_state,
                "room_state": self._get_room_state(event.room),
                "duration": event.game_duration,
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_move_completed(self, event: MoveCompletedEvent) -> None:
        """수 완료 알림"""
        message = WebSocketMessage(
            type=MessageType.GAME_UPDATE,
            data={
                "move": event.move_data,
                "player": event.player.player_number,
                "game_state": event.game_state_after,
                "next_player": event.next_player,
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_restart_requested(self, event: RestartRequestedEvent) -> None:
        """재시작 요청 알림"""
        message = WebSocketMessage(
            type=MessageType.RESTART_REQUEST,
            data={
                "requesting_player": event.requesting_player.player_number,
                "requester_nickname": event.requesting_player.nickname,
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_restart_accepted(self, event: RestartAcceptedEvent) -> None:
        """재시작 승인 알림"""
        message = WebSocketMessage(
            type=MessageType.RESTART_ACCEPTED,
            data={
                "game_state": event.room.game_state,
                "room_state": self._get_room_state(event.room),
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_undo_requested(self, event: UndoRequestedEvent) -> None:
        """무르기 요청 알림"""
        message = WebSocketMessage(
            type=MessageType.UNDO_REQUEST,
            data={
                "requesting_player": event.requesting_player.player_number,
                "requester_nickname": event.requesting_player.nickname,
                "moves_to_undo": event.moves_to_undo,
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    async def handle_undo_accepted(self, event: UndoAcceptedEvent) -> None:
        """무르기 승인 알림"""
        message = WebSocketMessage(
            type=MessageType.UNDO_ACCEPTED,
            data={
                "moves_undone": event.moves_undone,
                "game_state": event.game_state_after,
            }
        )
        
        await self._broadcast_to_room(event.room_id, message)
    
    def _get_room_state(self, room: Any) -> dict[str, Any]:
        """방 상태 정보 생성"""
        return {
            "room_id": room.room_id,
            "status": room.status.value,
            "players": [
                {
                    "nickname": p.nickname,
                    "player_number": p.player_number,
                    "is_connected": p.is_connected,
                    "color": p.color,
                }
                for p in room.players
            ],
            "game_ended": room.game_ended,
            "winner": room.winner,
            "games_played": room.games_played,
        }
    
    async def _broadcast_to_room(self, room_id: str, message: WebSocketMessage) -> None:
        """방의 모든 연결에 메시지 브로드캐스트"""
        connections = self.get_connections(room_id)
        if not connections:
            logger.debug(f"No connections found for room {room_id}")
            return
        
        message_json = json.dumps(message.to_json())
        
        # 연결이 끊어진 WebSocket들을 추적
        disconnected_connections: Set[WebSocket] = set()
        
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send message to WebSocket: {e}")
                disconnected_connections.add(websocket)
        
        # 끊어진 연결들은 연결 목록에서 제거할 수 있도록 로그 남김
        if disconnected_connections:
            logger.info(
                f"Found {len(disconnected_connections)} disconnected WebSockets "
                f"in room {room_id}"
            )


def register_notification_handlers(event_bus: Any, get_connections_func: Callable[[str], Set[WebSocket]]) -> None:
    """알림 핸들러들을 이벤트 버스에 등록
    
    Args:
        event_bus: 이벤트 버스 인스턴스
        get_connections_func: 연결 조회 함수
    """
    handler = NotificationEventHandler(get_connections_func)
    
    # 비동기 핸들러들 등록 (중간 우선순위)
    event_bus.subscribe(PlayerJoinedEvent, handler.handle_player_joined, priority=50)
    event_bus.subscribe(PlayerDisconnectedEvent, handler.handle_player_disconnected, priority=50)
    event_bus.subscribe(PlayerReconnectedEvent, handler.handle_player_reconnected, priority=50)
    event_bus.subscribe(GameStartedEvent, handler.handle_game_started, priority=50)
    event_bus.subscribe(GameEndedEvent, handler.handle_game_ended, priority=50)
    event_bus.subscribe(MoveCompletedEvent, handler.handle_move_completed, priority=50)
    event_bus.subscribe(RestartRequestedEvent, handler.handle_restart_requested, priority=50)
    event_bus.subscribe(RestartAcceptedEvent, handler.handle_restart_accepted, priority=50)
    event_bus.subscribe(UndoRequestedEvent, handler.handle_undo_requested, priority=50)
    event_bus.subscribe(UndoAcceptedEvent, handler.handle_undo_accepted, priority=50)