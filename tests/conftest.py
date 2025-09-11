"""E2E 테스트 공통 설정"""

import pytest_asyncio
from playwright.async_api import Browser, async_playwright


@pytest_asyncio.fixture(scope="function")
async def browser():
    """브라우저 인스턴스 (세션당 하나)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(**BROWSER_CONFIG)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser):
    """단일 페이지 테스트용"""
    context = await browser.new_context(**CONTEXT_CONFIG)
    page = await context.new_page()
    await page.goto(TEST_CONFIG["base_url"])

    yield page

    await page.close()
    await context.close()


@pytest_asyncio.fixture
async def dual_pages(browser: Browser):
    """멀티플레이어 테스트를 위한 2개 페이지 (세션 분리)"""
    context1 = await browser.new_context(**CONTEXT_CONFIG)
    context2 = await browser.new_context(**CONTEXT_CONFIG)

    page1 = await context1.new_page()
    page2 = await context2.new_page()

    # 두 페이지 모두 홈페이지로 이동
    await page1.goto(TEST_CONFIG["base_url"])
    await page2.goto(TEST_CONFIG["base_url"])

    yield page1, page2

    await page1.close()
    await page2.close()
    await context1.close()
    await context2.close()


# 테스트 설정
TEST_CONFIG = {
    "base_url": "http://localhost:8003",
    # 핵심 타임아웃들 (실제 필요한 것들만)
    "element_wait": 2000,  # UI 요소 표시 대기
    "state_sync": 1500,  # 상태 동기화 대기 (턴 변경 등)
    "game_action": 3000,  # 게임 액션 처리 대기
    "ui_timeout": 5000,  # 페이지 전환 등 UI 대기
    "game_timeout": 10000,  # 게임 시작 등 긴 작업
}

# 브라우저 설정
BROWSER_CONFIG = {
    "headless": True,
    "slow_mo": 0,
    "args": ["--disable-web-security", "--disable-features=VizDisplayCompositor"],
}

CONTEXT_CONFIG = {
    "viewport": {"width": 1280, "height": 720},
    "locale": "ko-KR",
    "ignore_https_errors": True,
}


@pytest_asyncio.fixture
async def omok_game_setup(dual_pages):
    """
    기존 dual_pages를 활용해서 오목 게임을 설정합니다.
    """
    page1, page2 = dual_pages
    from tests.e2e.omok.helpers.game_flow_helper import GameFlowHelper

    # GameFlowHelper를 사용해서 게임 시작까지 진행
    game_page1, game_page2 = await GameFlowHelper.setup_game_from_homepage(
        page1, page2, "TestPlayer1", "TestPlayer2"
    )

    yield game_page1, game_page2
    # cleanup은 기존 dual_pages fixture에서 처리됨
