"""WebSocket 연결 관리 전담 클래스"""

from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import WebSocket

from ..models import Room


class ConnectionManager:
    """WebSocket 연결 및 세션 관리 전담

    단일 책임: WebSocket 연결의 생성, 제거, 세션 매핑 관리
    """

    def __init__(self):
        # 방별 WebSocket 연결 관리
        self.connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> session_id 매핑
        self.websocket_sessions: Dict[WebSocket, str] = {}
        # session_id -> room_id 매핑 (빠른 조회용)
        self.session_to_room: Dict[str, str] = {}

    def add_connection(
        self, room_id: str, websocket: WebSocket, session_id: Optional[str] = None
    ) -> None:
        """WebSocket 연결 추가 및 세션 매핑

        Args:
            room_id: 방 ID
            websocket: 추가할 WebSocket 연결
            session_id: 세션 ID (옵션)
        """
        # 방별 연결 집합 초기화
        if room_id not in self.connections:
            self.connections[room_id] = set()

        # WebSocket 연결 추가
        self.connections[room_id].add(websocket)

        # 세션 매핑 저장
        if session_id:
            self.websocket_sessions[websocket] = session_id
            self.session_to_room[session_id] = room_id

    def remove_connection(self, room_id: str, websocket: WebSocket) -> Optional[str]:
        """WebSocket 연결 제거 및 세션 매핑 정리

        Args:
            room_id: 방 ID
            websocket: 제거할 WebSocket 연결

        Returns:
            제거된 연결의 session_id (있는 경우)
        """
        # 연결 제거
        if room_id in self.connections:
            self.connections[room_id].discard(websocket)

            # 빈 연결 집합 정리
            if not self.connections[room_id]:
                del self.connections[room_id]

        # 세션 매핑 정리 및 세션 ID 반환
        disconnected_session_id = None
        if websocket in self.websocket_sessions:
            disconnected_session_id = self.websocket_sessions[websocket]
            del self.websocket_sessions[websocket]

            # session_to_room 매핑에서도 제거
            if disconnected_session_id in self.session_to_room:
                del self.session_to_room[disconnected_session_id]

        return disconnected_session_id

    def get_connections(self, room_id: str) -> Set[WebSocket]:
        """방의 모든 WebSocket 연결 반환

        Args:
            room_id: 방 ID

        Returns:
            WebSocket 연결 집합
        """
        return self.connections.get(room_id, set())

    def get_session_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        """WebSocket으로 세션 ID 조회

        Args:
            websocket: WebSocket 연결

        Returns:
            세션 ID (있는 경우)
        """
        return self.websocket_sessions.get(websocket)

    def get_room_id_by_session(self, session_id: str) -> Optional[str]:
        """세션 ID로 방 ID 조회 (O(1) 성능)

        Args:
            session_id: 세션 ID

        Returns:
            방 ID (있는 경우)
        """
        return self.session_to_room.get(session_id)

    def update_session_room_mapping(self, session_id: str, room_id: str) -> None:
        """세션-방 매핑 업데이트

        Args:
            session_id: 세션 ID
            room_id: 방 ID
        """
        self.session_to_room[session_id] = room_id

    def remove_session_mapping(self, session_id: str) -> None:
        """세션 매핑 제거

        Args:
            session_id: 제거할 세션 ID
        """
        if session_id in self.session_to_room:
            del self.session_to_room[session_id]

    def has_connections(self, room_id: str) -> bool:
        """방에 활성 연결이 있는지 확인

        Args:
            room_id: 방 ID

        Returns:
            연결 존재 여부
        """
        return room_id in self.connections and bool(self.connections[room_id])

    def get_connection_count(self, room_id: str) -> int:
        """방의 연결 수 반환

        Args:
            room_id: 방 ID

        Returns:
            연결 수
        """
        return len(self.connections.get(room_id, set()))

    def cleanup_room_connections(self, room_id: str) -> None:
        """방의 모든 연결 정리

        Args:
            room_id: 방 ID
        """
        # 방의 모든 WebSocket 연결 가져오기
        websockets = self.connections.get(room_id, set()).copy()

        # 각 연결에 대해 세션 매핑 정리
        for websocket in websockets:
            if websocket in self.websocket_sessions:
                session_id = self.websocket_sessions[websocket]
                del self.websocket_sessions[websocket]
                if session_id in self.session_to_room:
                    del self.session_to_room[session_id]

        # 연결 집합 제거
        if room_id in self.connections:
            del self.connections[room_id]

    def update_player_connection_status(
        self, room: Room, session_id: str, is_connected: bool
    ) -> bool:
        """플레이어 연결 상태 업데이트

        Args:
            room: 방 객체
            session_id: 플레이어 세션 ID
            is_connected: 연결 상태

        Returns:
            업데이트 성공 여부
        """
        for player in room.players:
            if player.session_id == session_id:
                player.is_connected = is_connected
                player.last_seen = datetime.now()
                return True
        return False

    def handle_reconnection(
        self, room_id: str, websocket: WebSocket, session_id: str
    ) -> None:
        """재접속 처리

        Args:
            room_id: 방 ID
            websocket: 새 WebSocket 연결
            session_id: 재접속하는 플레이어의 세션 ID
        """
        # 기존 세션의 WebSocket이 있다면 정리
        old_websocket = None
        for ws, sid in self.websocket_sessions.items():
            if sid == session_id:
                old_websocket = ws
                break

        if old_websocket:
            # 기존 WebSocket 연결 제거
            if room_id in self.connections:
                self.connections[room_id].discard(old_websocket)
            if old_websocket in self.websocket_sessions:
                del self.websocket_sessions[old_websocket]

        # 새 연결 추가
        self.add_connection(room_id, websocket, session_id)

    def get_all_connections(self) -> Dict[str, Set[WebSocket]]:
        """모든 연결 정보 반환 (디버깅용)

        Returns:
            모든 방의 연결 정보
        """
        return self.connections.copy()

    def get_session_mappings(self) -> Dict[str, str]:
        """모든 세션-방 매핑 반환 (디버깅용)

        Returns:
            세션-방 매핑 정보
        """
        return self.session_to_room.copy()

    def cleanup_expired_sessions(self, room: Room) -> None:
        """방의 만료된 세션 매핑 정리

        Args:
            room: 방 객체
        """
        # 방에 있는 플레이어들의 세션 ID 수집
        valid_sessions = {player.session_id for player in room.players}

        # session_to_room에서 해당 방의 무효한 세션 제거
        sessions_to_remove = []
        for session_id, rid in self.session_to_room.items():
            if rid == room.room_id and session_id not in valid_sessions:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.session_to_room[session_id]
