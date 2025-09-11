"""
오목 E2E 테스트용 상태 헬퍼 클래스

클라이언트의 JavaScript 객체에 직접 접근하여 게임의 현재 상태를 정확히 파악합니다.
실제 확인된 window.omokClient 구조를 기반으로 구현되었습니다.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import Page


class StateHelper:
    """클라이언트의 실시간 게임 상태 조회를 담당하는 헬퍼 클래스"""

    @staticmethod
    async def get_game_state(page: Page) -> Optional[Dict[str, Any]]:
        """클라이언트의 실시간 게임 상태 객체를 반환합니다.

        Returns:
            게임 상태 딕셔너리 또는 None (omokClient가 없는 경우)
        """
        return await page.evaluate(
            "window.omokClient ? window.omokClient.state.gameState : null"
        )

    @staticmethod
    async def get_my_color(page: Page) -> Optional[int]:
        """현재 플레이어의 돌 색상을 반환합니다.

        실제 확인된 JavaScript 구조:
        - window.omokClient.state.players: 플레이어 목록
        - window.omokClient.state.myPlayerNumber: 내 플레이어 번호
        - player.color: 1(흑돌), 2(백돌)

        Returns:
            1(흑돌), 2(백돌), 또는 None
        """
        script = """
        const myPlayer = window.omokClient.state.players.find(
            p => p.player_number === window.omokClient.state.myPlayerNumber
        );
        return myPlayer ? myPlayer.color : null;
        """
        return await page.evaluate(script)

    @staticmethod
    async def get_current_turn(page: Page) -> Optional[int]:
        """현재 턴을 확인합니다.

        Returns:
            1(흑돌 턴), 2(백돌 턴), 또는 None
        """
        return await page.evaluate(
            "window.omokClient?.state?.gameState?.current_player"
        )

    @staticmethod
    async def get_board_state(page: Page) -> Optional[List[List[int]]]:
        """보드 상태를 확인합니다.

        보드 구조: board[y][x] 형태의 15x15 배열
        - 0: 빈 공간
        - 1: 흑돌
        - 2: 백돌

        Returns:
            15x15 보드 배열 또는 None
        """
        return await page.evaluate("window.omokClient?.state?.gameState?.board")

    @staticmethod
    async def wait_for_turn_change(
        page: Page, expected_turn: int, timeout: int = 3000
    ) -> bool:
        """턴 변경을 대기합니다.

        기존 conftest.py의 타임아웃 값을 활용하여 안정적인 대기를 제공합니다.

        Args:
            page: Playwright Page 객체
            expected_turn: 기대하는 턴 (1: 흑돌, 2: 백돌)
            timeout: 대기 시간 (밀리초, 기본값: 3000ms)

        Returns:
            True if 턴 변경 성공, False if 타임아웃

        Raises:
            TimeoutError: 대기 시간 초과
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            current_turn = await StateHelper.get_current_turn(page)
            if current_turn == expected_turn:
                return True

            if (asyncio.get_event_loop().time() - start_time) * 1000 > timeout:
                raise TimeoutError(f"턴 변경 대기 시간 초과: 예상 턴 {expected_turn}")

            await asyncio.sleep(0.1)  # 100ms 간격으로 체크

    @staticmethod
    async def get_total_moves_from_dom(page: Page) -> Optional[int]:
        """DOM에서 총 수를 추출합니다.

        JavaScript 접근이 불가능할 때 사용하는 백업 메서드입니다.
        DOM 텍스트에서 "X 총 수" 패턴을 찾아 숫자를 추출합니다.

        Returns:
            총 수 또는 None (패턴을 찾을 수 없는 경우)
        """
        text = await page.inner_text("body")
        match = re.search(r"(\d+)\s*총 수", text)
        return int(match.group(1)) if match else None

    @staticmethod
    async def get_player_info(page: Page) -> Optional[Dict[str, Any]]:
        """현재 플레이어 정보를 반환합니다.

        Returns:
            플레이어 정보 딕셔너리 또는 None
            - nickname: 닉네임
            - player_number: 플레이어 번호
            - color: 돌 색상 (1: 흑돌, 2: 백돌)
        """
        script = """
        const myPlayer = window.omokClient?.state?.players?.find(
            p => p.player_number === window.omokClient.state.myPlayerNumber
        );
        return myPlayer || null;
        """
        return await page.evaluate(script)

    @staticmethod
    async def is_game_started(page: Page) -> bool:
        """게임이 시작되었는지 확인합니다.

        Returns:
            True if 게임 시작됨, False otherwise
        """
        game_state = await StateHelper.get_game_state(page)
        return game_state is not None and "current_player" in game_state
