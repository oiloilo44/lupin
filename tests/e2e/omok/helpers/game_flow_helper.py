"""
게임 플로우 헬퍼 모듈

복잡한 게임 설정 로직을 캡슐화하여 테스트에서 재사용 가능한
게임 시작 및 플레이어 입장 기능을 제공합니다.
"""

from playwright.async_api import BrowserContext, Page

from .action_helper import ActionHelper


class GameFlowHelper:
    """오목 게임 설정 및 플로우 관리 헬퍼 클래스"""

    @staticmethod
    async def setup_game_from_homepage(
        page1: Page, page2: Page, player1_name: str, player2_name: str
    ) -> tuple[Page, Page]:
        """
        기존 dual_pages fixture에서 제공된 페이지들로 오목 게임을 설정합니다.
        (이미 홈페이지에 있는 상태에서 시작)

        Args:
            page1, page2: 기존 dual_pages fixture에서 제공된 분리된 페이지들
            player1_name, player2_name: 플레이어 닉네임

        Returns:
            tuple[Page, Page]: 게임이 시작된 (player1_page, player2_page)
        """
        from tests.conftest import TEST_CONFIG

        # 1. 첫 번째 플레이어 - 방 생성 (이미 홈페이지에 있음)
        # 오목 게임 선택 → 방 만들기
        await ActionHelper.js_click(page1, '.game-card:has-text("오목")')
        await ActionHelper.js_click(page1, '.option-card:has-text("방 만들기")')

        # 방 URL 추출 (두 번째 플레이어가 사용할 URL)
        room_url_element = await page1.wait_for_selector(
            "input[readonly]", timeout=TEST_CONFIG["ui_timeout"]
        )
        room_url = await room_url_element.get_attribute("value")

        # 첫 번째 플레이어 닉네임 입력 및 입장
        await ActionHelper.type_text(page1, "#nicknameInput", player1_name)
        await ActionHelper.js_click(page1, 'button:has-text("게임 입장")')

        # 실제 확인된 플로우: 자동 입장 대기
        await GameFlowHelper.wait_for_auto_entry(page1, TEST_CONFIG["game_timeout"])

        # 2. 두 번째 플레이어 - 방 참여 (기존 분리된 페이지 사용)
        await page2.goto(room_url)

        # 실제 확인된 플로우: E2E 환경에서는 바로 닉네임 입력 화면 표시
        await page2.wait_for_selector(
            'h3:has-text("오목 게임 참여")', timeout=TEST_CONFIG["ui_timeout"]
        )

        # 두 번째 플레이어 닉네임 입력 및 참여
        await ActionHelper.type_text(page2, "#nicknameInput", player2_name)
        await ActionHelper.js_click(page2, 'button:has-text("게임 참여")')

        # 게임 시작 대기 (두 플레이어 모두 입장 완료)
        await page2.wait_for_selector(
            'h4:has-text("현재 턴")', timeout=TEST_CONFIG["game_timeout"]
        )
        await page1.wait_for_selector(
            'h4:has-text("현재 턴")', timeout=TEST_CONFIG["game_timeout"]
        )

        return page1, page2

    @staticmethod
    async def wait_for_auto_entry(page: Page, timeout: int = 10000):
        """
        방 생성자의 자동 입장을 대기합니다.
        "오목 게임 참여" 화면에서 게임방으로 자동 전환될 때까지 대기
        """
        try:
            # 게임방 UI 요소 출현 대기
            await page.wait_for_selector('h4:has-text("플레이어")', timeout=timeout)
        except TimeoutError:
            # 자동 입장 실패 시 수동으로 재시도 로직 추가 가능
            current_url = page.url
            raise Exception(f"자동 입장 실패. 현재 URL: {current_url}")

    @staticmethod
    async def ensure_session_separation(
        context1: BrowserContext, context2: BrowserContext
    ):
        """
        두 브라우저 컨텍스트가 완전히 분리되어 있는지 확인합니다.
        세션 겹침으로 인한 "기존 게임 발견" 화면을 방지
        """
        # 각 컨텍스트의 localStorage 및 sessionStorage 정리
        for context in [context1, context2]:
            page = await context.new_page()
            await page.evaluate("localStorage.clear(); sessionStorage.clear();")
            await page.close()
