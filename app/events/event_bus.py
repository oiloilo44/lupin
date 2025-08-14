"""이벤트 버스 시스템 구현."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from .game_events import GameEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[GameEvent], Union[None, asyncio.Task[None]]]


class EventBus:
    """이벤트 버스 - 게임 이벤트의 발행과 구독을 관리

    특징:
    - 타입 안전한 이벤트 시스템
    - 비동기 이벤트 처리 지원
    - 핸들러 우선순위 지원
    - 에러 격리 (한 핸들러 실패가 다른 핸들러에 영향 없음)
    """

    def __init__(self) -> None:
        # 이벤트 타입별 핸들러 목록 (우선순위 순서)
        self._handlers: Dict[
            Type[GameEvent], List[tuple[int, EventHandler]]
        ] = {}
        # 모든 이벤트에 대한 글로벌 핸들러들
        self._global_handlers: List[tuple[int, EventHandler]] = []
        # 이벤트 타입별 핸들러 수 (디버깅용)
        self._handler_count: Dict[Type[GameEvent], int] = {}

    def subscribe(
        self,
        event_type: Type[GameEvent],
        handler: EventHandler,
        priority: int = 0,
    ) -> None:
        """이벤트 타입에 핸들러 등록

        Args:
            event_type: 구독할 이벤트 타입
            handler: 이벤트 핸들러 함수
            priority: 우선순위 (높을수록 먼저 실행, 기본값 0)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            self._handler_count[event_type] = 0

        self._handlers[event_type].append((priority, handler))
        # 우선순위 순으로 정렬 (높은 우선순위가 앞에)
        self._handlers[event_type].sort(key=lambda x: x[0], reverse=True)
        self._handler_count[event_type] += 1

        logger.debug(
            f"Registered handler for {event_type.__name__} "
            f"(priority: {priority}, total: {self._handler_count[event_type]})"
        )

    def subscribe_global(
        self, handler: EventHandler, priority: int = 0
    ) -> None:
        """모든 이벤트에 대한 글로벌 핸들러 등록

        Args:
            handler: 이벤트 핸들러 함수
            priority: 우선순위 (높을수록 먼저 실행, 기본값 0)
        """
        self._global_handlers.append((priority, handler))
        self._global_handlers.sort(key=lambda x: x[0], reverse=True)

        logger.debug(f"Registered global handler (priority: {priority})")

    def unsubscribe(
        self, event_type: Type[GameEvent], handler: EventHandler
    ) -> bool:
        """이벤트 핸들러 등록 해제

        Args:
            event_type: 이벤트 타입
            handler: 제거할 핸들러

        Returns:
            제거 성공 여부
        """
        if event_type not in self._handlers:
            return False

        # 핸들러 찾아서 제거
        original_length = len(self._handlers[event_type])
        self._handlers[event_type] = [
            (priority, h)
            for priority, h in self._handlers[event_type]
            if h != handler
        ]

        removed = original_length > len(self._handlers[event_type])
        if removed:
            self._handler_count[event_type] -= 1
            logger.debug(f"Unregistered handler for {event_type.__name__}")

        return removed

    async def publish(self, event: GameEvent) -> None:
        """이벤트 발행

        Args:
            event: 발행할 이벤트 객체
        """
        event_type = type(event)
        logger.debug(f"Publishing event: {event_type.__name__}")

        # 실행할 핸들러들 수집
        handlers_to_run = []

        # 글로벌 핸들러들 추가
        handlers_to_run.extend(self._global_handlers)

        # 특정 이벤트 타입 핸들러들 추가
        if event_type in self._handlers:
            handlers_to_run.extend(self._handlers[event_type])

        # 우선순위 순으로 정렬
        handlers_to_run.sort(key=lambda x: x[0], reverse=True)

        if not handlers_to_run:
            logger.debug(f"No handlers found for {event_type.__name__}")
            return

        # 핸들러들 실행
        tasks: List[asyncio.Task[Any]] = []
        for priority, handler in handlers_to_run:
            try:
                result = handler(event)
                # 비동기 핸들러인 경우 태스크로 실행
                if asyncio.iscoroutine(result):
                    task = asyncio.create_task(
                        result
                    )  # type: ignore[unreachable]
                    tasks.append(task)
            except Exception as e:
                logger.error(
                    f"Error in event handler for {event_type.__name__}: {e}",
                    exc_info=True,
                )

        # 모든 비동기 핸들러 완료 대기
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error waiting for event handlers: {e}")

    def publish_sync(self, event: GameEvent) -> None:
        """동기적 이벤트 발행 (비동기 컨텍스트가 아닌 경우 사용)

        Args:
            event: 발행할 이벤트 객체
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 실행 중인 루프가 있으면 태스크로 스케줄링
                asyncio.create_task(self.publish(event))
            else:
                # 새 루프에서 실행
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # 이벤트 루프가 없는 경우 새로 생성
            asyncio.run(self.publish(event))

    def get_handler_count(self, event_type: Type[GameEvent]) -> int:
        """특정 이벤트 타입의 핸들러 수 반환

        Args:
            event_type: 이벤트 타입

        Returns:
            핸들러 수
        """
        return self._handler_count.get(event_type, 0)

    def get_total_handler_count(self) -> int:
        """전체 핸들러 수 반환

        Returns:
            전체 핸들러 수
        """
        return sum(self._handler_count.values()) + len(self._global_handlers)

    def clear_handlers(
        self, event_type: Optional[Type[GameEvent]] = None
    ) -> None:
        """핸들러들 제거

        Args:
            event_type: 특정 이벤트 타입 (None이면 모든 핸들러 제거)
        """
        if event_type is None:
            # 모든 핸들러 제거
            self._handlers.clear()
            self._global_handlers.clear()
            self._handler_count.clear()
            logger.info("Cleared all event handlers")
        else:
            # 특정 이벤트 타입의 핸들러만 제거
            if event_type in self._handlers:
                del self._handlers[event_type]
                self._handler_count[event_type] = 0
                logger.info(f"Cleared handlers for {event_type.__name__}")

    def get_registered_events(self) -> Set[Type[GameEvent]]:
        """등록된 이벤트 타입들 반환

        Returns:
            등록된 이벤트 타입들의 집합
        """
        return set(self._handlers.keys())


# 전역 이벤트 버스 인스턴스
event_bus = EventBus()
