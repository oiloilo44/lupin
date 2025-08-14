"""기본 메트릭 수집 시스템."""
import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, DefaultDict, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """메트릭 데이터 포인트."""

    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class CounterMetric:
    """카운터 메트릭 (누적 값)."""

    name: str
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class GaugeMetric:
    """게이지 메트릭 (현재 값)."""

    name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class HistogramMetric:
    """히스토그램 메트릭 (분포 측정)."""

    name: str
    values: List[float] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    max_samples: int = 1000

    def add_value(self, value: float) -> None:
        """값 추가."""
        self.values.append(value)
        # 최대 샘플 수 제한
        if len(self.values) > self.max_samples:
            self.values.pop(0)

    @property
    def count(self) -> int:
        """총 샘플 수."""
        return len(self.values)

    @property
    def sum(self) -> float:
        """총합."""
        return sum(self.values) if self.values else 0.0

    @property
    def avg(self) -> float:
        """평균."""
        return self.sum / self.count if self.count > 0 else 0.0

    @property
    def min(self) -> float:
        """최솟값."""
        return min(self.values) if self.values else 0.0

    @property
    def max(self) -> float:
        """최댓값."""
        return max(self.values) if self.values else 0.0

    def percentile(self, p: float) -> float:
        """백분위수 계산."""
        if not self.values:
            return 0.0

        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * p / 100.0)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


class MetricsCollector:
    """메트릭 수집기."""

    def __init__(self, retention_hours: int = 24):
        """
        Args:
            retention_hours: 메트릭 보존 시간 (시간)
        """
        self.retention_hours = retention_hours
        self._lock = threading.RLock()

        # 메트릭 저장소
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._time_series: DefaultDict[str, deque[MetricPoint]] = defaultdict(deque)

        # 자동 정리를 위한 타이머
        self._last_cleanup = datetime.now()
        self._cleanup_interval = timedelta(hours=1)

    def increment_counter(
        self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """카운터 증가."""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._lock:
            if key not in self._counters:
                self._counters[key] = CounterMetric(name=name, tags=tags)
            self._counters[key].value += value

            # 시계열 데이터 추가
            self._add_time_series_point(key, float(self._counters[key].value), tags)

    def set_gauge(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """게이지 값 설정."""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._lock:
            self._gauges[key] = GaugeMetric(
                name=name, value=value, tags=tags, updated_at=datetime.now()
            )

            # 시계열 데이터 추가
            self._add_time_series_point(key, value, tags)

    def record_histogram(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """히스토그램에 값 기록."""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = HistogramMetric(name=name, tags=tags)
            self._histograms[key].add_value(value)

            # 시계열 데이터 추가 (평균값)
            avg_value = self._histograms[key].avg
            self._add_time_series_point(key, avg_value, tags)

    def get_counter(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> Optional[CounterMetric]:
        """카운터 조회."""
        key = self._make_key(name, tags or {})
        with self._lock:
            return self._counters.get(key)

    def get_gauge(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> Optional[GaugeMetric]:
        """게이지 조회."""
        key = self._make_key(name, tags or {})
        with self._lock:
            return self._gauges.get(key)

    def get_histogram(
        self, name: str, tags: Optional[Dict[str, str]] = None
    ) -> Optional[HistogramMetric]:
        """히스토그램 조회."""
        key = self._make_key(name, tags or {})
        with self._lock:
            return self._histograms.get(key)

    def get_time_series(
        self, name: str, tags: Optional[Dict[str, str]] = None, hours: int = 1
    ) -> List[MetricPoint]:
        """시계열 데이터 조회."""
        key = self._make_key(name, tags or {})
        cutoff = datetime.now() - timedelta(hours=hours)

        with self._lock:
            points = self._time_series.get(key, deque())
            return [p for p in points if p.timestamp >= cutoff]

    def get_all_metrics(self) -> Dict[str, Any]:
        """모든 메트릭 조회."""
        with self._lock:
            self._cleanup_old_data()

            result = {
                "counters": {
                    k: {
                        "name": v.name,
                        "value": v.value,
                        "tags": v.tags,
                        "created_at": v.created_at.isoformat(),
                    }
                    for k, v in self._counters.items()
                },
                "gauges": {
                    k: {
                        "name": v.name,
                        "value": v.value,
                        "tags": v.tags,
                        "updated_at": v.updated_at.isoformat(),
                    }
                    for k, v in self._gauges.items()
                },
                "histograms": {
                    k: {
                        "name": v.name,
                        "count": v.count,
                        "sum": v.sum,
                        "avg": v.avg,
                        "min": v.min,
                        "max": v.max,
                        "p50": v.percentile(50),
                        "p95": v.percentile(95),
                        "p99": v.percentile(99),
                        "tags": v.tags,
                    }
                    for k, v in self._histograms.items()
                },
                "time_series_count": len(self._time_series),
                "last_cleanup": self._last_cleanup.isoformat(),
            }

            return result

    def reset_metrics(self) -> None:
        """모든 메트릭 초기화."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._time_series.clear()
            logger.info("All metrics have been reset")

    def _make_key(self, name: str, tags: Dict[str, str]) -> str:
        """메트릭 키 생성."""
        if not tags:
            return name

        # 태그를 정렬하여 일관된 키 생성
        tag_parts = [f"{k}: {v}" for k, v in sorted(tags.items())]
        return f"{name}|{','.join(tag_parts)}"

    def _add_time_series_point(
        self, key: str, value: float, tags: Dict[str, str]
    ) -> None:
        """시계열 데이터 포인트 추가."""
        point = MetricPoint(timestamp=datetime.now(), value=value, tags=tags)

        self._time_series[key].append(point)

        # 오래된 데이터 정리 (메모리 절약)
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        while self._time_series[key] and self._time_series[key][0].timestamp < cutoff:
            self._time_series[key].popleft()

    def _cleanup_old_data(self) -> None:
        """오래된 데이터 정리."""
        now = datetime.now()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - timedelta(hours=self.retention_hours)

        # 시계열 데이터 정리
        for key in list(self._time_series.keys()):
            points = self._time_series[key]
            while points and points[0].timestamp < cutoff:
                points.popleft()

            # 빈 덱 제거
            if not points:
                del self._time_series[key]

        self._last_cleanup = now
        logger.debug(f"Cleaned up old metrics data. Cutoff: {cutoff}")


# 전역 메트릭 수집기 인스턴스
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """전역 메트릭 수집기 인스턴스 반환."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# 편의 함수들
def increment(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
    """카운터 증가."""
    get_metrics_collector().increment_counter(name, value, tags)


def gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """게이지 설정."""
    get_metrics_collector().set_gauge(name, value, tags)


def histogram(name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """히스토그램 기록."""
    get_metrics_collector().record_histogram(name, value, tags)
