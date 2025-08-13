from abc import ABC, abstractmethod
from typing import Dict

from ..models import GameStatus, GameType, Room


class BaseGameManager(ABC):
    """게임별 매니저의 기본 클래스."""

    @abstractmethod
    def get_game_type(self) -> GameType:
        """게임 타입 반환."""
        pass

    @abstractmethod
    def get_initial_state(self) -> Dict:
        """초기 게임 상태 반환."""
        pass

    @abstractmethod
    def get_max_players(self) -> int:
        """최대 플레이어 수 반환."""
        pass

    def create_room(self, room_id: str) -> Room:
        """방 생성 (기본 구현 제공)."""
        return Room(
            room_id=room_id,
            game_type=self.get_game_type(),
            players=[],
            game_state=self.get_initial_state(),
            status=GameStatus.WAITING,
        )

    @abstractmethod
    def reset_game(self, room: Room):
        """게임 재시작 로직."""
        pass

    def assign_colors(self, room: Room):
        """색상 배정 로직 (기본은 빈 구현)."""
        pass

    def get_url_path(self, room_id: str) -> str:
        """게임 URL 경로 반환."""
        return f"/{self.get_game_type().value}/{room_id}"
