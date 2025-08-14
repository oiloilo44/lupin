from typing import Dict

from ..models import GameType, Room
from .base import BaseGameManager


class JanggiManager(BaseGameManager):
    """장기 게임 매니저 (플레이스홀더)"""

    def get_game_type(self) -> GameType:
        return GameType.JANGGI

    def get_initial_state(self) -> Dict:
        return {"board": None, "current_player": "red"}

    def get_max_players(self) -> int:
        return 2

    def reset_game(self, room: Room):
        """장기 게임 재시작 (향후 구현)"""
        room.game_ended = False
        room.winner = None
        room.game_state = self.get_initial_state()
        room.move_history = []
        room.undo_requests = {}
