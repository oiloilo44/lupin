"""방 생명주기 관리 전담 클래스"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import RoomFullError, RoomNotFoundError
from ..games.game_factory import GameManagerFactory
from ..models import GameStatus, GameType, Player, Room
from ..utils.player_utils import (
    find_player_by_session,
    get_disconnected_players as get_disconnected_players_util,
)


class RoomLifecycleManager:
    """방 생성, 삭제, 정리 전담
    
    단일 책임: 방의 생명주기 관리 (생성, 삭제, 만료 처리)
    """
    
    def __init__(self) -> None:
        self.rooms: Dict[str, Room] = {}
    
    def create_room(self, game_type: GameType) -> Tuple[str, str]:
        """게임 방 생성
        
        Args:
            game_type: 생성할 게임 타입
            
        Returns:
            (방 ID, URL 경로) 튜플
        """
        room_id = str(uuid.uuid4())[:8]
        
        # 팩토리를 통해 게임 매니저를 가져오고 초기 상태 생성
        game_manager = GameManagerFactory.get_manager(game_type)
        initial_state = game_manager.get_initial_state()
        url_path = game_manager.get_url_path(room_id)
        
        room = Room(
            room_id=room_id,
            game_type=game_type,
            status=GameStatus.WAITING,
            players=[],
            game_state=initial_state,
        )
        self.rooms[room_id] = room
        return room_id, url_path
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """방 조회
        
        Args:
            room_id: 방 ID
            
        Returns:
            방 객체 또는 None
        """
        return self.rooms.get(room_id)
    
    def room_exists(self, room_id: str) -> bool:
        """방 존재 여부 확인
        
        Args:
            room_id: 방 ID
            
        Returns:
            존재 여부
        """
        return room_id in self.rooms
    
    def delete_room(self, room_id: str) -> bool:
        """방 삭제
        
        Args:
            room_id: 삭제할 방 ID
            
        Returns:
            삭제 성공 여부
        """
        if room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False
    
    def add_player_to_room(
        self, 
        room_id: str, 
        player: Player
    ) -> None:
        """방에 플레이어 추가
        
        Args:
            room_id: 방 ID
            player: 추가할 플레이어
            
        Raises:
            RoomNotFoundError: 방을 찾을 수 없는 경우
            RoomFullError: 방이 가득 찬 경우
        """
        room = self.rooms.get(room_id)
        if not room:
            raise RoomNotFoundError(room_id)
        
        # 게임 매니저를 통해 최대 플레이어 수 확인
        game_manager = GameManagerFactory.get_manager(room.game_type)
        max_players = game_manager.get_max_players()
        
        if len(room.players) >= max_players:
            raise RoomFullError(room_id, max_players)
        
        # 플레이어 번호 할당
        existing_numbers = {p.player_number for p in room.players}
        for i in range(1, max_players + 1):
            if i not in existing_numbers:
                player.player_number = i
                break
        
        room.players.append(player)
        
        # 게임 시작 조건 확인
        if len(room.players) >= max_players:
            room.status = GameStatus.PLAYING
    
    def remove_player_from_room(
        self, 
        room_id: str, 
        session_id: str
    ) -> Optional[Player]:
        """방에서 플레이어 제거
        
        Args:
            room_id: 방 ID
            session_id: 플레이어 세션 ID
            
        Returns:
            제거된 플레이어 또는 None
        """
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        player_info = find_player_by_session(self.rooms, session_id)
        if not player_info:
            return None
        
        player, found_room = player_info
        if found_room.room_id != room_id:
            return None
        
        room.players.remove(player)
        
        # 방 상태 업데이트
        if not room.players:
            room.status = GameStatus.WAITING
        elif len(room.players) < 2 and room.status == GameStatus.PLAYING:
            room.status = GameStatus.WAITING
        
        return player
    
    def reset_room_game(self, room_id: str) -> bool:
        """방의 게임 재시작
        
        Args:
            room_id: 방 ID
            
        Returns:
            재시작 성공 여부
        """
        room = self.rooms.get(room_id)
        if not room:
            return False
        
        # 팩토리를 통해 게임 매니저를 가져와서 재시작 처리
        game_manager = GameManagerFactory.get_manager(room.game_type)
        game_manager.reset_game(room)
        return True
    
    def get_room_status_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """방 상태 정보 반환
        
        Args:
            room_id: 방 ID
            
        Returns:
            방 상태 정보 딕셔너리 또는 None
        """
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        disconnected_players = get_disconnected_players_util(room)
        
        return {
            "room_id": room.room_id,
            "game_type": room.game_type.value,
            "status": room.status.value,
            "player_count": len(room.players),
            "disconnected_count": len(disconnected_players),
            "game_ended": room.game_ended,
            "winner": room.winner,
            "games_played": room.games_played,
        }
    
    def cleanup_expired_rooms(self, max_age_hours: int = 24) -> List[str]:
        """만료된 방들 정리
        
        Args:
            max_age_hours: 최대 보관 시간 (시간)
            
        Returns:
            정리된 방 ID 목록
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_rooms = []
        
        for room_id, room in list(self.rooms.items()):
            # 방이 비어있고 오래된 경우
            if not room.players:
                # 간단한 만료 기준: 게임이 끝났거나 대기 상태가 오래 지속된 경우
                if room.status == GameStatus.ENDED or (
                    room.status == GameStatus.WAITING and room.games_played == 0
                ):
                    expired_rooms.append(room_id)
                    del self.rooms[room_id]
        
        return expired_rooms
    
    def get_all_rooms(self) -> Dict[str, Room]:
        """모든 방 정보 반환 (디버깅용)
        
        Returns:
            모든 방 정보
        """
        return self.rooms.copy()
    
    def get_room_count(self) -> int:
        """전체 방 개수 반환
        
        Returns:
            방 개수
        """
        return len(self.rooms)