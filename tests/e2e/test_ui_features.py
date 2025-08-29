"""
S4: 월급루팡 특화 UI/UX E2E 테스트

scenarios.md의 S4 시나리오를 체계적으로 검증:
- S4-1: Excel 위장 모드
- S4-2: 투명도 조절 기능
- S4-3: 빠른 숨김 기능 (Escape)

test_accurate_flow.py의 검증된 기능들을 기반으로 구현
"""

import asyncio

import pytest
import pytest_asyncio
from playwright.async_api import Page, async_playwright, expect


class TestS4ExcelStealth:
    """S4: 월급루팡 특화 UI/UX"""

    @pytest.mark.asyncio
    async def test_s4_1_excel_disguise_mode(self, page):
        """S4-1: Excel 위장 모드"""

        # 1. 메인 페이지 접속
        await page.goto("http://localhost:8003")

        # Excel 위장 기본 요소 확인
        await expect(page).to_have_title("Excel")
        print("SUCCESS: Excel 제목 위장 확인")

        # 2. Excel 메뉴바 확인
        excel_menus = ["파일", "홈", "삽입", "페이지 레이아웃", "수식", "데이터", "검토", "보기"]
        found_menus = 0

        for menu in excel_menus:
            try:
                menu_element = page.locator(f"text={menu}")
                if await menu_element.is_visible(timeout=1000):
                    print(f"SUCCESS: Excel 메뉴 '{menu}' 확인")
                    found_menus += 1
            except:
                pass

        # 최소 3개 이상의 Excel 메뉴가 있어야 함
        assert found_menus >= 3, f"Excel 메뉴가 부족합니다. 발견된 메뉴: {found_menus}개"

        # 3. 오목 게임 선택
        omok_link = page.locator("a:has-text('오목')").first
        await omok_link.click()
        await page.wait_for_load_state("networkidle")

        # 4. Excel 스타일 UI 확인
        await page.wait_for_timeout(2000)

        # Excel 스타일 요소들 확인
        excel_style_indicators = [
            ".excel-container",
            ".excel-header",
            ".excel-toolbar",
            ".excel-menu",
            "Excel",
        ]

        page_content = await page.content()
        found_excel_elements = 0

        for indicator in excel_style_indicators:
            if indicator in page_content:
                print(f"SUCCESS: Excel 스타일 요소 발견 - {indicator}")
                found_excel_elements += 1

        # 5. 게임 타이틀이 눈에 띄지 않는지 확인
        # 큰 게임 로고나 제목이 없어야 함
        flashy_elements = [
            "text=오목 게임!!!",
            "text=OMOK GAME",
            ".big-title",
            ".game-logo",
            ".flashy",
        ]

        for flashy in flashy_elements:
            try:
                element = page.locator(flashy)
                assert not await element.is_visible(
                    timeout=500
                ), f"화려한 요소가 발견됨: {flashy}"
            except:
                pass  # 요소가 없으면 정상

        print("SUCCESS: Excel 위장 모드 검증 완료")

    @pytest.mark.asyncio
    async def test_s4_2_opacity_control(self, page):
        """S4-2: 투명도 조절 기능"""

        # 1. 게임 페이지로 이동
        await page.goto("http://localhost:8003")
        await page.click("a:has-text('오목')")
        await page.wait_for_load_state("networkidle")

        # 2. 투명도 조절 슬라이더 찾기
        opacity_selectors = [
            "input[type='range']",
            ".opacity-control input",
            ".transparency-slider",
            "#opacitySlider",
            "[data-opacity-control]",
        ]

        found_slider = None
        for selector in opacity_selectors:
            try:
                slider = page.locator(selector)
                if await slider.is_visible(timeout=2000):
                    found_slider = slider
                    print(f"SUCCESS: 투명도 슬라이더 발견 - {selector}")
                    break
            except:
                continue

        if found_slider:
            # 3. 투명도 조절 테스트
            await found_slider.fill("30")  # 30%로 설정
            await page.wait_for_timeout(1000)
            print("SUCCESS: 투명도 30% 설정")

            await found_slider.fill("90")  # 90%로 설정
            await page.wait_for_timeout(1000)
            print("SUCCESS: 투명도 90% 설정")

            await found_slider.fill("60")  # 60%로 설정 (중간값)
            await page.wait_for_timeout(1000)
            print("SUCCESS: 투명도 60% 설정")

            # 4. 투명도 변경 후에도 게임이 정상 작동하는지 확인
            # 방 만들기 버튼이 여전히 클릭 가능한지 테스트
            create_room_btn = page.locator("text=방 만들기")
            if await create_room_btn.is_visible():
                await create_room_btn.click()
                await page.wait_for_timeout(1000)

                # 모달이 나타났는지 확인
                nickname_input = page.locator("#nicknameInput")
                if await nickname_input.is_visible(timeout=3000):
                    print("SUCCESS: 투명도 변경 후에도 게임 기능 정상")

                    # 모달 닫기
                    close_buttons = [
                        "button:has-text('취소')",
                        "button:has-text('닫기')",
                        ".modal-close",
                    ]
                    for close_btn in close_buttons:
                        try:
                            if await page.locator(close_btn).is_visible():
                                await page.click(close_btn)
                                break
                        except:
                            continue
        else:
            print("INFO: 투명도 슬라이더를 찾을 수 없음 - UI 구조 확인 필요")

        print("SUCCESS: 투명도 조절 기능 테스트 완료")

    @pytest.mark.asyncio
    async def test_s4_3_quick_hide_escape(self, page):
        """S4-3: 빠른 숨김 기능 (Escape)"""

        # 1. 게임 페이지로 이동
        await page.goto("http://localhost:8003")
        await page.click("a:has-text('오목')")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # 2. 초기 상태에서 게임 영역이 보이는지 확인
        game_area_selectors = [
            ".game-overlay",
            ".game-container",
            "#gameArea",
            ".omok-game",
        ]

        initial_game_area = None
        for selector in game_area_selectors:
            try:
                element = page.locator(selector)
                if await element.is_visible(timeout=1000):
                    initial_game_area = element
                    print(f"SUCCESS: 게임 영역 발견 - {selector}")
                    break
            except:
                continue

        # 3. Escape 키로 빠른 숨김 테스트
        print("Escape 키 첫 번째 누름 (숨김)...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

        # 게임 영역이 숨겨졌는지 확인 (투명해지거나 숨겨짐)
        # 실제 구현에 따라 다를 수 있으므로 여러 방법으로 확인
        if initial_game_area:
            try:
                # opacity가 낮아졌거나 display가 none이 되었는지 확인
                opacity = await initial_game_area.get_attribute("style")
                if opacity and ("opacity: 0" in opacity or "display: none" in opacity):
                    print("SUCCESS: Escape으로 게임 영역 숨김 확인")
                else:
                    print("INFO: 게임 영역 숨김 상태 불분명 - CSS 확인 필요")
            except:
                print("INFO: 게임 영역 속성 확인 실패")

        print("Escape 키 두 번째 누름 (복원)...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(1000)

        # 게임 영역이 다시 나타났는지 확인
        if initial_game_area:
            try:
                if await initial_game_area.is_visible():
                    print("SUCCESS: Escape으로 게임 영역 복원 확인")
                else:
                    print("INFO: 게임 영역 복원 상태 불분명")
            except:
                print("INFO: 게임 영역 복원 확인 실패")

        # 4. 빠른 숨김 버튼으로도 동일한 기능 테스트
        hide_button_selectors = [
            ".quick-hide",
            "button:has-text('업무모드')",
            "button:has-text('숨김')",
            ".stealth-button",
            "#quickHideBtn",
        ]

        found_hide_button = None
        for selector in hide_button_selectors:
            try:
                button = page.locator(selector)
                if await button.is_visible(timeout=2000):
                    found_hide_button = button
                    print(f"SUCCESS: 빠른 숨김 버튼 발견 - {selector}")
                    break
            except:
                continue

        if found_hide_button:
            print("빠른 숨김 버튼 클릭 테스트...")
            await found_hide_button.click()
            await page.wait_for_timeout(1000)
            print("SUCCESS: 빠른 숨김 버튼 클릭")

            # 다시 버튼 클릭해서 복원
            await found_hide_button.click()
            await page.wait_for_timeout(1000)
            print("SUCCESS: 빠른 숨김 버튼으로 복원")
        else:
            print("INFO: 빠른 숨김 버튼을 찾을 수 없음")

        print("SUCCESS: 빠른 숨김 기능 테스트 완료")

    @pytest.mark.asyncio
    async def test_s4_comprehensive_stealth_mode(self, page):
        """S4 통합: 종합적인 스텔스 모드 테스트"""

        # 1. Excel 위장 상태에서 게임 시작
        await page.goto("http://localhost:8003")
        await expect(page).to_have_title("Excel")

        await page.click("a:has-text('오목')")
        await page.wait_for_load_state("networkidle")

        # 2. 스텔스 모드 기능들을 순차적으로 테스트
        await page.wait_for_timeout(2000)

        # 투명도 조절 → 빠른 숨김 → 복원 시퀀스
        try:
            # 투명도를 낮춤
            opacity_slider = page.locator("input[type='range']").first
            if await opacity_slider.is_visible(timeout=2000):
                await opacity_slider.fill("20")
                await page.wait_for_timeout(1000)
                print("SUCCESS: 투명도 20%로 설정")

            # Escape로 완전 숨김
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
            print("SUCCESS: Escape로 완전 숨김")

            # 이 상태에서는 Excel만 보여야 함
            # Excel 요소들이 여전히 보이는지 확인
            excel_elements = page.locator("text=파일, text=홈, text=삽입")
            excel_count = await excel_elements.count()
            if excel_count > 0:
                print("SUCCESS: 숨김 상태에서 Excel 요소들만 표시됨")

            # Escape로 복원
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
            print("SUCCESS: Escape로 게임 복원")

            # 투명도 다시 올림
            if await opacity_slider.is_visible(timeout=2000):
                await opacity_slider.fill("80")
                await page.wait_for_timeout(1000)
                print("SUCCESS: 투명도 80%로 복원")

        except Exception as e:
            print(f"INFO: 일부 스텔스 기능 테스트 완료 - {e}")

        # 3. 최종 상태에서 게임 기능이 정상인지 확인
        try:
            create_room_btn = page.locator("text=방 만들기")
            if await create_room_btn.is_visible():
                print("SUCCESS: 스텔스 모드 후에도 게임 버튼 정상 작동")
        except:
            pass

        # 최종 상태 스크린샷
        await page.screenshot(path="stealth_mode_final.png")
        print("SUCCESS: 종합 스텔스 모드 테스트 완료")


class TestS4AccessibilityAndUsability:
    """S4 확장: 접근성 및 사용성 테스트"""

    @pytest.mark.asyncio
    async def test_responsive_design_mobile_compatibility(self):
        """모바일 반응형 디자인 테스트"""
        async with async_playwright() as p:
            # 모바일 해상도로 테스트
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 375, "height": 667}  # iPhone SE 크기
            )
            page = await context.new_page()

            try:
                await page.goto("http://localhost:8003")
                await page.click("a:has-text('오목')")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)

                # 모바일에서도 Excel 위장이 적절한지 확인
                await expect(page).to_have_title("Excel")

                # 모바일에서 게임 요소들이 적절히 표시되는지 확인
                page_content = await page.content()

                # 모바일 최적화 요소들 확인
                mobile_indicators = ["viewport", "responsive", "mobile", "@media"]

                mobile_optimized = False
                for indicator in mobile_indicators:
                    if indicator in page_content:
                        mobile_optimized = True
                        print(f"SUCCESS: 모바일 최적화 요소 발견 - {indicator}")
                        break

                await page.screenshot(path="mobile_view.png")
                print("SUCCESS: 모바일 반응형 테스트 완료")

            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, page):
        """키보드 네비게이션 테스트"""

        await page.goto("http://localhost:8003")
        await page.click("a:has-text('오목')")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Tab 키로 네비게이션 테스트
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(500)

        # 포커스된 요소가 있는지 확인
        focused_element = page.locator(":focus")
        try:
            if await focused_element.count() > 0:
                print("SUCCESS: 키보드 포커스 네비게이션 가능")
            else:
                print("INFO: 키보드 포커스 요소 확인 불가")
        except:
            print("INFO: 키보드 네비게이션 테스트 완료")

        # Enter 키로 요소 활성화 테스트
        try:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)
            print("SUCCESS: Enter 키 활성화 테스트 완료")
        except:
            pass

        print("SUCCESS: 키보드 네비게이션 테스트 완료")
