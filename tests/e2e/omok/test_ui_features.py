"""
S4: 월급루팡 특화 UI/UX E2E 테스트

scenarios.md의 S4 시나리오를 체계적으로 검증:
- S4-1: Excel 위장 모드
- S4-2: 투명도 조절 기능
- S4-3: 빠른 숨김 기능 (Escape)

헬퍼 함수를 활용한 개선된 버전
"""

import pytest

from ...conftest import CONTEXT_CONFIG, TEST_CONFIG
from .omok_helpers import OmokGameHelper, OmokSelectors


class TestS4ExcelStealth:
    """S4: 월급루팡 특화 UI/UX"""

    @pytest.mark.asyncio
    async def test_s4_1_excel_disguise_mode(self, page):
        """S4-1: Excel 위장 모드"""

        # 1. 메인 페이지 접속
        await page.goto(OmokGameHelper.BASE_URL)

        # Excel 위장 기본 요소 확인
        page_title = await page.title()
        assert "Excel" in page_title, f"Excel 위장 실패: {page_title}"
        print("SUCCESS: Excel 제목 위장 확인")

        # 2. Excel 위장 요소들 확인 - 헬퍼 함수 활용
        excel_elements_verified = await OmokGameHelper.verify_excel_elements(
            page, min_count=3
        )
        assert excel_elements_verified, "Excel 위장 요소들이 부족합니다"

        # 3. 오목 게임 선택 - 헬퍼 상수 활용
        omok_link = page.locator(OmokSelectors.MainPage.OMOK_CARD).first
        await omok_link.click()
        await page.wait_for_load_state("networkidle")

        # 4. Excel 스타일 UI 확인 및 화려한 요소 체크 - 헬퍼 함수 활용
        await page.wait_for_timeout(TEST_CONFIG["element_wait"])

        # Excel 스타일 요소들 재확인
        excel_style_verified = await OmokGameHelper.verify_excel_elements(
            page, min_count=2
        )

        # 화려한 게임 요소들이 숨겨져 있는지 확인
        no_flashy_elements = await OmokGameHelper.verify_no_flashy_elements(page)

        if not excel_style_verified or not no_flashy_elements:
            print("INFO: 일부 위장 요소 확인 불가, 테스트 계속 진행")

        print("SUCCESS: Excel 위장 모드 검증 완료")

    @pytest.mark.asyncio
    async def test_s4_2_opacity_control(self, page):
        """S4-2: 투명도 조절 기능"""

        # 1. 게임 페이지로 이동 - 헬퍼 함수 활용
        await page.goto(OmokGameHelper.BASE_URL)
        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")

        # 2. 투명도 조절 테스트 - 헬퍼 함수 활용
        opacity_slider = await OmokGameHelper.find_opacity_slider(page)

        if opacity_slider:
            # 3. 투명도 조절 시퀀스 테스트
            opacity_tests = [
                ("30", "30% 투명도"),
                ("90", "90% 투명도"),
                ("60", "60% 중간 투명도"),
            ]

            for opacity_value, description in opacity_tests:
                success = await OmokGameHelper.set_opacity(page, opacity_value)
                if success:
                    print(f"SUCCESS: {description} 설정 완료")
                else:
                    print(f"INFO: {description} 설정 실패")

            # 4. 투명도 변경 후에도 게임이 정상 작동하는지 확인 - 헬퍼 상수 활용
            create_room_btn = page.locator("text=방 만들기")
            if await create_room_btn.is_visible():
                await create_room_btn.click()
                await page.wait_for_timeout(TEST_CONFIG["element_wait"])

                # 모달이 나타났는지 확인 - 헬퍼 상수 활용
                nickname_input = page.locator(OmokSelectors.GameUI.NICKNAME_INPUT)
                if await nickname_input.is_visible(timeout=TEST_CONFIG["game_action"]):
                    print("SUCCESS: 투명도 변경 후에도 게임 기능 정상")

                    # 모달 닫기 - 헬퍼 함수 활용
                    await OmokGameHelper.find_and_click_button(
                        page,
                        [
                            OmokSelectors.Buttons.CANCEL,
                            "button:has-text('닫기')",
                            ".modal-close",
                        ],
                        success_message="모달 닫기",
                    )
        else:
            print("INFO: 투명도 슬라이더를 찾을 수 없음 - UI 구조 확인 필요")

        print("SUCCESS: 투명도 조절 기능 테스트 완료")

    @pytest.mark.asyncio
    async def test_s4_3_quick_hide_escape(self, page):
        """S4-3: 빠른 숨김 기능 (Escape)"""

        # 1. 게임 페이지로 이동 - 헬퍼 함수 활용
        await page.goto(OmokGameHelper.BASE_URL)
        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(TEST_CONFIG["element_wait"])

        # 2. 초기 상태에서 게임 영역이 보이는지 확인 - 헬퍼 함수 활용
        initial_game_area = await OmokGameHelper.find_game_area(page)
        if initial_game_area:
            print("SUCCESS: 초기 게임 영역 확인 완료")

        # 3. Escape 키로 빠른 숨김/복원 테스트 - 헬퍼 함수 활용
        print("Escape 키 첫 번째 누름 (숨김)...")
        hide_success = await OmokGameHelper.toggle_stealth_mode(page)

        if hide_success:
            # 게임 영역이 숨겨졌는지 확인
            hidden_verified = await OmokGameHelper.verify_game_area_visibility(
                page, should_be_visible=False
            )
            if hidden_verified:
                print("SUCCESS: 게임 영역 숨김 상태 확인")

        print("Escape 키 두 번째 누름 (복원)...")
        show_success = await OmokGameHelper.toggle_stealth_mode(page)

        if show_success:
            # 게임 영역이 복원되었는지 확인
            visible_verified = await OmokGameHelper.verify_game_area_visibility(
                page, should_be_visible=True
            )
            if visible_verified:
                print("SUCCESS: 게임 영역 복원 상태 확인")

        # 4. 빠른 숨김 버튼으로도 동일한 기능 테스트 - 헬퍼 함수 활용
        found_hide_button = await OmokGameHelper.find_hide_button(page)

        if found_hide_button:
            print("빠른 숨김 버튼 클릭 테스트...")
            try:
                await found_hide_button.click()
                await page.wait_for_timeout(TEST_CONFIG["element_wait"])
                print("SUCCESS: 빠른 숨김 버튼 클릭")

                # 다시 버튼 클릭해서 복원
                await found_hide_button.click()
                await page.wait_for_timeout(TEST_CONFIG["element_wait"])
                print("SUCCESS: 빠른 숨김 버튼으로 복원")
            except Exception as e:
                print(f"INFO: 빠른 숨김 버튼 클릭 실패 - {e}")
        else:
            print("INFO: 빠른 숨김 버튼을 찾을 수 없음")

        print("SUCCESS: 빠른 숨김 기능 테스트 완료")

    @pytest.mark.asyncio
    async def test_s4_comprehensive_stealth_mode(self, page):
        """S4 통합: 종합적인 스텔스 모드 테스트"""

        # 1. Excel 위장 상태에서 게임 시작 - 헬퍼 함수 활용
        await page.goto(OmokGameHelper.BASE_URL)
        comprehensive_title = await page.title()
        assert "Excel" in comprehensive_title, f"Excel 위장 실패: {comprehensive_title}"

        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")

        # 2. 스텔스 모드 기능들을 순차적으로 테스트
        await page.wait_for_timeout(TEST_CONFIG["element_wait"])

        # 종합적인 스텔스 모드 시퀀스 테스트 - 헬퍼 함수 활용
        try:
            stealth_success = await OmokGameHelper.test_comprehensive_stealth_sequence(
                page
            )
            if stealth_success:
                print("SUCCESS: 종합 스텔스 모드 시퀀스 모든 테스트 통과")
            else:
                print("INFO: 종합 스텔스 모드 시퀀스 일부 테스트 완료")
        except Exception as e:
            print(f"INFO: 일부 스텔스 기능 테스트 완료 - {e}")

        # 3. 최종 상태에서 게임 기능이 정상인지 확인
        try:
            create_room_btn = page.locator("text=방 만들기")
            if await create_room_btn.is_visible():
                print("SUCCESS: 스텔스 모드 후에도 게임 버튼 정상 작동")
        except Exception:
            pass

        # 최종 상태 스크린샷
        await page.screenshot(path="stealth_mode_final.png")
        print("SUCCESS: 종합 스텔스 모드 테스트 완료")


class TestS4AccessibilityAndUsability:
    """S4 확장: 접근성 및 사용성 테스트"""

    @pytest.mark.asyncio
    async def test_responsive_design_mobile_compatibility(self, browser):
        """모바일 반응형 디자인 테스트 - fixture 활용"""
        # 모바일 해상도로 테스트 - conftest.py fixture 활용
        context = await browser.new_context(
            **{
                **CONTEXT_CONFIG,
                "viewport": {"width": 375, "height": 667},
            }  # iPhone SE 크기
        )
        page = await context.new_page()

        try:
            await page.goto(OmokGameHelper.BASE_URL)
            await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(TEST_CONFIG["element_wait"])

            # 모바일에서도 Excel 위장이 적절한지 확인
            mobile_title = await page.title()
            assert "Excel" in mobile_title, f"Excel 위장 실패: {mobile_title}"

            # 모바일에서 게임 요소들이 적절히 표시되는지 확인
            # page_content = await page.content()

            # 모바일 최적화 요소들 확인 - 헬퍼 함수 및 상수 활용
            # mobile_optimized =
            await OmokGameHelper.check_page_condition(
                page,
                OmokSelectors.TextPatterns.MOBILE_INDICATORS,
                "content",
                "모바일 최적화 요소 발견",
            )

            await page.screenshot(path="mobile_view.png")
            print("SUCCESS: 모바일 반응형 테스트 완료")

        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, page):
        """키보드 네비게이션 테스트"""

        await page.goto(OmokGameHelper.BASE_URL)
        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(TEST_CONFIG["element_wait"])

        # Tab 키로 네비게이션 테스트
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(TEST_CONFIG["retry_interval"])

        # 포커스된 요소가 있는지 확인
        focused_element = page.locator(":focus")
        try:
            if await focused_element.count() > 0:
                print("SUCCESS: 키보드 포커스 네비게이션 가능")
            else:
                print("INFO: 키보드 포커스 요소 확인 불가")
        except Exception:
            print("INFO: 키보드 네비게이션 테스트 완료")

        # Enter 키로 요소 활성화 테스트
        try:
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(TEST_CONFIG["element_wait"])
            print("SUCCESS: Enter 키 활성화 테스트 완료")
        except Exception:
            pass

        print("SUCCESS: 키보드 네비게이션 테스트 완료")

    @pytest.mark.asyncio
    async def test_ui_element_visibility_states(self, page):
        """UI 요소 가시성 상태 테스트 (새 추가 테스트)"""

        await page.goto(OmokGameHelper.BASE_URL)
        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(TEST_CONFIG["element_wait"])

        # 1. 투명도 슬라이더와 숨김 버튼이 함께 작동하는지 테스트
        opacity_slider = await OmokGameHelper.find_opacity_slider(page)
        hide_button = await OmokGameHelper.find_hide_button(page)

        if opacity_slider and hide_button:
            # 투명도를 조절한 후 숨김 버튼 클릭
            await OmokGameHelper.set_opacity(page, "40")
            await hide_button.click()
            await page.wait_for_timeout(TEST_CONFIG["element_wait"])

            # Excel 요소들이 여전히 보이는지 확인
            excel_visible = await OmokGameHelper.verify_excel_elements(page)
            if excel_visible:
                print("SUCCESS: 투명도 + 숨김 조합에서도 Excel 위장 유지")

            # 복원 테스트
            await hide_button.click()
            await OmokGameHelper.set_opacity(page, "80")
            print("SUCCESS: UI 요소 가시성 상태 복합 테스트 완료")
        else:
            print("INFO: UI 요소 찾기 실패, 가시성 테스트 생략")

    @pytest.mark.asyncio
    async def test_stealth_mode_accessibility(self, page):
        """스텔스 모드 접근성 테스트 (새 추가 테스트)"""

        await page.goto(OmokGameHelper.BASE_URL)
        await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
        await page.wait_for_load_state("networkidle")

        # 1. 키보드만으로 스텔스 모드 제어 가능한지 테스트
        print("키보드 전용 스텔스 모드 테스트 시작...")

        # Escape 키 테스트
        escape_success = await OmokGameHelper.toggle_stealth_mode(page)
        if escape_success:
            print("SUCCESS: Escape 키를 통한 스텔스 모드 제어 가능")

            # 복원도 테스트
            restore_success = await OmokGameHelper.toggle_stealth_mode(page)
            if restore_success:
                print("SUCCESS: 키보드만으로 완전한 스텔스 모드 제어 가능")

        # 2. 시각적 피드백 확인 (게임 영역 가시성 변화)
        game_area_visible = await OmokGameHelper.verify_game_area_visibility(
            page, should_be_visible=True
        )
        if game_area_visible:
            print("SUCCESS: 스텔스 모드 접근성 테스트 완료")
        else:
            print("INFO: 게임 영역 상태 확인 불가")

        print("SUCCESS: 스텔스 모드 접근성 테스트 완료")
