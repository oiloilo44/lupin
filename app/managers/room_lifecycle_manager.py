"""방 생명주기 관리 전담 클래스"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..games.janggi_manager import JanggiManager
from ..games.omok_manager import OmokManager
from ..models import GameStatus, GameType, Player, Room
from ..utils.room_timer import RoomTimer


class RoomLifecycleManager:
    """방 생성, 삭제, 플레이어 관리 전담

    단일 책임: 방의 생명주기 관리 (생성, 플레이어 추가/제거, 상태 관리)
    """

    def __init__(self):
        # 방 저장소
        self.rooms: Dict[str, Room] = {}
        # 세션-방 매핑 (빠른 조회용)
        self.session_to_room: Dict[str, str] = {}

        # 게임별 매니저 인스턴스
        self.omok_manager = OmokManager()
        self.janggi_manager = JanggiManager()

        # 방 정리 타이머 관리
        self.room_timer = RoomTimer()

    def create_room(self, game_type: GameType) -> Tuple[str, str]:
        """게임 방 생성

        Args:
            game_type: 생성할 게임 타입

        Returns:
            (방 ID, URL 경로) 튜플
        """
        room_id = str(uuid.uuid4())[:8]

        # 게임 타입별 방 생성
        if game_type == GameType.OMOK:
            room = self.omok_manager.create_room(room_id)
            url_path = self.omok_manager.get_url_path(room_id)
        elif game_type == GameType.JANGGI:
            room = self.janggi_manager.create_room(room_id)
            url_path = self.janggi_manager.get_url_path(room_id)
        else:
            raise ValueError(f"지원하지 않는 게임 타입: {game_type}")

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

    def add_player_to_room(
        self, room_id: str, nickname: str, session_id: str
    ) -> Optional[Player]:
        """방에 플레이어 추가 (세션 ID 포함)

        Args:
            room_id: 방 ID
            nickname: 플레이어 닉네임
            session_id: 세션 ID

        Returns:
            추가된 플레이어 객체 또는 None
        """
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
            is_connected=True,
        )
        room.players.append(player)

        # session_to_room 매핑 추가
        self.session_to_room[session_id] = room_id

        # 게임 시작 조건 확인 (2명이 모이면 게임 시작)
        if len(room.players) == 2:
            room.status = GameStatus.PLAYING
            # 두 번째 플레이어 참여 시 색상 배정
            if room.game_type == GameType.OMOK:
                self.omok_manager.assign_colors(room)
            elif room.game_type == GameType.JANGGI:
                self.janggi_manager.assign_colors(room)

        return player

    def remove_player_from_room(
        self, room_id: str, session_id: str
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

        removed_player = None
        for player in room.players:
            if player.session_id == session_id:
                removed_player = player
                room.players.remove(player)
                break

        if removed_player:
            # session_to_room 매핑 제거
            if session_id in self.session_to_room:
                del self.session_to_room[session_id]

            # 방 상태 업데이트
            if not room.players:
                room.status = GameStatus.WAITING
            elif len(room.players) < 2 and room.status == GameStatus.PLAYING:
                room.status = GameStatus.WAITING

        return removed_player

    def find_player_by_session(self, session_id: str) -> Optional[Tuple[Player, Room]]:
        """세션 ID로 플레이어 찾기 (O(1) 성능)

        Args:
            session_id: 세션 ID

        Returns:
            (플레이어, 방) 튜플 또는 None
        """
        # 먼저 session_to_room 매핑으로 빠르게 조회
        room_id = self.session_to_room.get(session_id)
        if room_id:
            room = self.rooms.get(room_id)
            if room:
                for player in room.players:
                    if player.session_id == session_id:
                        return player, room

        # 매핑이 없으면 전체 탐색 (failsafe)
        for room_id, room in self.rooms.items():
            for player in room.players:
                if player.session_id == session_id:
                    # 찾았으면 매핑 업데이트
                    self.session_to_room[session_id] = room_id
                    return player, room

        return None

    def get_room_status_info(self, room_id: str) -> Optional[Dict]:
        """방 상태 정보 조회 (재접속 시 사용)

        Args:
            room_id: 방 ID

        Returns:
            방 상태 정보 딕셔너리 또는 None
        """
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
                    "last_seen": (
                        player.last_seen.isoformat() if player.last_seen else None
                    ),
                }
                for player in room.players
            ],
            "game_state": room.game_state,
            "game_ended": room.game_ended,
            "winner": room.winner,
        }

    def get_disconnected_players(self, room_id: str) -> List[Player]:
        """연결이 끊긴 플레이어 목록 조회

        Args:
            room_id: 방 ID

        Returns:
            연결이 끊긴 플레이어 목록
        """
        room = self.rooms.get(room_id)
        if not room:
            return []

        return [player for player in room.players if not player.is_connected]

    def update_player_connection_status(
        self, room_id: str, player_identifier: str, is_connected: bool
    ) -> bool:
        """플레이어 연결 상태 업데이트

        Args:
            room_id: 방 ID
            player_identifier: 플레이어 식별자 (세션 ID 또는 플레이어 번호)
            is_connected: 연결 상태

        Returns:
            업데이트 성공 여부
        """
        room = self.rooms.get(room_id)
        if not room:
            return False

        # 플레이어 번호로 찾기 시도
        try:
            player_number = int(player_identifier)
            for player in room.players:
                if player.player_number == player_number:
                    player.is_connected = is_connected
                    player.last_seen = datetime.now()
                    return True
        except ValueError:
            pass

        # 세션 ID로 찾기
        for player in room.players:
            if player.session_id == player_identifier:
                player.is_connected = is_connected
                player.last_seen = datetime.now()
                return True

        return False

    def reset_game(self, room_id: str) -> bool:
        """게임 재시작

        Args:
            room_id: 방 ID

        Returns:
            재시작 성공 여부
        """
        room = self.rooms.get(room_id)
        if not room:
            return False

        if room.game_type == GameType.OMOK:
            self.omok_manager.reset_game(room)
        elif room.game_type == GameType.JANGGI:
            # 장기 재시작 로직 (미구현)
            pass

        return True

    def delete_room(self, room_id: str) -> bool:
        """방 삭제

        Args:
            room_id: 삭제할 방 ID

        Returns:
            삭제 성공 여부
        """
        if room_id not in self.rooms:
            return False

        room = self.rooms[room_id]

        # session_to_room 매핑 정리
        for player in room.players:
            if player.session_id in self.session_to_room:
                del self.session_to_room[player.session_id]

        # 방 삭제
        del self.rooms[room_id]
        return True

    def cleanup_expired_rooms(self, max_inactive_minutes: int = 30) -> List[str]:
        """만료된 방들 정리

        Args:
            max_inactive_minutes: 최대 비활성 시간 (분)

        Returns:
            삭제된 방 ID 목록
        """
        current_time = datetime.now()
        rooms_to_delete = []

        for room_id, room in self.rooms.items():
            # 모든 플레이어가 지정 시간 이상 비활성 상태인 경우
            if room.players:
                all_expired = True
                for player in room.players:
                    if player.last_seen and (
                        current_time - player.last_seen
                    ).total_seconds() < (max_inactive_minutes * 60):
                        all_expired = False
                        break

                if all_expired:
                    rooms_to_delete.append(room_id)
            # 플레이어가 없는 빈 방인 경우
            elif room.status == GameStatus.WAITING:
                rooms_to_delete.append(room_id)

        # 만료된 방들 삭제
        for room_id in rooms_to_delete:
            self.delete_room(room_id)

        return rooms_to_delete

    def get_game_manager(self, game_type: GameType):
        """게임 타입별 매니저 반환

        Args:
            game_type: 게임 타입

        Returns:
            게임 매니저 인스턴스
        """
        if game_type == GameType.OMOK:
            return self.omok_manager
        elif game_type == GameType.JANGGI:
            return self.janggi_manager
        else:
            raise ValueError(f"지원하지 않는 게임 타입: {game_type}")

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

    def get_player_count(self) -> int:
        """전체 플레이어 수 반환

        Returns:
            플레이어 수
        """
        total = 0
        for room in self.rooms.values():
            total += len(room.players)
        return total

    def schedule_room_cleanup_after_empty(
        self, room_id: str, cleanup_callback, delay_minutes: int = 30
    ) -> None:
        """방이 비었을 때 정리 타이머 스케줄링

        Args:
            room_id: 방 ID
            cleanup_callback: 정리 작업 콜백 함수
            delay_minutes: 지연 시간 (분)
        """
        room = self.rooms.get(room_id)
        if room and room.status.value in ["playing", "waiting"] and room.players:
            self.room_timer.schedule_room_cleanup(
                room_id, cleanup_callback, delay_minutes
            )

    def cancel_room_timer(self, room_id: str) -> bool:
        """방 타이머 취소

        Args:
            room_id: 방 ID

        Returns:
            취소 성공 여부
        """
        return self.room_timer.cancel_timer(room_id)

    def is_room_waiting_for_reconnection(self, room_id: str) -> bool:
        """방이 재접속 대기 중인지 확인

        Args:
            room_id: 방 ID

        Returns:
            재접속 대기 여부
        """
        return self.room_timer.has_timer(room_id)
