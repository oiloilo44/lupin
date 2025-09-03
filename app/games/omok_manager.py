import random
from typing import Dict, List, Optional, Tuple

from ..models import GameMove, GameType, OmokGameState, Player, Room
from .base import BaseGameManager
from .omok import OmokGame


class OmokManager(BaseGameManager):
    """오목 게임 매니저."""

    def get_game_type(self) -> GameType:
        return GameType.OMOK

    def get_initial_state(self) -> Dict:
        return {
            "board": [[0 for _ in range(15)] for _ in range(15)],
            "current_player": 1,
        }

    def get_max_players(self) -> int:
        return 2

    def reset_game(self, room: Room):
        """오목 게임 재시작."""
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
        """오목 플레이어 색상 배정."""
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

    def validate_move(
        self, room: Room, player: Player, x: int, y: int
    ) -> Tuple[bool, str]:
        """이동 유효성 검증."""
        # 게임 종료 확인
        if room.game_ended:
            return False, "게임이 이미 종료되었습니다."

        # 게임 상태를 OmokGameState로 타입 안전하게 변환
        game_state = self._get_omok_game_state(room)

        # 플레이어 턴 확인
        if player.color != game_state.current_player:
            return False, "당신의 턴이 아닙니다."

        # 좌표 범위 확인
        if not (0 <= x < 15 and 0 <= y < 15):
            return False, "유효하지 않은 좌표입니다."

        # 빈 위치 확인
        if not OmokGame.is_valid_move(game_state.board, x, y):
            return False, "해당 위치에 돌을 놓을 수 없습니다."

        return True, ""

    def make_move(
        self, room: Room, player: Player, x: int, y: int
    ) -> Tuple[bool, Optional[List[dict]], str]:
        """이동 실행 및 승리 조건 확인

        Returns:
            (성공 여부, 승리 라인 또는 None, 에러 메시지)
        """
        # 이동 유효성 검증
        is_valid, error_msg = self.validate_move(room, player, x, y)
        if not is_valid:
            return False, None, error_msg

        # 게임 상태를 OmokGameState로 변환
        game_state = self._get_omok_game_state(room)

        # player.color가 None이면 에러
        if player.color is None:
            return False, None, "플레이어 색상이 설정되지 않았습니다."

        # 돌 놓기
        game_state.board[y][x] = player.color

        # 이동 기록 저장
        move = GameMove(x=x, y=y, player=player.color)
        history_entry = OmokGame.create_move_history_entry(
            move=move, board_state=game_state.board, player=player.color
        )
        room.move_history.append(history_entry)

        # 승리 조건 확인
        winning_line = OmokGame.check_win(game_state.board, x, y, player.color)
        if winning_line:
            # 게임 종료 처리
            room.game_ended = True
            room.winner = player.player_number
            room.last_winner = player.player_number
            # 게임 상태를 다시 Dict로 저장
            self._set_omok_game_state(room, game_state)
            return True, winning_line, ""

        # 턴 변경
        game_state.current_player = 2 if player.color == 1 else 1

        # 게임 상태를 다시 Dict로 저장
        self._set_omok_game_state(room, game_state)

        return True, None, ""

    def _get_omok_game_state(self, room: Room) -> OmokGameState:
        """Room의 game_state Dict를 OmokGameState로 변환."""
        return OmokGameState(
            board=room.game_state["board"],
            current_player=room.game_state["current_player"],
        )

    def _set_omok_game_state(self, room: Room, game_state: OmokGameState) -> None:
        """OmokGameState를 Room의 game_state Dict로 저장."""
        room.game_state = {
            "board": game_state.board,
            "current_player": game_state.current_player,
        }
