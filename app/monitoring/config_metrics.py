"""설정 변경 추적 및 메트릭"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .metrics import MetricsCollector, get_metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class ConfigChange:
    """설정 변경 기록"""

    timestamp: datetime
    config_name: str
    path: str
    old_value: Any
    new_value: Any
    changed_by: Optional[str] = None  # 사용자 ID 또는 시스템
    source: str = "api"  # api, file, system 등
    tags: Dict[str, str] = field(default_factory=dict)


class ConfigMetrics:
    """설정 변경 메트릭 수집기"""

    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        max_history: int = 1000,
    ):
        """
        Args:
            metrics_collector: 메트릭 수집기
            max_history: 최대 변경 히스토리 보관 개수
        """
        self.metrics = metrics_collector or get_metrics_collector()
        self.max_history = max_history
        self._change_history: List[ConfigChange] = []

    def record_config_change(
        self,
        config_name: str,
        path: str,
        old_value: Any,
        new_value: Any,
        changed_by: Optional[str] = None,
        source: str = "api",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """설정 변경 기록"""
        change = ConfigChange(
            timestamp=datetime.now(),
            config_name=config_name,
            path=path,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            source=source,
            tags=tags or {},
        )

        # 히스토리 추가
        self._change_history.append(change)

        # 최대 히스토리 수 제한
        if len(self._change_history) > self.max_history:
            self._change_history.pop(0)

        # 메트릭 기록
        metric_tags = {
            "config_name": config_name,
            "path": path,
            "source": source,
            **change.tags,
        }

        if changed_by:
            metric_tags["changed_by"] = changed_by

        # 설정 변경 카운트
        self.metrics.increment_counter("config.changes", 1, metric_tags)

        # 설정별 변경 카운트
        self.metrics.increment_counter(
            f"config.{config_name}.changes",
            1,
            {k: v for k, v in metric_tags.items() if k != "config_name"},
        )

        logger.info(
            f"Config change recorded: {config_name}.{path} = {new_value} "
            f"(was: {old_value}) by {changed_by or 'system'}"
        )

    def record_config_load_time(
        self,
        config_name: str,
        load_time_ms: float,
        source: str = "file",
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """설정 로드 시간 기록"""
        metric_tags = {"config_name": config_name, "source": source, **(tags or {})}

        self.metrics.record_histogram("config.load_time", load_time_ms, metric_tags)

    def record_config_validation_result(
        self,
        config_name: str,
        success: bool,
        error_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """설정 검증 결과 기록"""
        metric_tags = {
            "config_name": config_name,
            "status": "success" if success else "error",
            **(tags or {}),
        }

        if not success and error_type:
            metric_tags["error_type"] = error_type

        self.metrics.increment_counter("config.validation", 1, metric_tags)

    def record_config_cache_metrics(
        self,
        cache_hits: int,
        cache_misses: int,
        cache_size: int,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """설정 캐시 메트릭 기록"""
        base_tags = tags or {}

        self.metrics.set_gauge("config.cache.hits", cache_hits, base_tags)
        self.metrics.set_gauge("config.cache.misses", cache_misses, base_tags)
        self.metrics.set_gauge("config.cache.size", cache_size, base_tags)

        # 캐시 히트율 계산
        total_requests = cache_hits + cache_misses
        if total_requests > 0:
            hit_rate = (cache_hits / total_requests) * 100
            self.metrics.set_gauge("config.cache.hit_rate", hit_rate, base_tags)

    def get_config_change_history(
        self, config_name: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """설정 변경 히스토리 조회"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=hours)

        filtered_changes = []
        for change in self._change_history:
            if change.timestamp >= cutoff:
                if config_name is None or change.config_name == config_name:
                    filtered_changes.append(
                        {
                            "timestamp": change.timestamp.isoformat(),
                            "config_name": change.config_name,
                            "path": change.path,
                            "old_value": change.old_value,
                            "new_value": change.new_value,
                            "changed_by": change.changed_by,
                            "source": change.source,
                            "tags": change.tags,
                        }
                    )

        return sorted(filtered_changes, key=lambda x: x["timestamp"], reverse=True)

    def get_config_change_stats(self) -> Dict[str, Any]:
        """설정 변경 통계"""
        all_metrics = self.metrics.get_all_metrics()

        # 설정 관련 카운터 추출
        config_counters = {}
        for key, value in all_metrics.get("counters", {}).items():
            if key.startswith("config."):
                config_counters[key] = value

        # 설정 관련 히스토그램 추출
        config_histograms = {}
        for key, value in all_metrics.get("histograms", {}).items():
            if key.startswith("config."):
                config_histograms[key] = value

        # 설정 관련 게이지 추출
        config_gauges = {}
        for key, value in all_metrics.get("gauges", {}).items():
            if key.startswith("config."):
                config_gauges[key] = value

        return {
            "total_changes": len(self._change_history),
            "counters": config_counters,
            "histograms": config_histograms,
            "gauges": config_gauges,
            "recent_changes_count": len(self.get_config_change_history(hours=1)),
        }

    def analyze_config_impact(self, config_name: str, hours: int = 1) -> Dict[str, Any]:
        """설정 변경이 성능에 미친 영향 분석"""
        # 최근 변경사항 조회
        recent_changes = self.get_config_change_history(config_name, hours)

        if not recent_changes:
            return {"message": "No recent changes found", "changes": 0}

        # 변경 전후 성능 메트릭 비교를 위한 기본 구조
        analysis = {
            "config_name": config_name,
            "analysis_period_hours": hours,
            "changes_count": len(recent_changes),
            "recent_changes": recent_changes[:5],  # 최근 5개만
            "performance_impact": {
                "message": "Performance impact analysis requires before/after metrics",
                "note": "This would compare metrics before and after config changes",
            },
        }

        # 실제 성능 영향 분석은 더 복잡한 로직이 필요
        # 여기서는 기본 구조만 제공

        return analysis

    def get_config_health_score(self) -> Dict[str, Any]:
        """설정 시스템 건강도 점수"""
        all_metrics = self.metrics.get_all_metrics()

        # 캐시 히트율 확인
        cache_gauges = {
            k: v
            for k, v in all_metrics.get("gauges", {}).items()
            if "config.cache" in k
        }

        hit_rate = 0.0
        if "config.cache.hit_rate" in cache_gauges:
            hit_rate = cache_gauges["config.cache.hit_rate"]["value"]

        # 에러율 확인
        validation_counters = {
            k: v
            for k, v in all_metrics.get("counters", {}).items()
            if "config.validation" in k
        }

        total_validations = 0
        error_validations = 0

        for key, counter in validation_counters.items():
            total_validations += counter["value"]
            if "error" in counter.get("tags", {}).get("status", ""):
                error_validations += counter["value"]

        error_rate = (
            (error_validations / total_validations * 100)
            if total_validations > 0
            else 0
        )

        # 건강도 점수 계산 (0-100)
        health_score = 100

        # 캐시 히트율이 낮으면 점수 감점
        if hit_rate < 80:
            health_score -= int((80 - hit_rate) * 0.5)

        # 에러율이 높으면 점수 감점
        if error_rate > 5:
            health_score -= int((error_rate - 5) * 2)

        health_score = max(0, min(100, health_score))

        return {
            "health_score": round(health_score, 2),
            "cache_hit_rate": round(hit_rate, 2),
            "error_rate": round(error_rate, 2),
            "total_changes": len(self._change_history),
            "status": (
                "healthy"
                if health_score >= 80
                else "warning" if health_score >= 60 else "critical"
            ),
        }


# 전역 설정 메트릭 인스턴스
_config_metrics: Optional[ConfigMetrics] = None


def get_config_metrics() -> ConfigMetrics:
    """전역 설정 메트릭 인스턴스 반환"""
    global _config_metrics
    if _config_metrics is None:
        _config_metrics = ConfigMetrics()
    return _config_metrics
