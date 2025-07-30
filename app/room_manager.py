import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket

from .models import Room, GameType, GameStatus, OmokGameState
from .games.omok_manager import OmokManager
from .games.janggi_manager import JanggiManager


class RoomManager:
    """방 관리 시스템"""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.game_managers = {
            GameType.OMOK: OmokManager(),
            GameType.JANGGI: JanggiManager(),
        }
    
    def create_room(self, game_type: GameType) -> tuple[str, str]:
        """게임 방 생성 (통합 메서드)"""
        room_id = str(uuid.uuid4())[:8]
        
        game_manager = self.game_managers[game_type]
        room = game_manager.create_room(room_id)
        
        self.rooms[room_id] = room
        self.connections[room_id] = set()
        
        return room_id, game_manager.get_url_path(room_id)
    
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """방 조회"""
        return self.rooms.get(room_id)
    
    def room_exists(self, room_id: str) -> bool:
        """방 존재 여부 확인"""
        return room_id in self.rooms
    
    def add_connection(self, room_id: str, websocket: WebSocket):
        """WebSocket 연결 추가"""
        if room_id not in self.connections:
            self.connections[room_id] = set()
        self.connections[room_id].add(websocket)
    
    def remove_connection(self, room_id: str, websocket: WebSocket):
        """WebSocket 연결 제거"""
        if room_id in self.connections:
            self.connections[room_id].discard(websocket)
            
            # 방에 아무도 없으면 방 삭제
            if not self.connections[room_id]:
                if room_id in self.rooms:
                    del self.rooms[room_id]
                del self.connections[room_id]
    
    def get_room_connections(self, room_id: str) -> Set[WebSocket]:
        """방의 모든 연결 조회"""
        return self.connections.get(room_id, set())
    
    def reset_game(self, room_id: str):
        """게임 재시작 (통합 메서드)"""
        room = self.rooms.get(room_id)
        if room:
            game_manager = self.game_managers[room.game_type]
            game_manager.reset_game(room)
    
    def assign_colors(self, room: Room):
        """플레이어 색상 배정 (게임 매니저에 위임)"""
        game_manager = self.game_managers[room.game_type]
        game_manager.assign_colors(room)
    


# 전역 방관리자 인스턴스
room_manager = RoomManager()