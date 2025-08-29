"""E2E 테스트 공통 설정"""
import asyncio

import pytest
import pytest_asyncio
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@pytest_asyncio.fixture(scope="function")
async def browser():
    """브라우저 인스턴스 (세션당 하나)"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # 개발 시에는 브라우저 보이게
            slow_mo=0,  # 액션 간 500ms 지연 (관찰하기 좋음)
            args=["--disable-web-security", "--disable-features=VizDisplayCompositor"],
        )
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def context(browser: Browser):
    """브라우저 컨텍스트 (테스트마다 새로 생성)"""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="ko-KR",
        ignore_https_errors=True,
    )
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
    context1 = await browser.new_context(
        viewport={"width": 1280, "height": 720}, locale="ko-KR"  # 데스크톱 해상도 유지
    )
    context2 = await browser.new_context(
        viewport={"width": 1280, "height": 720}, locale="ko-KR"
    )

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
    "timeout": 30000,  # 30초
    "game_timeout": 60000,  # 게임 관련은 1분
}
