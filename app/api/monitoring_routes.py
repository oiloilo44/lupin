"""모니터링 API 라우트."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..monitoring.config_metrics import get_config_metrics
from ..monitoring.dashboard import get_dashboard
from ..monitoring.metrics import get_metrics_collector
from ..monitoring.performance import get_performance_monitor

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

dashboard = get_dashboard()
metrics_collector = get_metrics_collector()
performance_monitor = get_performance_monitor()
config_metrics = get_config_metrics()


class MetricRequest(BaseModel):
    """메트릭 기록 요청."""

    name: str
    value: float
    tags: Optional[Dict[str, str]] = None


@router.get("/overview")
async def get_system_overview() -> Dict[str, Any]:
    """시스템 전체 개요."""
    return dashboard.get_overview()


@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(1, ge=1, le=168, description="분석 기간 (시간)")
) -> Dict[str, Any]:
    """성능 메트릭."""
    return dashboard.get_performance_metrics(hours)


@router.get("/websocket")
async def get_websocket_metrics() -> Dict[str, Any]:
    """WebSocket 메트릭."""
    return dashboard.get_websocket_metrics()


@router.get("/games")
async def get_game_metrics() -> Dict[str, Any]:
    """게임 메트릭."""
    return dashboard.get_game_metrics()


@router.get("/config")
async def get_config_monitoring() -> Dict[str, Any]:
    """설정 메트릭."""
    return dashboard.get_config_metrics()


@router.get("/system")
async def get_system_resources() -> Dict[str, Any]:
    """시스템 리소스."""
    return dashboard.get_system_resources()


@router.get("/alerts")
async def get_system_alerts() -> List[Dict[str, Any]]:
    """시스템 알림."""
    return dashboard.get_alerts()


@router.get("/metrics/raw")
async def get_raw_metrics() -> Dict[str, Any]:
    """원시 메트릭 데이터."""
    return metrics_collector.get_all_metrics()


@router.post("/metrics/counter")
async def record_counter_metric(request: MetricRequest) -> Dict[str, str]:
    """카운터 메트릭 기록."""
    metrics_collector.increment_counter(request.name, int(request.value), request.tags)
    return {"message": f"Counter metric '{request.name}' recorded successfully"}


@router.post("/metrics/gauge")
async def record_gauge_metric(request: MetricRequest) -> Dict[str, str]:
    """게이지 메트릭 기록."""
    metrics_collector.set_gauge(request.name, request.value, request.tags)
    return {"message": f"Gauge metric '{request.name}' recorded successfully"}


@router.post("/metrics/histogram")
async def record_histogram_metric(request: MetricRequest) -> Dict[str, str]:
    """히스토그램 메트릭 기록."""
    metrics_collector.record_histogram(request.name, request.value, request.tags)
    return {"message": (f"Histogram metric '{request.name}' recorded successfully")}


@router.get("/config/changes")
async def get_config_change_history(
    config_name: Optional[str] = Query(None, description="설정 이름 필터"),
    hours: int = Query(24, ge=1, le=720, description="조회 기간 (시간)"),
) -> List[Dict[str, Any]]:
    """설정 변경 히스토리."""
    return config_metrics.get_config_change_history(config_name, hours)


@router.get("/config/impact/{config_name}")
async def analyze_config_impact(
    config_name: str,
    hours: int = Query(1, ge=1, le=168, description="분석 기간 (시간)"),
) -> Dict[str, Any]:
    """설정 변경 영향 분석."""
    return config_metrics.analyze_config_impact(config_name, hours)


@router.get("/config/health")
async def get_config_health() -> Dict[str, Any]:
    """설정 시스템 건강도."""
    return config_metrics.get_config_health_score()


@router.delete("/metrics")
async def reset_all_metrics() -> Dict[str, str]:
    """모든 메트릭 초기화."""
    metrics_collector.reset_metrics()
    return {"message": "All metrics have been reset successfully"}


@router.get("/health")
async def monitoring_health_check() -> Dict[str, Any]:
    """모니터링 시스템 헬스체크."""
    overview = dashboard.get_overview()
    alerts = dashboard.get_alerts()

    critical_alerts = [alert for alert in alerts if alert["level"] == "critical"]
    warning_alerts = [alert for alert in alerts if alert["level"] == "warning"]

    health_status = "healthy"
    if critical_alerts:
        health_status = "critical"
    elif warning_alerts:
        health_status = "warning"

    return {
        "status": health_status,
        "timestamp": overview["timestamp"],
        "alerts_count": {
            "critical": len(critical_alerts),
            "warning": len(warning_alerts),
            "total": len(alerts),
        },
        "system_health": overview["system_health"],
        "config_health": overview["config_health"],
    }
