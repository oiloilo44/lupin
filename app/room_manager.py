import uuid
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
from datetime import datetime, timedelta
import asyncio

from .models import Room, GameType, GameStatus, OmokGameState, Player


class RoomManager:
    """방 관리 시스템"""
    
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.room_timers: Dict[str, asyncio.Task] = {}  # 방 정리 타이머
    
    def create_omok_room(self) -> tuple[str, str]:
        """오목 방 생성"""
        room_id = str(uuid.uuid4())[:8]
        room = Room(
            room_id=room_id,
            game_type=GameType.OMOK,
            status=GameStatus.WAITING,
            game_state={
                "board": [[0 for _ in range(15)] for _ in range(15)],
                "current_player": 1
            }
        )
        self.rooms[room_id] = room
        return room_id, f"/omok/{room_id}"

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

    def remove_connection(self, room_id: str, websocket: WebSocket, session_id: Optional[str] = None):
        """WebSocket 연결 제거"""
        if room_id in self.connections:
            self.connections[room_id].discard(websocket)
            
            # 세션 ID가 있으면 플레이어 연결 상태 업데이트
            if session_id:
                self.update_player_connection_status(room_id, session_id, False)
            
            room = self.rooms.get(room_id)
            if not room:
                return
                
            # 방에 연결이 없을 때의 처리
            if not self.connections[room_id]:
                # 게임이 진행 중이거나 대기 중인 경우 30분 대기 후 삭제
                if room.status in [GameStatus.PLAYING, GameStatus.WAITING] and room.players:
                    # 기존 타이머가 있으면 취소
                    if room_id in self.room_timers:
                        self.room_timers[room_id].cancel()
                    
                    # 새 타이머 시작
                    self.room_timers[room_id] = asyncio.create_task(
                        self._cleanup_room_after_delay(room_id, 30)
                    )
                else:
                    # 게임이 끝났거나 플레이어가 없으면 즉시 삭제
                    if room_id in self.rooms:
                        del self.rooms[room_id]
                    del self.connections[room_id]

    def get_room_connections(self, room_id: str) -> Set[WebSocket]:
        """방의 모든 연결 조회"""
        return self.connections.get(room_id, set())

    def find_player_by_session(self, session_id: str) -> Optional[tuple[Player, Room]]:
        """세션 ID로 플레이어 찾기"""
        for room_id, room in self.rooms.items():
            for player in room.players:
                if player.session_id == session_id:
                    return player, room
        return None

    def update_player_connection_status(self, room_id: str, player_number_or_session: str, is_connected: bool):
        """플레이어 연결 상태 업데이트 (세션 ID 또는 플레이어 번호로)"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        # 플레이어 번호로 찾기 시도
        try:
            player_number = int(player_number_or_session)
            for player in room.players:
                if player.player_number == player_number:
                    player.is_connected = is_connected
                    player.last_seen = datetime.now()
                    return
        except ValueError:
            pass
        
        # 세션 ID로 찾기
        for player in room.players:
            if player.session_id == player_number_or_session:
                player.is_connected = is_connected
                player.last_seen = datetime.now()
                break

    def update_player_connection_status_old(self, room_id: str, session_id: str, is_connected: bool):
        """플레이어 연결 상태 업데이트 (기존 메서드)"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        for player in room.players:
            if player.session_id == session_id:
                player.is_connected = is_connected
                player.last_seen = datetime.now()
                break

    async def _cleanup_room_after_delay(self, room_id: str, delay_minutes: int = 30):
        """지연 후 방 정리"""
        await asyncio.sleep(delay_minutes * 60)  # 분을 초로 변환
        
        room = self.rooms.get(room_id)
        if not room:
            return
        
        # 모든 플레이어가 연결 해제된 상태인지 확인
        all_disconnected = all(not player.is_connected for player in room.players)
        
        # 연결이 없고 모든 플레이어가 연결 해제된 경우에만 방 삭제
        if room_id in self.connections and not self.connections[room_id] and all_disconnected:
            del self.rooms[room_id]
            del self.connections[room_id]
            
        # 타이머 정리
        if room_id in self.room_timers:
            del self.room_timers[room_id]

    def handle_reconnection(self, room_id: str, session_id: str, websocket: WebSocket):
        """재접속 처리"""
        # 진행 중인 정리 타이머가 있으면 취소
        if room_id in self.room_timers:
            self.room_timers[room_id].cancel()
            del self.room_timers[room_id]
        
        # WebSocket 연결 추가
        self.add_connection(room_id, websocket)
        
        # 플레이어 연결 상태 업데이트
        self.update_player_connection_status(room_id, session_id, True)
        
        return True

    def get_room_status_info(self, room_id: str) -> Optional[Dict]:
        """방 상태 정보 조회 (재접속 시 사용)"""
        room = self.rooms.get(room_id)
        if not room:
            return None
        
        return {
            "room_id": room.room_id,
            "game_type": room.game_type,
            "status": room.status,
            "players": [
                {
                    "nickname": player.nickname,
                    "player_number": player.player_number,
                    "is_connected": player.is_connected,
                    "last_seen": player.last_seen.isoformat() if player.last_seen else None
                }
                for player in room.players
            ],
            "game_state": room.game_state,
            "game_ended": room.game_ended,
            "winner": room.winner
        }

    def add_player_to_room(self, room_id: str, nickname: str, session_id: str) -> Optional[Player]:
        """방에 플레이어 추가 (세션 ID 포함)"""
        room = self.rooms.get(room_id)
        if not room or room.is_full():
            return None
        
        # 기존 플레이어 중 같은 세션 ID가 있는지 확인 (재접속)
        for player in room.players:
            if player.session_id == session_id:
                player.is_connected = True
                player.last_seen = datetime.now()
                return player
        
        # 새 플레이어 추가
        player = Player(
            nickname=nickname,
            player_number=len(room.players) + 1,
            session_id=session_id,
            last_seen=datetime.now(),
            is_connected=True
        )
        room.players.append(player)
        
        if len(room.players) == 2:
            room.status = GameStatus.PLAYING
            # 두 번째 플레이어 참여 시 색상 배정
            self.assign_colors(room)
            
        return player

    def is_room_waiting_for_reconnection(self, room_id: str) -> bool:
        """방이 재접속 대기 중인지 확인"""
        return room_id in self.room_timers

    def get_disconnected_players(self, room_id: str) -> List[Player]:
        """연결이 끊긴 플레이어 목록 조회"""
        room = self.rooms.get(room_id)
        if not room:
            return []
        
        return [player for player in room.players if not player.is_connected]

    def cleanup_expired_rooms(self):
        """만료된 방들 정리 (수동 호출용)"""
        current_time = datetime.now()
        rooms_to_delete = []
        
        for room_id, room in self.rooms.items():
            # 연결이 없고 모든 플레이어가 30분 이상 비활성 상태인 경우
            if (room_id not in self.connections or not self.connections[room_id]):
                all_expired = True
                for player in room.players:
                    if player.last_seen and (current_time - player.last_seen) < timedelta(minutes=30):
                        all_expired = False
                        break
                
                if all_expired and room.players:
                    rooms_to_delete.append(room_id)
        
        # 만료된 방들 삭제
        for room_id in rooms_to_delete:
            if room_id in self.rooms:
                del self.rooms[room_id]
            if room_id in self.connections:
                del self.connections[room_id]
            if room_id in self.room_timers:
                self.room_timers[room_id].cancel()
                del self.room_timers[room_id]

    def assign_colors(self, room: Room):
        """플레이어 색상 배정"""
        if len(room.players) != 2:
            return
        
        # 첫 게임이거나 마지막 승자가 없는 경우
        if room.games_played == 0 or room.last_winner is None:
            room.players[0].color = 1  # 흑돌
            room.players[1].color = 2  # 백돌
        else:
            # 이전 게임 승자가 백돌로 시작
            if room.last_winner == 1:
                room.players[0].color = 2  # 백돌
                room.players[1].color = 1  # 흑돌
            else:
                room.players[0].color = 1  # 흑돌
                room.players[1].color = 2  # 백돌

    def reset_omok_game(self, room_id: str):
        """오목 게임 재시작"""
        room = self.rooms.get(room_id)
        if room and room.game_type == GameType.OMOK:
            room.game_ended = False
            room.winner = None
            room.games_played += 1
            
            # 색상 재배정
            self.assign_colors(room)
            
            room.game_state = {
                "board": [[0 for _ in range(15)] for _ in range(15)],
                "current_player": 1
            }
            room.move_history = []
            room.undo_requests = {}


# 전역 방관리자 인스턴스
room_manager = RoomManager()