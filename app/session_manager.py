"""Session management system for user authentication and state tracking."""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import Request, Response

from .models import Player


class SessionManager:
    """세션 관리 시스템."""

    def __init__(self):
        """Initialize the session manager."""
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_data
        self.session_timeout = timedelta(hours=24)  # 24시간 세션 유지

    def generate_session_id(self) -> str:
        """새로운 세션 ID 생성."""
        return str(uuid.uuid4())

    def create_session(
        self, response: Response, player_data: Optional[Dict] = None
    ) -> str:
        """새 세션 생성 및 쿠키 설정."""
        session_id = self.generate_session_id()

        # 세션 데이터 저장
        self.sessions[session_id] = {
            "created_at": datetime.now(),
            "last_seen": datetime.now(),
            "player_data": player_data or {},
            "room_id": None,
            "is_active": True,
        }

        # 쿠키 설정 (24시간, httpOnly, sameSite)
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=int(self.session_timeout.total_seconds()),
            httponly=True,
            samesite="lax",
        )

        return session_id

    def get_session_id(self, request: Request) -> Optional[str]:
        """요청에서 세션 ID 추출."""
        return request.cookies.get("session_id")

    def get_session_data(self, session_id: str) -> Optional[Dict]:
        """세션 데이터 조회."""
        if not session_id or session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # 세션 만료 확인
        if self._is_session_expired(session):
            self.delete_session(session_id)
            return None

        return session

    def update_session(self, session_id: str, data: Dict):
        """세션 데이터 업데이트."""
        if session_id in self.sessions:
            self.sessions[session_id].update(data)
            self.sessions[session_id]["last_seen"] = datetime.now()

    def update_player_info(self, session_id: str, player: Player):
        """플레이어 정보를 세션에 저장."""
        if session_id in self.sessions:
            self.sessions[session_id]["player_data"] = {
                "nickname": player.nickname,
                "player_number": player.player_number,
            }
            self.sessions[session_id]["last_seen"] = datetime.now()

    def set_room_id(self, session_id: str, room_id: str):
        """세션에 방 ID 설정."""
        if session_id in self.sessions:
            self.sessions[session_id]["room_id"] = room_id
            self.sessions[session_id]["last_seen"] = datetime.now()

    def get_room_id(self, session_id: str) -> Optional[str]:
        """세션에서 방 ID 조회."""
        session = self.get_session_data(session_id)
        return session.get("room_id") if session else None

    def delete_session(self, session_id: str):
        """세션 삭제."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def cleanup_expired_sessions(self):
        """만료된 세션들 정리."""
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.delete_session(session_id)

    def _is_session_expired(self, session: Dict) -> bool:
        """세션 만료 여부 확인."""
        last_seen = session.get("last_seen", session.get("created_at"))
        if not last_seen:
            return True

        return datetime.now() - last_seen > self.session_timeout

    def get_active_sessions_count(self) -> int:
        """활성 세션 수 조회."""
        self.cleanup_expired_sessions()
        return len(self.sessions)

    def find_session_by_room(self, room_id: str) -> Optional[str]:
        """방 ID로 세션 찾기."""
        for session_id, session in self.sessions.items():
            if session.get("room_id") == room_id:
                session_data = self.get_session_data(session_id)
                if session_data:  # 만료되지 않은 세션만 반환
                    return session_id
        return None


# 전역 세션 매니저 인스턴스
session_manager = SessionManager()
