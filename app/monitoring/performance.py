"""성능 측정 및 모니터링."""

import functools
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

from .metrics import GaugeMetric, MetricsCollector, get_metrics_collector

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class PerformanceMonitor:
    """성능 모니터링 클래스."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics = metrics_collector or get_metrics_collector()

    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """컨텍스트 매니저로 실행 시간 측정."""
        start_time = time.time()
        tags = tags or {}

        try:
            yield
        finally:
            duration = time.time() - start_time
            self.metrics.record_histogram(
                f"{name}.duration", duration * 1000, tags
            )  # ms 단위
            logger.debug(f"Timer '{name}' completed in {duration*1000:.2f}ms")

    @asynccontextmanager
    async def async_timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """비동기 컨텍스트 매니저로 실행 시간 측정."""
        start_time = time.time()
        tags = tags or {}

        try:
            yield
        finally:
            duration = time.time() - start_time
            self.metrics.record_histogram(
                f"{name}.duration", duration * 1000, tags
            )  # ms 단위
            logger.debug(f"Async timer '{name}' completed in {duration*1000:.2f}ms")

    def timed(self, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
        """함수 실행 시간을 측정하는 데코레이터."""

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            metric_name = name or f"function.{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with self.timer(metric_name, tags):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def async_timed(
        self, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None
    ):
        """비동기 함수 실행 시간을 측정하는 데코레이터."""

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            metric_name = name or f"async_function.{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                async with self.async_timer(metric_name, tags):
                    return await func(*args, **kwargs)  # type: ignore

            return wrapper  # type: ignore

        return decorator

    def count_calls(
        self, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None
    ):
        """함수 호출 횟수를 카운트하는 데코레이터."""

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            metric_name = name or f"calls.{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    result = func(*args, **kwargs)
                    self.metrics.increment_counter(f"{metric_name}.success", 1, tags)
                    return result
                except Exception as e:
                    error_tags = {**(tags or {}), "error_type": type(e).__name__}
                    self.metrics.increment_counter(
                        f"{metric_name}.error", 1, error_tags
                    )
                    raise

            return wrapper

        return decorator

    def async_count_calls(
        self, name: Optional[str] = None, tags: Optional[Dict[str, str]] = None
    ):
        """비동기 함수 호출 횟수를 카운트하는 데코레이터."""

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            metric_name = name or f"async_calls.{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    result = await func(*args, **kwargs)  # type: ignore
                    self.metrics.increment_counter(f"{metric_name}.success", 1, tags)
                    return result
                except Exception as e:
                    error_tags = {**(tags or {}), "error_type": type(e).__name__}
                    self.metrics.increment_counter(
                        f"{metric_name}.error", 1, error_tags
                    )
                    raise

            return wrapper  # type: ignore

        return decorator

    def monitor_memory_usage(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """메모리 사용량 모니터링."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            # RSS (Resident Set Size) - 물리 메모리 사용량
            self.metrics.set_gauge(
                f"{name}.memory.rss", memory_info.rss / 1024 / 1024, tags
            )  # MB
            # VMS (Virtual Memory Size) - 가상 메모리 사용량
            self.metrics.set_gauge(
                f"{name}.memory.vms", memory_info.vms / 1024 / 1024, tags
            )  # MB

            # 메모리 사용률
            memory_percent = process.memory_percent()
            self.metrics.set_gauge(f"{name}.memory.percent", memory_percent, tags)

        except ImportError:
            logger.warning("psutil not available, skipping memory monitoring")
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {e}")

    def monitor_cpu_usage(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """CPU 사용량 모니터링."""
        try:
            import psutil

            process = psutil.Process()

            # CPU 사용률
            cpu_percent = process.cpu_percent()
            self.metrics.set_gauge(f"{name}.cpu.percent", cpu_percent, tags)

            # 시스템 전체 CPU 사용률
            system_cpu = psutil.cpu_percent(interval=None)
            self.metrics.set_gauge(f"{name}.system.cpu.percent", system_cpu, tags)

        except ImportError:
            logger.warning("psutil not available, skipping CPU monitoring")
        except Exception as e:
            logger.error(f"Error monitoring CPU usage: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보 반환."""
        all_metrics = self.metrics.get_all_metrics()

        # 성능 관련 메트릭만 필터링
        performance_metrics: Dict[str, Dict[str, Any]] = {}

        for category in ["histograms", "counters", "gauges"]:
            performance_metrics[category] = {}
            for key, value in all_metrics[category].items():
                # 성능 관련 메트릭만 선택
                if any(
                    keyword in key
                    for keyword in [
                        "duration",
                        "calls",
                        "memory",
                        "cpu",
                        "latency",
                        "response_time",
                    ]
                ):
                    performance_metrics[category][key] = value

        return performance_metrics

    def record_event_processing_time(
        self,
        event_type: str,
        duration_ms: float,
        success: bool = True,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """이벤트 처리 시간 기록."""
        base_tags = {
            "event_type": event_type,
            "status": "success" if success else "error",
        }
        if tags:
            base_tags.update(tags)

        # 처리 시간 히스토그램
        self.metrics.record_histogram("event.processing_time", duration_ms, base_tags)

        # 이벤트 카운트
        self.metrics.increment_counter("event.processed", 1, base_tags)

    def record_websocket_metrics(
        self,
        event: str,
        connection_count: Optional[int] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """WebSocket 메트릭 기록."""
        base_tags = {"event": event}
        if tags:
            base_tags.update(tags)

        # WebSocket 이벤트 카운트
        self.metrics.increment_counter("websocket.events", 1, base_tags)

        # 연결 수 게이지 (제공된 경우)
        if connection_count is not None:
            self.metrics.set_gauge("websocket.connections", connection_count, tags)

    def record_game_session_metrics(
        self,
        game_type: str,
        session_duration_seconds: float,
        players_count: int,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """게임 세션 메트릭 기록."""
        base_tags = {"game_type": game_type, "players": str(players_count)}
        if tags:
            base_tags.update(tags)

        # 세션 지속 시간
        self.metrics.record_histogram(
            "game.session_duration", session_duration_seconds, base_tags
        )

        # 세션 카운트
        self.metrics.increment_counter("game.sessions", 1, base_tags)

    def record_game_session_start(
        self,
        game_type: str,
        room_id: str,
        player_count: int,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """게임 세션 시작 메트릭 기록."""
        base_tags = {
            "game_type": game_type,
            "room_id": room_id,
            "players": str(player_count),
        }
        if tags:
            base_tags.update(tags)

        # 게임 세션 시작 카운트
        self.metrics.increment_counter("game.sessions_started", 1, base_tags)

        # 현재 활성 세션 수 증가
        current_sessions = self.metrics._gauges.get(
            "game.active_sessions", GaugeMetric("game.active_sessions", 0)
        ).value
        self.metrics.set_gauge(
            "game.active_sessions", current_sessions + 1, {"game_type": game_type}
        )

    def record_game_session_end(
        self,
        game_type: str,
        room_id: str,
        winner: Optional[str] = None,
        reason: str = "normal",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """게임 세션 종료 메트릭 기록."""
        base_tags = {"game_type": game_type, "room_id": room_id, "reason": reason}
        if winner:
            base_tags["winner"] = winner
        if tags:
            base_tags.update(tags)

        # 게임 세션 종료 카운트
        self.metrics.increment_counter("game.sessions_ended", 1, base_tags)

        # 현재 활성 세션 수 감소
        current_sessions = self.metrics._gauges.get(
            "game.active_sessions", GaugeMetric("game.active_sessions", 1)
        ).value
        self.metrics.set_gauge(
            "game.active_sessions",
            max(0, current_sessions - 1),
            {"game_type": game_type},
        )


# 전역 성능 모니터 인스턴스
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """전역 성능 모니터 인스턴스 반환."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# 편의 함수들
def timer(name: str, tags: Optional[Dict[str, str]] = None):
    """실행 시간 측정 컨텍스트 매니저."""
    return get_performance_monitor().timer(name, tags)


def async_timer(name: str, tags: Optional[Dict[str, str]] = None):
    """비동기 실행 시간 측정 컨텍스트 매니저."""
    return get_performance_monitor().async_timer(name, tags)


def timed(name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """함수 실행 시간 측정 데코레이터."""
    return get_performance_monitor().timed(name, tags)


def async_timed(name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """비동기 함수 실행 시간 측정 데코레이터."""
    return get_performance_monitor().async_timed(name, tags)


def count_calls(name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """함수 호출 횟수 카운트 데코레이터."""
    return get_performance_monitor().count_calls(name, tags)
