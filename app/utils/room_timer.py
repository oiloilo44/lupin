"""방 타이머 관리 유틸리티."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from ..config.constants import SERVER_CONSTANTS

logger = logging.getLogger(__name__)


class RoomTimer:
    """방 타이머 관리 클래스.

    단일 책임: 방 정리 타이머 관리 및 지연된 작업 스케줄링.
    """

    def __init__(self) -> None:
        """타이머 관리자 초기화."""
        self.timers: Dict[str, asyncio.Task[Any]] = {}

    def schedule_room_cleanup(
        self,
        room_id: str,
        cleanup_callback: Callable[[str], None],
        delay_minutes: Optional[int] = None,
    ) -> None:
        """방 정리 타이머 스케줄링.

        Args:
            room_id: 방 ID.
            cleanup_callback: 정리 작업 콜백 함수.
            delay_minutes: 지연 시간 (분). None이면 설정에서 기본값 사용.
        """
        # 기존 타이머가 있으면 취소
        self.cancel_timer(room_id)

        # 지연 시간 결정
        if delay_minutes is None:
            delay_minutes = (
                SERVER_CONSTANTS.room_config["default_cleanup_delay"] // 60
            )

        # 새 타이머 생성
        delay_seconds = delay_minutes * 60
        timer_task = asyncio.create_task(
            self._cleanup_after_delay(room_id, cleanup_callback, delay_seconds)
        )
        self.timers[room_id] = timer_task

        logger.info(
            f"Room cleanup scheduled for {room_id} in {delay_minutes} minutes"
        )

    async def _cleanup_after_delay(
        self,
        room_id: str,
        cleanup_callback: Callable[[str], None],
        delay_seconds: int,
    ) -> None:
        """지연 후 정리 작업 실행.

        Args:
            room_id: 방 ID.
            cleanup_callback: 정리 작업 콜백 함수.
            delay_seconds: 지연 시간 (초).
        """
        try:
            await asyncio.sleep(delay_seconds)

            # 타이머가 여전히 활성 상태인지 확인
            if room_id in self.timers:
                logger.info(f"Executing cleanup for room {room_id}")
                cleanup_callback(room_id)
                self.remove_timer(room_id)

        except asyncio.CancelledError:
            logger.info(f"Cleanup timer for room {room_id} was cancelled")
            self.remove_timer(room_id)
        except Exception as e:
            logger.error(f"Error during room cleanup for {room_id}: {e}")
            self.remove_timer(room_id)

    def cancel_timer(self, room_id: str) -> bool:
        """특정 방의 타이머 취소.

        Args:
            room_id: 방 ID.

        Returns:
            취소 성공 여부.
        """
        if room_id in self.timers:
            timer_task = self.timers[room_id]
            if not timer_task.done():
                timer_task.cancel()
            self.remove_timer(room_id)
            logger.info(f"Timer cancelled for room {room_id}")
            return True
        return False

    def remove_timer(self, room_id: str) -> None:
        """타이머 제거 (내부 사용).

        Args:
            room_id: 방 ID.
        """
        if room_id in self.timers:
            del self.timers[room_id]

    def has_timer(self, room_id: str) -> bool:
        """방에 활성 타이머가 있는지 확인.

        Args:
            room_id: 방 ID.

        Returns:
            타이머 존재 여부.
        """
        return room_id in self.timers and not self.timers[room_id].done()

    def get_active_timers(self) -> list[str]:
        """활성 타이머가 있는 방 ID 목록 반환.

        Returns:
            활성 타이머가 있는 방 ID 목록.
        """
        return [
            room_id for room_id, timer in self.timers.items() if not timer.done()
        ]

    def cancel_all_timers(self) -> int:
        """모든 타이머 취소.

        Returns:
            취소된 타이머 수.
        """
        cancelled_count = 0

        for room_id in list(self.timers.keys()):
            if self.cancel_timer(room_id):
                cancelled_count += 1

        logger.info(f"Cancelled {cancelled_count} timers")
        return cancelled_count

    def cleanup_completed_timers(self) -> int:
        """완료된 타이머들 정리.

        Returns:
            정리된 타이머 수.
        """
        completed_rooms = [
            room_id for room_id, timer in self.timers.items() if timer.done()
        ]

        for room_id in completed_rooms:
            self.remove_timer(room_id)

        return len(completed_rooms)

    def get_timer_status(self, room_id: str) -> Optional[str]:
        """타이머 상태 반환.

        Args:
            room_id: 방 ID.

        Returns:
            타이머 상태 ('active', 'completed', 'cancelled', None).
        """
        if room_id not in self.timers:
            return None

        timer = self.timers[room_id]
        if timer.cancelled():
            return "cancelled"
        elif timer.done():
            return "completed"
        else:
            return "active"
