import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket

from .models import Room, GameType, GameStatus, OmokGameState


class RoomManager:
    """방 관리 시스템"""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    def create_omok_room(self) -> tuple[str, str]:
        """오목 방 생성"""
        room_id = str(uuid.uuid4())[:8]
        
        room = Room(
            room_id=room_id,
            game_type=GameType.OMOK,
            players=[],
            game_state={
                "board": [[0 for _ in range(15)] for _ in range(15)],
                "current_player": 1
            },
            status=GameStatus.WAITING
        )
        
        self.rooms[room_id] = room
        self.connections[room_id] = set()
        
        return room_id, f"/omok/{room_id}"
    
    def create_janggi_room(self) -> tuple[str, str]:
        """장기 방 생성"""
        room_id = str(uuid.uuid4())[:8]
        
        room = Room(
            room_id=room_id,
            game_type=GameType.JANGGI,
            players=[],
            game_state={
                "board": None,
                "current_player": "red"
            },
            status=GameStatus.WAITING
        )
        
        self.rooms[room_id] = room
        self.connections[room_id] = set()
        
        return room_id, f"/janggi/{room_id}"
    
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
    
    def reset_omok_game(self, room_id: str):
        """오목 게임 재시작"""
        room = self.rooms.get(room_id)
        if room and room.game_type == GameType.OMOK:
            room.game_ended = False
            room.winner = None
            room.game_state = {
                "board": [[0 for _ in range(15)] for _ in range(15)],
                "current_player": 1
            }
            room.move_history = []
            room.undo_requests = {}


# 전역 방관리자 인스턴스
room_manager = RoomManager()