"""헬스체크 엔드포인트 - 컨테이너 상태 모니터링."""

from datetime import datetime
from typing import Any, Dict, cast

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ..monitoring.metrics import get_metrics_collector
from ..monitoring.performance import get_performance_monitor
from ..room_manager import room_manager
from ..session_manager import session_manager

router = APIRouter(prefix="/health", tags=["health"])

# 헬스체크 메트릭
metrics_collector = get_metrics_collector()
performance_monitor = get_performance_monitor()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """기본 헬스체크 - Docker healthcheck용."""
    # 최소한의 헬스체크 - 서버가 응답하면 healthy
    # 세부 서비스 상태는 /health/detailed 에서 확인
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "lupin-game",
    }


@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """라이브니스 프로브 - 애플리케이션이 살아있는지 확인."""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


def _validate_service_readiness() -> Dict[str, bool]:
    """서비스 준비 상태를 검증하는 재사용 가능한 메서드."""
    return {
        "session_manager": (
            session_manager is not None
            and hasattr(session_manager, "sessions")
            and isinstance(session_manager.sessions, dict)
            and hasattr(session_manager, "create_session")
            and hasattr(session_manager, "get_session_data")
        ),
        "room_manager": room_manager is not None,
        "metrics_collector": metrics_collector is not None,
        "performance_monitor": performance_monitor is not None,
    }


@router.get("/ready", response_model=None)
async def readiness_probe():
    """레디니스 프로브 - 애플리케이션이 트래픽을 받을 준비가 되었는지 확인."""
    # 서비스 준비 상태 확인
    checks = _validate_service_readiness()
    all_ready = all(checks.values())

    if all_ready:
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }
    else:
        return JSONResponse(
            content={
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "checks": checks,
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """상세 헬스체크 - 모니터링 대시보드용."""
    # 세션 통계
    sessions = session_manager.sessions
    session_stats = {
        "total_sessions": len(sessions),
        "active_sessions": sum(
            1
            for s in sessions.values()
            if isinstance(s, dict)
            and s.get("last_seen", 0) > (datetime.now().timestamp() - 300)
        ),
    }

    # 방 통계
    room_stats = {
        "total_rooms": len(room_manager.lifecycle_manager.rooms),
        "active_games": sum(
            1
            for room in room_manager.lifecycle_manager.rooms.values()
            if len(room.players) == 2
        ),
    }

    # 메트릭 통계
    metrics_stats = cast(
        Dict[str, Any],
        (
            getattr(metrics_collector, "get_summary", lambda: {})()
            if metrics_collector
            else {}
        ),
    )

    # WebSocket 연결 통계
    ws_stats = cast(
        Dict[str, Any],
        (
            getattr(performance_monitor, "get_connection_metrics", lambda: {})()
            if performance_monitor
            else {}
        ),
    )

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (
            getattr(metrics_collector, "_counters", {})
            .get("app.uptime", {"value": 0})
            .get("value", 0)
            if metrics_collector
            else 0
        ),
        "stats": {
            "sessions": session_stats,
            "rooms": room_stats,
            "metrics": metrics_stats,
            "websocket": ws_stats,
        },
        "environment": {"version": "1.0.0", "environment": "production"},
    }
