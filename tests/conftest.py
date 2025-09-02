"""E2E 테스트 공통 설정"""

import pytest_asyncio
from playwright.async_api import Browser, BrowserContext, async_playwright


@pytest_asyncio.fixture(scope="function")
async def browser():
    """브라우저 인스턴스 (세션당 하나)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(**BROWSER_CONFIG)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def context(browser: Browser):
    """브라우저 컨텍스트 (테스트마다 새로 생성)"""
    context = await browser.new_context(**CONTEXT_CONFIG)
    yield context
    await context.close()


@pytest_asyncio.fixture
async def page(context: BrowserContext):
    """페이지 (테스트마다 새로 생성)"""
    page = await context.new_page()

    # 기본적으로 우리 서버로 이동
    await page.goto(TEST_CONFIG["base_url"])

    yield page
    await page.close()


@pytest_asyncio.fixture
async def dual_pages(browser: Browser):
    """멀티플레이어 테스트를 위한 2개 페이지"""
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


@pytest_asyncio.fixture
async def single_browser_context(browser: Browser):
    """단일 컨텍스트 테스트용 (test_error_handling 등에서 사용)"""
    context = await browser.new_context(**CONTEXT_CONFIG)
    yield context
    await context.close()


# 테스트 설정 (통합된 타임아웃 관리)
TEST_CONFIG = {
    "base_url": "http://localhost:8003",
    # 기본 타임아웃들
    "timeout": 30000,  # 30초 (일반적인 최대 대기)
    "short_timeout": 2000,  # 2초 (짧은 대기)
    "ui_timeout": 5000,  # 5초 (UI 요소 대기)
    "network_timeout": 10000,  # 10초 (네트워크 관련)
    "game_timeout": 60000,  # 60초 (게임 관련)
    # 세분화된 타임아웃들
    "element_wait": 2000,  # 요소 표시 대기
    "network_wait": 5000,  # 네트워크 응답 대기
    "game_action": 3000,  # 게임 액션 처리 대기
    "state_sync": 1500,  # 상태 동기화 대기
    "websocket": 10000,  # WebSocket 연결 대기
    "page_load": 8000,  # 페이지 로딩 대기
    "retry_interval": 500,  # 재시도 간격
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
