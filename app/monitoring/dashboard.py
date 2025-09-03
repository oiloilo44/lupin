"""모니터링 대시보드."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config_metrics import get_config_metrics
from .metrics import get_metrics_collector
from .performance import get_performance_monitor

logger = logging.getLogger(__name__)


class MonitoringDashboard:
    """모니터링 대시보드 데이터 제공."""

    def __init__(self):
        self.metrics = get_metrics_collector()
        self.performance = get_performance_monitor()
        self.config_metrics = get_config_metrics()

    def get_overview(self) -> Dict[str, Any]:
        """전체 시스템 개요."""
        all_metrics = self.metrics.get_all_metrics()
        config_health = self.config_metrics.get_config_health_score()

        # 주요 지표 추출
        total_connections = 0
        total_errors = 0
        total_requests = 0

        # WebSocket 연결 수
        for key, gauge in all_metrics.get("gauges", {}).items():
            if "websocket.connections" in key:
                total_connections = max(total_connections, gauge["value"])

        # 에러 카운트
        for key, counter in all_metrics.get("counters", {}).items():
            if "error" in key or "failed" in key:
                total_errors += counter["value"]

        # 총 요청 수
        for key, counter in all_metrics.get("counters", {}).items():
            if "calls" in key or "requests" in key:
                total_requests += counter["value"]

        # 평균 응답 시간 계산
        avg_response_time = 0.0
        response_time_metrics = []

        for key, histogram in all_metrics.get("histograms", {}).items():
            if "duration" in key or "response_time" in key:
                response_time_metrics.append(histogram["avg"])

        if response_time_metrics:
            avg_response_time = sum(response_time_metrics) / len(response_time_metrics)

        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": {
                "status": (
                    "healthy"
                    if total_errors < 10
                    else "warning" if total_errors < 50 else "critical"
                ),
                "total_errors": total_errors,
                "error_rate": (
                    (total_errors / total_requests * 100) if total_requests > 0 else 0
                ),
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "total_requests": total_requests,
            },
            "connections": {"websocket_connections": total_connections},
            "config_health": config_health,
            "metrics_summary": {
                "counters": len(all_metrics.get("counters", {})),
                "gauges": len(all_metrics.get("gauges", {})),
                "histograms": len(all_metrics.get("histograms", {})),
            },
        }

    def get_performance_metrics(self, hours: int = 1) -> Dict[str, Any]:
        """성능 메트릭 대시보드."""
        performance_summary = self.performance.get_performance_summary()

        # 주요 성능 지표들
        response_times: Dict[str, Any] = {}
        error_rates: Dict[str, Any] = {}

        # 응답 시간 분석
        for key, histogram in performance_summary.get("histograms", {}).items():
            if "duration" in key:
                response_times[key] = {
                    "avg": histogram["avg"],
                    "p50": histogram["p50"],
                    "p95": histogram["p95"],
                    "p99": histogram["p99"],
                    "count": histogram["count"],
                }

        # 에러율 분석
        success_counters = {}
        error_counters = {}

        for key, counter in performance_summary.get("counters", {}).items():
            if "success" in key:
                base_key = key.replace(".success", "")
                success_counters[base_key] = counter["value"]
            elif "error" in key:
                base_key = key.replace(".error", "")
                error_counters[base_key] = counter["value"]

        for base_key in set(success_counters.keys()) | set(error_counters.keys()):
            success = success_counters.get(base_key, 0)
            errors = error_counters.get(base_key, 0)
            total = success + errors

            if total > 0:
                error_rates[base_key] = {
                    "error_rate": (errors / total * 100),
                    "success_count": success,
                    "error_count": errors,
                    "total_count": total,
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "analysis_period_hours": hours,
            "response_times": response_times,
            "error_rates": error_rates,
            "top_slow_endpoints": self._get_top_slow_endpoints(response_times),
            "top_error_endpoints": self._get_top_error_endpoints(error_rates),
        }

    def get_websocket_metrics(self) -> Dict[str, Any]:
        """WebSocket 메트릭 대시보드."""
        all_metrics = self.metrics.get_all_metrics()

        # WebSocket 관련 메트릭만 추출
        websocket_counters = {}
        websocket_gauges = {}

        for key, counter in all_metrics.get("counters", {}).items():
            if "websocket" in key:
                websocket_counters[key] = counter

        for key, gauge in all_metrics.get("gauges", {}).items():
            if "websocket" in key:
                websocket_gauges[key] = gauge

        # 연결 통계
        current_connections = 0
        total_events = 0

        for gauge in websocket_gauges.values():
            if "connections" in gauge["name"]:
                current_connections = max(current_connections, gauge["value"])

        for counter in websocket_counters.values():
            if "events" in counter["name"]:
                total_events += counter["value"]

        return {
            "timestamp": datetime.now().isoformat(),
            "current_connections": current_connections,
            "total_events": total_events,
            "counters": websocket_counters,
            "gauges": websocket_gauges,
            "connection_health": "healthy" if current_connections < 100 else "warning",
        }

    def get_game_metrics(self) -> Dict[str, Any]:
        """게임 메트릭 대시보드."""
        all_metrics = self.metrics.get_all_metrics()

        # 게임 관련 메트릭 추출
        game_counters = {}
        game_histograms = {}

        for key, counter in all_metrics.get("counters", {}).items():
            if "game" in key:
                game_counters[key] = counter

        for key, histogram in all_metrics.get("histograms", {}).items():
            if "game" in key:
                game_histograms[key] = histogram

        # 게임별 통계
        game_stats = {}

        for key, counter in game_counters.items():
            game_type = counter.get("tags", {}).get("game_type")
            if game_type:
                if game_type not in game_stats:
                    game_stats[game_type] = {
                        "sessions": 0,
                        "total_players": 0,
                        "avg_session_duration": 0,
                    }

                if "sessions" in key:
                    game_stats[game_type]["sessions"] += counter["value"]

        return {
            "timestamp": datetime.now().isoformat(),
            "game_stats": game_stats,
            "counters": game_counters,
            "histograms": game_histograms,
        }

    def get_config_metrics(self) -> Dict[str, Any]:
        """설정 메트릭 대시보드."""
        config_stats = self.config_metrics.get_config_change_stats()
        recent_changes = self.config_metrics.get_config_change_history(hours=24)
        health_score = self.config_metrics.get_config_health_score()

        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": health_score,
            "stats": config_stats,
            "recent_changes": recent_changes[:10],  # 최근 10개만
            "change_frequency": len(recent_changes),
        }

    def get_system_resources(self) -> Dict[str, Any]:
        """시스템 리소스 메트릭."""
        # 시스템 리소스 모니터링 시도
        self.performance.monitor_memory_usage("system")
        self.performance.monitor_cpu_usage("system")

        all_metrics = self.metrics.get_all_metrics()

        # 시스템 리소스 메트릭 추출
        memory_metrics = {}
        cpu_metrics = {}

        for key, gauge in all_metrics.get("gauges", {}).items():
            if "memory" in key:
                memory_metrics[key] = gauge
            elif "cpu" in key:
                cpu_metrics[key] = gauge

        return {
            "timestamp": datetime.now().isoformat(),
            "memory": memory_metrics,
            "cpu": cpu_metrics,
        }

    def get_alerts(self) -> List[Dict[str, Any]]:
        """시스템 알림 생성."""
        alerts = []
        overview = self.get_overview()

        # 에러율 알림
        if overview["system_health"]["error_rate"] > 5:
            alerts.append(
                {
                    "level": (
                        "warning"
                        if overview["system_health"]["error_rate"] < 10
                        else "critical"
                    ),
                    "message": (
                        f"High error rate: "
                        f"{overview['system_health']['error_rate']:.2f}%"
                    ),
                    "metric": "error_rate",
                    "value": overview["system_health"]["error_rate"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 응답 시간 알림
        if overview["performance"]["avg_response_time_ms"] > 1000:
            alerts.append(
                {
                    "level": (
                        "warning"
                        if overview["performance"]["avg_response_time_ms"] < 2000
                        else "critical"
                    ),
                    "message": (
                        f"High response time: "
                        f"{overview['performance']['avg_response_time_ms']:.2f}ms"
                    ),
                    "metric": "response_time",
                    "value": overview["performance"]["avg_response_time_ms"],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 설정 건강도 알림
        config_health = overview["config_health"]["health_score"]
        if config_health < 80:
            alerts.append(
                {
                    "level": "warning" if config_health >= 60 else "critical",
                    "message": f"Config system health low: {config_health:.1f}/100",
                    "metric": "config_health",
                    "value": config_health,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return alerts

    def _get_top_slow_endpoints(
        self, response_times: Dict[str, Any], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """가장 느린 엔드포인트들."""
        endpoints = []
        for key, metrics in response_times.items():
            endpoints.append(
                {
                    "endpoint": key,
                    "avg_time": metrics["avg"],
                    "p95_time": metrics["p95"],
                    "count": metrics["count"],
                }
            )

        return sorted(endpoints, key=lambda x: x["avg_time"], reverse=True)[:limit]

    def _get_top_error_endpoints(
        self, error_rates: Dict[str, Any], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """에러율이 가장 높은 엔드포인트들."""
        endpoints = []
        for key, metrics in error_rates.items():
            endpoints.append(
                {
                    "endpoint": key,
                    "error_rate": metrics["error_rate"],
                    "error_count": metrics["error_count"],
                    "total_count": metrics["total_count"],
                }
            )

        return sorted(endpoints, key=lambda x: x["error_rate"], reverse=True)[:limit]


# 전역 대시보드 인스턴스
_dashboard: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """전역 대시보드 인스턴스 반환."""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard
