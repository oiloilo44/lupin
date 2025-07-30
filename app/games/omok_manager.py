import random
from typing import Dict
from .base import BaseGameManager
from ..models import Room, GameType


class OmokManager(BaseGameManager):
    """오목 게임 매니저"""
    
    def get_game_type(self) -> GameType:
        return GameType.OMOK
    
    def get_initial_state(self) -> Dict:
        return {
            "board": [[0 for _ in range(15)] for _ in range(15)],
            "current_player": 1
        }
    
    def get_max_players(self) -> int:
        return 2
    
    def reset_game(self, room: Room):
        """오목 게임 재시작"""
        # 게임 횟수 증가
        room.games_played += 1
        
        # 색상 재배정
        self.assign_colors(room)
        
        # 게임 상태 리셋
        room.game_ended = False
        room.winner = None
        room.game_state = self.get_initial_state()
        room.move_history = []
        room.undo_requests = {}
    
    def assign_colors(self, room: Room):
        """오목 플레이어 색상 배정"""
        if len(room.players) != 2:
            return
            
        if room.games_played == 0:
            # 첫 게임은 랜덤 배정
            colors = [1, 2]  # 1: 흑돌, 2: 백돌
            random.shuffle(colors)
            room.players[0].color = colors[0]
            room.players[1].color = colors[1]
        else:
            # 이후 게임은 패자가 흑돌(유리한 색상)
            if room.last_winner:
                for player in room.players:
                    if player.player_number == room.last_winner:
                        player.color = 2  # 승자는 백돌
                    else:
                        player.color = 1  # 패자는 흑돌