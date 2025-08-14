"""로깅 이벤트 핸들러"""

import logging
import time
from typing import Any

from ...config.constants import SERVER_CONSTANTS
from ...monitoring.performance import get_performance_monitor
from ..game_events import (
    ChatMessageEvent,
    GameEndedEvent,
    GameEvent,
    GameStartedEvent,
    InvalidMoveAttemptedEvent,
    MoveCompletedEvent,
    PlayerDisconnectedEvent,
    PlayerJoinedEvent,
    PlayerReconnectedEvent,
    RoomCreatedEvent,
    RoomDeletedEvent,
)

logger = logging.getLogger(__name__)
performance_monitor = get_performance_monitor()


class LoggingEventHandler:
    """게임 이벤트 로깅 핸들러

    모든 게임 이벤트를 적절한 로그 레벨로 기록합니다.
    """

    def handle_player_joined(self, event: PlayerJoinedEvent) -> None:
        """플레이어 입장 로깅"""
        action = "rejoined" if event.is_rejoining else "joined"
        logger.info(
            f"Player {event.player.nickname} ({event.player.session_id}) "
            f"{action} room {event.room_id}"
        )

    def handle_player_disconnected(self, event: PlayerDisconnectedEvent) -> None:
        """플레이어 연결 끊김 로깅"""
        logger.warning(
            f"Player {event.player.nickname} disconnected from room {event.room_id}"
        )

    def handle_player_reconnected(self, event: PlayerReconnectedEvent) -> None:
        """플레이어 재접속 로깅"""
        logger.info(
            f"Player {event.player.nickname} reconnected to room {event.room_id} "
            f"after {event.was_disconnected_duration:.1f}s"
        )

    def handle_game_started(self, event: GameStartedEvent) -> None:
        """게임 시작 로깅"""
        player_names = [p.nickname for p in event.players]
        logger.info(
            f"Game started in room {event.room_id} "
            f"({event.game_type.value}) with players: {', '.join(player_names)}"
        )

    def handle_game_ended(self, event: GameEndedEvent) -> None:
        """게임 종료 로깅"""
        if event.winner:
            logger.info(
                f"Game ended in room {event.room_id}, winner: player {event.winner} "
                f"(duration: {event.game_duration:.1f}s, reason: {event.reason})"
            )
        else:
            logger.info(
                f"Game ended in room {event.room_id} with no winner "
                f"(duration: {event.game_duration:.1f}s, reason: {event.reason})"
            )

    def handle_move_completed(self, event: MoveCompletedEvent) -> None:
        """수 완료 로깅"""
        logger.debug(
            f"Move completed by {event.player.nickname} in room {event.room_id}: "
            f"{event.move_data}"
        )

    def handle_invalid_move_attempted(self, event: InvalidMoveAttemptedEvent) -> None:
        """유효하지 않은 수 시도 로깅"""
        logger.warning(
            f"Invalid move attempted by {event.player.nickname} in room "
            f"{event.room_id}: {event.move_data} - Reason: {event.error_reason}"
        )

    def handle_room_created(self, event: RoomCreatedEvent) -> None:
        """방 생성 로깅"""
        logger.info(f"Room created: {event.room_id} (type: {event.game_type.value})")

    def handle_room_deleted(self, event: RoomDeletedEvent) -> None:
        """방 삭제 로깅"""
        logger.info(f"Room deleted: {event.room_id} (reason: {event.reason})")

    def handle_chat_message(self, event: ChatMessageEvent) -> None:
        """채팅 메시지 로깅"""
        max_length = SERVER_CONSTANTS.logging_config["max_log_length"]
        truncated_msg = event.message[:max_length]
        suffix = "..." if len(event.message) > max_length else ""
        logger.debug(
            f"Chat message in room {event.room_id} from "
            f"{event.player.nickname}: {truncated_msg}{suffix}"
        )

    def handle_global_event(self, event: GameEvent) -> None:
        """모든 이벤트에 대한 글로벌 로깅 및 성능 메트릭"""
        event_name = type(event).__name__
        logger.debug(
            f"Event: {event_name} in room {event.room_id} at {event.timestamp}"
        )

        # 이벤트 처리 시간 기록 (이벤트 생성부터 로깅까지의 시간)
        if hasattr(event, "timestamp"):
            processing_time = (time.time() - event.timestamp.timestamp()) * 1000  # ms
            performance_monitor.record_event_processing_time(
                event_type=event_name,
                duration_ms=processing_time,
                success=True,
                tags={"room_id": event.room_id},
            )


def register_logging_handlers(event_bus: Any) -> None:
    """로깅 핸들러들을 이벤트 버스에 등록

    Args:
        event_bus: 이벤트 버스 인스턴스
    """
    handler = LoggingEventHandler()

    # 특정 이벤트별 핸들러 등록
    event_bus.subscribe(PlayerJoinedEvent, handler.handle_player_joined, priority=100)
    event_bus.subscribe(
        PlayerDisconnectedEvent, handler.handle_player_disconnected, priority=100
    )
    event_bus.subscribe(
        PlayerReconnectedEvent, handler.handle_player_reconnected, priority=100
    )
    event_bus.subscribe(GameStartedEvent, handler.handle_game_started, priority=100)
    event_bus.subscribe(GameEndedEvent, handler.handle_game_ended, priority=100)
    event_bus.subscribe(MoveCompletedEvent, handler.handle_move_completed, priority=100)
    event_bus.subscribe(
        InvalidMoveAttemptedEvent, handler.handle_invalid_move_attempted, priority=100
    )
    event_bus.subscribe(RoomCreatedEvent, handler.handle_room_created, priority=100)
    event_bus.subscribe(RoomDeletedEvent, handler.handle_room_deleted, priority=100)
    event_bus.subscribe(ChatMessageEvent, handler.handle_chat_message, priority=100)

    # 모든 이벤트에 대한 글로벌 핸들러 등록 (낮은 우선순위)
    event_bus.subscribe_global(handler.handle_global_event, priority=-100)
