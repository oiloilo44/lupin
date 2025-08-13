"""
헬스체크 엔드포인트 - 컨테이너 상태 모니터링
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Response, status

from ..monitoring.metrics import get_metrics_collector
from ..monitoring.performance import get_performance_monitor
from ..session_manager import SessionManager
from ..room_manager import room_manager

router = APIRouter(prefix="/health", tags=["health"])

# 헬스체크 메트릭
metrics_collector = get_metrics_collector()
performance_monitor = get_performance_monitor()


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    기본 헬스체크 - Docker healthcheck용
    """
    try:
        # 기본 서비스 상태 확인
        session_manager_status = SessionManager._instances is not None
        room_manager_status = room_manager is not None
        
        if session_manager_status and room_manager_status:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "lupin-game"
            }
        else:
            return Response(
                content={"status": "unhealthy", "error": "Core services not ready"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        return Response(
            content={"status": "unhealthy", "error": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/live")
async def liveness_probe() -> Dict[str, str]:
    """
    라이브니스 프로브 - 애플리케이션이 살아있는지 확인
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    레디니스 프로브 - 애플리케이션이 트래픽을 받을 준비가 되었는지 확인
    """
    try:
        # 서비스 준비 상태 확인
        checks = {
            "session_manager": SessionManager._instances is not None,
            "room_manager": room_manager is not None,
            "metrics_collector": metrics_collector is not None,
            "performance_monitor": performance_monitor is not None
        }
        
        all_ready = all(checks.values())
        
        if all_ready:
            return {
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "checks": checks
            }
        else:
            return Response(
                content={
                    "status": "not_ready",
                    "timestamp": datetime.now().isoformat(),
                    "checks": checks
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    except Exception as e:
        return Response(
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@router.get("/detailed")
async def detailed_health() -> Dict[str, Any]:
    """
    상세 헬스체크 - 모니터링 대시보드용
    """
    try:
        # 세션 통계
        session_stats = {
            "total_sessions": len(SessionManager()._sessions),
            "active_sessions": sum(
                1 for s in SessionManager()._sessions.values() 
                if s.get("last_seen", 0) > datetime.now().timestamp() - 300
            )
        }
        
        # 방 통계
        room_stats = {
            "total_rooms": len(room_manager.rooms),
            "active_games": sum(
                1 for room in room_manager.rooms.values() 
                if len(room.players) == 2
            )
        }
        
        # 메트릭 통계
        metrics_stats = metrics_collector.get_summary() if metrics_collector else {}
        
        # WebSocket 연결 통계
        ws_stats = performance_monitor.get_connection_metrics() if performance_monitor else {}
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": metrics_collector._counters.get(
                "app.uptime", {"value": 0}
            ).get("value", 0) if metrics_collector else 0,
            "stats": {
                "sessions": session_stats,
                "rooms": room_stats,
                "metrics": metrics_stats,
                "websocket": ws_stats
            },
            "environment": {
                "version": "1.0.0",
                "environment": "production"
            }
        }
    except Exception as e:
        return {
            "status": "partial",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "stats": {}
        }