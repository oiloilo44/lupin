"""WebSocket 연결 관리 전담 클래스"""

from typing import Dict, List, Optional, Set
from fastapi import WebSocket

from ..models import Player, Room
from ..utils.player_utils import find_player_by_session_or_number


class ConnectionManager:
    """WebSocket 연결 관리 전담
    
    단일 책임: WebSocket 연결의 생성, 제거, 상태 관리
    """
    
    def __init__(self) -> None:
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    def add_connection(self, room_id: str, websocket: WebSocket) -> None:
        """WebSocket 연결 추가
        
        Args:
            room_id: 방 ID
            websocket: 추가할 WebSocket 연결
        """
        if room_id not in self.connections:
            self.connections[room_id] = set()
        self.connections[room_id].add(websocket)
    
    def remove_connection(self, room_id: str, websocket: WebSocket) -> None:
        """WebSocket 연결 제거
        
        Args:
            room_id: 방 ID  
            websocket: 제거할 WebSocket 연결
        """
        if room_id in self.connections:
            self.connections[room_id].discard(websocket)
    
    def get_connections(self, room_id: str) -> Set[WebSocket]:
        """방의 모든 WebSocket 연결 반환
        
        Args:
            room_id: 방 ID
            
        Returns:
            WebSocket 연결들의 집합
        """
        return self.connections.get(room_id, set())
    
    def has_connections(self, room_id: str) -> bool:
        """방에 활성 연결이 있는지 확인
        
        Args:
            room_id: 방 ID
            
        Returns:
            연결 존재 여부
        """
        return bool(self.connections.get(room_id))
    
    def get_connection_count(self, room_id: str) -> int:
        """방의 연결 수 반환
        
        Args:
            room_id: 방 ID
            
        Returns:
            연결 수
        """
        return len(self.connections.get(room_id, set()))
    
    def remove_room_connections(self, room_id: str) -> None:
        """방의 모든 연결 제거
        
        Args:
            room_id: 방 ID
        """
        if room_id in self.connections:
            del self.connections[room_id]
    
    def update_player_connection_status(
        self, 
        room: Room, 
        player_identifier: str, 
        is_connected: bool
    ) -> bool:
        """플레이어 연결 상태 업데이트
        
        Args:
            room: 방 객체
            player_identifier: 플레이어 식별자 (세션 ID 또는 플레이어 번호)
            is_connected: 연결 상태
            
        Returns:
            업데이트 성공 여부
        """
        player = find_player_by_session_or_number(room, player_identifier)
        if player:
            player.is_connected = is_connected
            return True
        return False
    
    def get_all_connections(self) -> Dict[str, Set[WebSocket]]:
        """모든 연결 정보 반환 (디버깅용)
        
        Returns:
            모든 방의 연결 정보
        """
        return self.connections.copy()
    
    def cleanup_empty_connections(self) -> List[str]:
        """빈 연결 정보 정리
        
        Returns:
            정리된 방 ID 목록
        """
        empty_rooms = [
            room_id for room_id, connections in self.connections.items()
            if not connections
        ]
        
        for room_id in empty_rooms:
            del self.connections[room_id]
        
        return empty_rooms