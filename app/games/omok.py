from typing import List, Optional

from ..models import GameMove, MoveHistoryEntry, OmokGameState

# 오목 게임 상수
BOARD_SIZE = 15
FIRST_PLAYER = 1
SECOND_PLAYER = 2
WINNING_COUNT = 5


class OmokGame:
    """오목 게임 로직."""

    @staticmethod
    def create_initial_state() -> OmokGameState:
        """초기 게임 상태 생성."""
        return OmokGameState(
            board=[[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)],
            current_player=FIRST_PLAYER,
        )

    @staticmethod
    def is_valid_move(board: List[List[int]], x: int, y: int) -> bool:
        """유효한 수인지 확인."""
        if not (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE):
            return False
        return board[y][x] == 0

    @staticmethod
    def make_move(game_state: OmokGameState, x: int, y: int, player: int) -> bool:
        """수를 둠."""
        if not OmokGame.is_valid_move(game_state.board, x, y):
            return False

        game_state.board[y][x] = player
        game_state.current_player = (
            SECOND_PLAYER if player == FIRST_PLAYER else FIRST_PLAYER
        )
        return True

    @staticmethod
    def check_win(
        board: List[List[int]], x: int, y: int, player: int
    ) -> Optional[List[dict]]:
        """승리 조건 확인 - 승리 라인 반환."""
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dx, dy in directions:
            count = 1
            win_line = [{"x": x, "y": y}]

            # 한 방향으로 확인
            for i in range(1, WINNING_COUNT):
                nx, ny = x + dx * i, y + dy * i
                if (
                    0 <= nx < BOARD_SIZE
                    and 0 <= ny < BOARD_SIZE
                    and board[ny][nx] == player
                ):
                    count += 1
                    win_line.append({"x": nx, "y": ny})
                else:
                    break

            # 반대 방향으로 확인
            for i in range(1, WINNING_COUNT):
                nx, ny = x - dx * i, y - dy * i
                if (
                    0 <= nx < BOARD_SIZE
                    and 0 <= ny < BOARD_SIZE
                    and board[ny][nx] == player
                ):
                    count += 1
                    win_line.insert(0, {"x": nx, "y": ny})
                else:
                    break

            if count == WINNING_COUNT:
                return win_line  # 정확히 5개만 반환

        return None

    @staticmethod
    def create_move_history_entry(
        move: GameMove, board_state: List[List[int]], player: int
    ) -> MoveHistoryEntry:
        """이동 기록 엔트리 생성."""
        return MoveHistoryEntry(
            move=move,
            board_state=[row[:] for row in board_state],  # 깊은 복사
            player=player,
        )

    @staticmethod
    def undo_last_move(
        game_state: OmokGameState, move_history: List[MoveHistoryEntry]
    ) -> bool:
        """마지막 수 되돌리기."""
        if not move_history:
            return False

        # 무를 수의 플레이어 저장
        undone_move_player = move_history[-1].player
        move_history.pop()  # 마지막 이동 제거

        if move_history:
            # 이전 보드 상태로 복원
            prev_state = move_history[-1]
            game_state.board = [row[:] for row in prev_state.board_state]
            # 턴은 무른 수를 둔 플레이어에게 다시 부여 (재기회)
            game_state.current_player = undone_move_player
        else:
            # 처음 상태로 복원 (첫 수를 무른 경우)
            game_state.board = [
                [0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
            ]
            game_state.current_player = FIRST_PLAYER

        return True

    @staticmethod
    def count_stones(board: List[List[int]]) -> int:
        """보드의 총 돌 개수 계산."""
        count = 0
        for row in board:
            for cell in row:
                if cell != 0:
                    count += 1
        return count
