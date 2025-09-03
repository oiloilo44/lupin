"""리팩토링된 방 관리 시스템 (Facade Pattern)"""

from typing import Dict, List, Optional, Set, Tuple

from fastapi import WebSocket

from .managers.connection_manager import ConnectionManager
from .managers.room_lifecycle_manager import RoomLifecycleManager
from .models import GameType, Player, Room


class RoomManager:
    """방 관리 시스템 (Facade Pattern)

    단일 진입점: 외부에서는 이 클래스만 사용하며, 내부적으로는 전문화된 매니저들에게 위임
    """

    def __init__(self):
        # 전문화된 매니저들
        self.connection_manager = ConnectionManager()
        self.lifecycle_manager = RoomLifecycleManager()

    # === 방 생성 관련 ===
    def create_omok_room(self) -> Tuple[str, str]:
        """오목 방 생성"""
        return self.lifecycle_manager.create_room(GameType.OMOK)

    def create_janggi_room(self) -> Tuple[str, str]:
        """장기 방 생성"""
        return self.lifecycle_manager.create_room(GameType.JANGGI)

    # === 방 조회 관련 ===
    def get_room(self, room_id: str) -> Optional[Room]:
        """방 조회"""
        return self.lifecycle_manager.get_room(room_id)

    def room_exists(self, room_id: str) -> bool:
        """방 존재 여부 확인"""
        return self.lifecycle_manager.room_exists(room_id)

    def get_room_status_info(self, room_id: str) -> Optional[Dict]:
        """방 상태 정보 조회 (재접속 시 사용)"""
        return self.lifecycle_manager.get_room_status_info(room_id)

    # === 연결 관리 관련 ===
    def add_connection(
        self, room_id: str, websocket: WebSocket, session_id: Optional[str] = None
    ) -> None:
        """WebSocket 연결 추가"""
        self.connection_manager.add_connection(room_id, websocket, session_id)

    def remove_connection(
        self, room_id: str, websocket: WebSocket, session_id: Optional[str] = None
    ) -> None:
        """WebSocket 연결 제거"""
        disconnected_session_id = self.connection_manager.remove_connection(
            room_id, websocket
        )

        # 실제 세션 ID 확인 (매개변수 우선)
        actual_session_id = session_id or disconnected_session_id

        # 플레이어 연결 상태 업데이트
        if actual_session_id:
            room = self.lifecycle_manager.get_room(room_id)
            if room:
                self.lifecycle_manager.update_player_connection_status(
                    room_id, actual_session_id, False
                )

                # 방이 비었을 때 타이머 스케줄링
                if not self.connection_manager.has_connections(room_id):
                    self.connection_manager.handle_room_empty(
                        room_id, room, self._cleanup_room_callback
                    )

    def get_room_connections(self, room_id: str) -> Set[WebSocket]:
        """방의 모든 연결 조회"""
        return self.connection_manager.get_connections(room_id)

    # === 플레이어 관리 관련 ===
    def add_player_to_room(
        self, room_id: str, nickname: str, session_id: str
    ) -> Optional[Player]:
        """방에 플레이어 추가 (세션 ID 포함)"""
        return self.lifecycle_manager.add_player_to_room(room_id, nickname, session_id)

    def find_player_by_session(self, session_id: str) -> Optional[Tuple[Player, Room]]:
        """세션 ID로 플레이어 찾기 (O(1) 성능)"""
        return self.lifecycle_manager.find_player_by_session(session_id)

    def update_player_connection_status(
        self, room_id: str, player_identifier: str, is_connected: bool
    ) -> None:
        """플레이어 연결 상태 업데이트 (세션 ID 또는 플레이어 번호로)"""
        self.lifecycle_manager.update_player_connection_status(
            room_id, player_identifier, is_connected
        )

    def get_disconnected_players(self, room_id: str) -> List[Player]:
        """연결이 끊긴 플레이어 목록 조회"""
        return self.lifecycle_manager.get_disconnected_players(room_id)

    # === 세션 관리 관련 ===
    def get_session_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        """WebSocket으로 세션 ID 조회"""
        return self.connection_manager.get_session_id_by_websocket(websocket)

    # === 재접속 처리 ===
    def handle_reconnection(
        self, room_id: str, session_id: str, websocket: WebSocket
    ) -> bool:
        """재접속 처리"""
        # 타이머 취소
        self.connection_manager.cancel_room_timer(room_id)

        # 재접속 처리
        self.connection_manager.handle_reconnection(room_id, websocket, session_id)

        # 플레이어 연결 상태 업데이트
        self.lifecycle_manager.update_player_connection_status(
            room_id, session_id, True
        )

        return True

    def is_room_waiting_for_reconnection(self, room_id: str) -> bool:
        """방이 재접속 대기 중인지 확인"""
        return self.connection_manager.is_room_waiting_for_reconnection(
            room_id
        ) or self.lifecycle_manager.is_room_waiting_for_reconnection(room_id)

    # === 게임 관리 관련 ===
    def reset_omok_game(self, room_id: str) -> None:
        """오목 게임 재시작"""
        self.lifecycle_manager.reset_game(room_id)

    def get_game_manager(self, game_type: GameType):
        """게임 타입별 매니저 반환"""
        return self.lifecycle_manager.get_game_manager(game_type)

    # === 정리 관련 ===
    def cleanup_expired_rooms(self) -> None:
        """만료된 방들 정리 (수동 호출용)"""
        expired_rooms = self.lifecycle_manager.cleanup_expired_rooms()

        # 연결 정보도 정리
        for room_id in expired_rooms:
            self.connection_manager.cleanup_room_connections(room_id)

    def _cleanup_room_callback(self, room_id: str) -> None:
        """방 정리 실행 (콜백용)"""
        room = self.lifecycle_manager.get_room(room_id)
        if not room:
            return

        # 모든 플레이어가 연결 해제된 상태인지 확인
        all_disconnected = all(not player.is_connected for player in room.players)

        # 연결이 없고 모든 플레이어가 연결 해제된 경우에만 방 삭제
        if not self.connection_manager.has_connections(room_id) and all_disconnected:
            self.connection_manager.cleanup_room_connections(room_id)
            self.lifecycle_manager.delete_room(room_id)

    # === 디버깅/모니터링 관련 ===
    def get_all_rooms(self) -> Dict[str, Room]:
        """모든 방 정보 반환 (디버깅용)"""
        return self.lifecycle_manager.get_all_rooms()

    def get_room_count(self) -> int:
        """전체 방 개수 반환"""
        return self.lifecycle_manager.get_room_count()

    def get_player_count(self) -> int:
        """전체 플레이어 수 반환"""
        return self.lifecycle_manager.get_player_count()


# 전역 방관리자 인스턴스
room_manager = RoomManager()
