"""게임 로직 이벤트 핸들러."""

import logging
from typing import Any

from ...models import GameStatus
from ..game_events import (
    GameEndedEvent,
    GameResetEvent,
    GameStartedEvent,
    PlayerJoinedEvent,
    PlayerLeftEvent,
    RoomCleanupScheduledEvent,
)

logger = logging.getLogger(__name__)


class GameEventHandler:
    """게임 로직 이벤트 핸들러

    게임 상태 변경, 점수 집계, 통계 등 게임 로직 관련 처리를 담당합니다.
    """

    def __init__(self, room_timer: Any = None) -> None:
        """핸들러 초기화

        Args:
            room_timer: 방 타이머 관리자 (선택적)
        """
        self.room_timer = room_timer
        self.game_statistics = {
            "total_games": 0,
            "total_players": 0,
            "rooms_created": 0,
            "average_game_duration": 0.0,
        }

    def handle_player_joined(self, event: PlayerJoinedEvent) -> None:
        """플레이어 입장 처리."""
        # 방에 충분한 플레이어가 모이면 게임 시작 가능 상태로 변경
        if len(event.room.players) >= 2 and event.room.status == GameStatus.WAITING:
            logger.debug(
                f"Room {event.room_id} ready to start "
                f"(players: {len(event.room.players)})"
            )

        # 재접속이 아닌 경우 플레이어 통계 업데이트
        if not event.is_rejoining:
            self.game_statistics["total_players"] += 1
            logger.debug(
                f"Total players count: {self.game_statistics['total_players']}"
            )

        # 방 정리 타이머가 있다면 취소 (플레이어가 들어왔으므로)
        if self.room_timer and self.room_timer.has_timer(event.room_id):
            self.room_timer.cancel_timer(event.room_id)
            logger.debug(f"Cancelled cleanup timer for room {event.room_id}")

    def handle_player_left(self, event: PlayerLeftEvent) -> None:
        """플레이어 나감 처리."""
        # 게임 중이었다면 게임 중단 처리
        if event.room.status == GameStatus.PLAYING:
            logger.info(
                f"Player left during game in room {event.room_id}, " "pausing game"
            )
            # 게임 일시정지나 종료 로직은 여기서 처리 가능

        # 방이 비었다면 정리 스케줄링
        if len(event.room.players) == 0:
            self._schedule_room_cleanup(event.room_id, "no_players")

    def handle_game_started(self, event: GameStartedEvent) -> None:
        """게임 시작 처리."""
        # 게임 통계 업데이트
        self.game_statistics["total_games"] += 1

        # 방 상태를 플레이 중으로 변경
        event.room.status = GameStatus.PLAYING

        logger.info(
            f"Game started in room {event.room_id}. "
            f"Total games played: {self.game_statistics['total_games']}"
        )

    def handle_game_ended(self, event: GameEndedEvent) -> None:
        """게임 종료 처리."""
        # 평균 게임 시간 업데이트
        current_avg = self.game_statistics["average_game_duration"]
        total_games = self.game_statistics["total_games"]

        if total_games > 0:
            new_avg = (
                (current_avg * (total_games - 1)) + event.game_duration
            ) / total_games
            self.game_statistics["average_game_duration"] = new_avg

        # 방 상태를 대기로 변경
        event.room.status = GameStatus.WAITING

        # 마지막 승자 기록
        event.room.last_winner = event.winner

        logger.info(
            f"Game ended in room {event.room_id}. "
            f"Duration: {event.game_duration:.1f}s, "
            f"Average duration: "
            f"{self.game_statistics['average_game_duration']:.1f}s"
        )

    def handle_game_reset(self, event: GameResetEvent) -> None:
        """게임 재시작 처리."""
        # 방 상태를 대기로 변경
        event.room.status = GameStatus.WAITING

        logger.info(
            f"Game reset in room {event.room_id}. "
            f"Total games in this room: {event.games_played_count}"
        )

    def handle_room_cleanup_scheduled(self, event: RoomCleanupScheduledEvent) -> None:
        """방 정리 스케줄링 처리."""
        if self.room_timer:
            # 실제 정리 타이머 설정은 RoomManager에서 처리
            logger.info(
                f"Room cleanup scheduled for {event.room_id} "
                f"in {event.delay_minutes} minutes (reason: {event.reason})"
            )

    def _schedule_room_cleanup(self, room_id: str, reason: str) -> None:
        """방 정리 스케줄링 헬퍼 메서드."""
        # 이벤트 발행을 통해 정리 스케줄링 알림
        # 실제 구현에서는 이벤트 버스를 통해 RoomCleanupScheduledEvent 발행
        logger.debug(f"Scheduling cleanup for room {room_id} (reason: {reason})")

    def get_statistics(self) -> dict[str, Any]:
        """게임 통계 반환."""
        return self.game_statistics.copy()

    def reset_statistics(self) -> None:
        """통계 초기화."""
        self.game_statistics = {
            "total_games": 0,
            "total_players": 0,
            "rooms_created": 0,
            "average_game_duration": 0.0,
        }
        logger.info("Game statistics reset")


def register_game_handlers(event_bus: Any, room_timer: Any = None) -> GameEventHandler:
    """게임 핸들러들을 이벤트 버스에 등록

    Args:
        event_bus: 이벤트 버스 인스턴스
        room_timer: 방 타이머 관리자

    Returns:
        생성된 게임 핸들러 인스턴스
    """
    handler = GameEventHandler(room_timer)

    # 게임 로직 핸들러들 등록 (높은 우선순위)
    event_bus.subscribe(PlayerJoinedEvent, handler.handle_player_joined, priority=80)
    event_bus.subscribe(PlayerLeftEvent, handler.handle_player_left, priority=80)
    event_bus.subscribe(GameStartedEvent, handler.handle_game_started, priority=80)
    event_bus.subscribe(GameEndedEvent, handler.handle_game_ended, priority=80)
    event_bus.subscribe(GameResetEvent, handler.handle_game_reset, priority=80)
    event_bus.subscribe(
        RoomCleanupScheduledEvent, handler.handle_room_cleanup_scheduled, priority=80
    )

    return handler
