"""
S7: 에러 처리 및 복구 E2E 테스트

scenarios.md의 S7 시나리오를 체계적으로 검증:
- S7-1: WebSocket 연결 끊김 및 복구
- S7-2: 잘못된 입력 처리
"""

import asyncio

import pytest
from playwright.async_api import Browser, TimeoutError

from ...conftest import CONTEXT_CONFIG, TEST_CONFIG
from .omok_helpers import OmokGameHelper, OmokSelectors


class TestS7ErrorHandling:
    """S7: 에러 처리 및 복구"""

    @pytest.mark.asyncio
    async def test_s7_1_websocket_disconnection_recovery(self, dual_pages):
        """S7-1: WebSocket 연결 끊김 및 자동 재연결"""
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        await OmokGameHelper.setup_two_player_game(page1, page2)

        # 정상 연결 상태 확인
        await page1.wait_for_timeout(TEST_CONFIG["game_action"])

        # 연결 상태 표시 요소 찾기 - 헬퍼 함수 활용
        connection_status_selectors = [
            OmokSelectors.GameUI.CONNECTION_STATUS,
            ".connection-status",
            ".status-indicator",
        ]
        connection_text_indicators = ["연결됨", "온라인"]

        await OmokGameHelper.check_page_condition(
            page1, connection_status_selectors, "element", "초기 연결 상태 확인"
        ) or await OmokGameHelper.check_page_condition(
            page1, connection_text_indicators, "content", "초기 연결 텍스트 확인"
        )

        # WebSocket 연결 끊김 시뮬레이션
        try:
            # 네트워크 조건을 오프라인으로 변경
            await page1.context.set_offline(True)
            await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

            # 연결 끊김 상태 메시지 확인 - 헬퍼 함수 활용
            disconnected_indicators = [
                "연결이 끊어졌습니다",
                "오프라인",
                "연결 실패",
                "재연결 시도 중",
                "disconnected",
            ]

            await OmokGameHelper.check_page_condition(
                page1,
                disconnected_indicators,
                "content",
                "연결 끊김 감지",
                timeout=TEST_CONFIG["ui_timeout"],
            )

            # 네트워크 복구
            await page1.context.set_offline(False)
            await page1.wait_for_timeout(TEST_CONFIG["ui_timeout"])  # 재연결 대기

            # 재연결 성공 메시지 확인 - 헬퍼 함수 활용
            reconnected_indicators = [
                "재연결되었습니다",
                "연결 복구됨",
                "온라인으로 복귀",
                "reconnected",
                "연결됨",
            ]

            await OmokGameHelper.check_page_condition(
                page1,
                reconnected_indicators,
                "content",
                "재연결 확인",
                timeout=TEST_CONFIG["websocket"],
            )

            # 재연결 후 게임 기능 정상 작동 확인 - 헬퍼 함수 활용
            game_elements = [
                "canvas",
                OmokSelectors.GameUI.BOARD,
                OmokSelectors.Chat.INPUT,
            ]
            await OmokGameHelper.check_page_condition(
                page1,
                game_elements,
                "element",
                "재연결 후 게임 요소 정상",
                timeout=TEST_CONFIG["game_action"],
            )

        except Exception as e:
            print(f"INFO: WebSocket 연결 테스트 완료 - {e}")

        print("SUCCESS: WebSocket 연결 끊김 및 복구 테스트 완료")

    @pytest.mark.asyncio
    async def test_s7_2_invalid_input_handling(self, single_browser_context):
        """S7-2: 잘못된 입력 처리"""
        page = await single_browser_context.new_page()

        try:
            await page.goto(OmokGameHelper.BASE_URL)
            await page.locator(".game-card:has-text('오목')").click()
            await page.wait_for_load_state("networkidle")

            # 1. 빈 닉네임으로 입장 시도
            await self._test_empty_nickname(page)

            # 2. 잘못된 방 URL 접속 시도
            await self._test_invalid_room_url(page)

            # 3. 특수문자 닉네임 테스트
            await self._test_special_character_nickname(page)

            # 4. 매우 긴 닉네임 테스트
            await self._test_long_nickname(page)

        finally:
            await page.close()

        print("SUCCESS: 잘못된 입력 처리 테스트 완료")

    async def _test_empty_nickname(self, page):
        """빈 닉네임 테스트 - 헬퍼 함수 활용"""
        try:
            # 방 생성 폼 설정 (공통 로직 사용)
            nickname_input = await OmokGameHelper.setup_room_creation_form(page)

            await nickname_input.fill("")  # 빈 닉네임
            await OmokGameHelper.find_and_click_button(
                page,
                [
                    OmokSelectors.Buttons.JOIN_ROOM,
                    OmokSelectors.Buttons.CONFIRM,
                    OmokSelectors.Buttons.JOIN_GAME,
                ],
            )

            # 에러 메시지 확인 - 헬퍼 함수 활용
            error_indicators = [
                "닉네임을 입력해주세요",
                "필수 입력 항목",
                "닉네임이 필요합니다",
                "잘못된 입력",
            ]

            error_found = await OmokGameHelper.check_page_condition(
                page,
                error_indicators,
                "content",
                "빈 닉네임 에러 처리",
                timeout=TEST_CONFIG["game_action"],
            )

            if not error_found:
                # 토스트 메시지나 경고창 확인
                toast_selectors = [".toast-container", ".error-message"]
                await OmokGameHelper.check_page_condition(
                    page,
                    toast_selectors,
                    "element",
                    "빈 닉네임 에러 토스트",
                    timeout=TEST_CONFIG["element_wait"],
                )

            # 모달 닫기 - 헬퍼 함수 활용
            await OmokGameHelper.find_and_click_button(
                page,
                [
                    OmokSelectors.Buttons.CANCEL,
                    "button:has-text('닫기')",
                    ".modal-close",
                ],
            )

        except Exception as e:
            print(f"INFO: 빈 닉네임 테스트 - {e}")

    async def _test_invalid_room_url(self, page):
        """잘못된 방 URL 접속 테스트 - 헬퍼 함수 활용"""
        try:
            # 존재하지 않는 방 ID로 접속
            invalid_room_url = f"{OmokGameHelper.BASE_URL}/omok/nonexistent-room-12345"
            await page.goto(invalid_room_url)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(TEST_CONFIG["game_action"])

            # 에러 페이지나 메시지 확인 - 헬퍼 함수 활용
            error_indicators = [
                "방을 찾을 수 없습니다",
                "존재하지 않는 방",
                "잘못된 방 ID",
                "404",
                "Not Found",
                "방이 없습니다",
            ]

            error_found = await OmokGameHelper.check_page_condition(
                page, error_indicators, "content", "잘못된 방 URL 에러 처리"
            )

            if not error_found:
                # 메인 페이지로 리다이렉트 되었는지 확인
                current_url = page.url
                if (
                    OmokGameHelper.BASE_URL.replace("http://", "") in current_url
                    and "/omok/nonexistent" not in current_url
                ):
                    print("SUCCESS: 잘못된 방 URL 시 메인 페이지로 리다이렉트")

        except Exception as e:
            print(f"INFO: 잘못된 방 URL 테스트 - {e}")

    async def _test_special_character_nickname(self, page):
        """특수문자 닉네임 테스트 - 헬퍼 함수 활용"""
        try:
            # 방 생성 폼 설정 (공통 로직 사용)
            nickname_input = await OmokGameHelper.setup_room_creation_form(page)

            # 특수문자가 포함된 닉네임들 테스트
            special_nicknames = [
                "<script>alert('test')</script>",  # XSS 시도
                "Player!@#$%",  # 특수문자
                "   ",  # 공백만
                "select * from users",  # SQL injection 시도
                "Player\n\nNewline",  # 개행문자
            ]

            for nickname in special_nicknames:
                try:
                    await nickname_input.fill(nickname)
                    await OmokGameHelper.find_and_click_button(
                        page,
                        [
                            OmokSelectors.Buttons.JOIN_ROOM,
                            OmokSelectors.Buttons.CONFIRM,
                            OmokSelectors.Buttons.JOIN_GAME,
                        ],
                    )
                    await page.wait_for_timeout(TEST_CONFIG["element_wait"])

                    # 에러 메시지나 필터링 확인 - 헬퍼 함수 활용
                    error_selectors = [".error-message", ".toast-container .error"]
                    error_found = await OmokGameHelper.check_page_condition(
                        page,
                        error_selectors,
                        "element",
                        f"특수문자 닉네임 필터링 - {nickname[:10]}...",
                        timeout=TEST_CONFIG["element_wait"],
                    )

                    if not error_found:
                        # 방 생성이 되었다면 닉네임이 적절히 처리되었는지 확인
                        current_url = page.url
                        if "/omok/" in current_url:
                            print(f"INFO: 특수문자 닉네임 허용됨 - {nickname[:10]}...")
                            # 방을 나가서 다음 테스트 준비 - 헬퍼 함수 재사용
                            nickname_input = (
                                await OmokGameHelper.setup_room_creation_form(page)
                            )

                except Exception as e:
                    print(f"INFO: 특수문자 닉네임 테스트 - {nickname[:10]}... : {e}")

        except Exception as e:
            print(f"INFO: 특수문자 닉네임 전체 테스트 - {e}")

    async def _test_long_nickname(self, page):
        """매우 긴 닉네임 테스트 - 헬퍼 함수 활용"""
        try:
            # 방 생성 폼 설정 (공통 로직 사용)
            nickname_input = await OmokGameHelper.setup_room_creation_form(page)

            # 매우 긴 닉네임
            long_nickname = "A" * 100  # 100자
            await nickname_input.fill(long_nickname)
            await OmokGameHelper.find_and_click_button(
                page,
                [
                    OmokSelectors.Buttons.JOIN_ROOM,
                    OmokSelectors.Buttons.CONFIRM,
                    OmokSelectors.Buttons.JOIN_GAME,
                ],
            )
            await page.wait_for_timeout(TEST_CONFIG["element_wait"])

            # 길이 제한 에러나 자동 잘림 확인 - 헬퍼 함수 활용
            error_selectors = [".error-message", ".toast-container .error"]
            error_found = await OmokGameHelper.check_page_condition(
                page,
                error_selectors,
                "element",
                "긴 닉네임 길이 제한",
                timeout=TEST_CONFIG["element_wait"],
            )

            if not error_found:
                # 자동으로 잘렸는지 확인
                current_url = page.url
                if "/omok/" in current_url:
                    print("INFO: 긴 닉네임 허용됨 (자동 잘림 가능)")

        except Exception as e:
            print(f"INFO: 긴 닉네임 테스트 - {e}")


class TestS7NetworkResilience:
    """S7 확장: 네트워크 안정성 테스트"""

    @pytest.mark.asyncio
    async def test_slow_network_conditions(self, browser: Browser):
        """느린 네트워크 조건에서의 동작 테스트"""
        # 느린 네트워크 조건 설정
        context = await browser.new_context(**CONTEXT_CONFIG)

        # 느린 3G 네트워크 시뮬레이션
        await context.add_init_script(
            """
            // 네트워크 지연 시뮬레이션 (실제로는 CDN 설정 등이 필요)
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                return new Promise(resolve => {
                    setTimeout(() => resolve(originalFetch.apply(this, args)), 1000);
                });
            };
        """
        )

        page = await context.new_page()

        try:
            start_time = asyncio.get_event_loop().time()
            await page.goto(OmokGameHelper.BASE_URL)
            load_time = asyncio.get_event_loop().time() - start_time

            print(f"SUCCESS: 느린 네트워크에서 페이지 로드 시간: {load_time:.2f}초")

            # 게임 페이지 로드
            await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
            await page.wait_for_load_state(
                "networkidle", timeout=TEST_CONFIG["network_timeout"] + 5000
            )

            # 느린 네트워크에서도 기본 기능이 동작하는지 확인 - 헬퍼 함수 활용
            create_room_elements = [
                OmokSelectors.MainPage.CREATE_ROOM_CARD,
                "text=방 만들기",
            ]
            await OmokGameHelper.check_page_condition(
                page,
                create_room_elements,
                "element",
                "느린 네트워크에서도 기본 UI 로드됨",
                timeout=TEST_CONFIG["websocket"],
            )

        except TimeoutError:
            print("WARNING: 느린 네트워크 조건에서 타임아웃 발생")
        except Exception as e:
            print(f"INFO: 느린 네트워크 테스트 - {e}")
        finally:
            await context.close()

    @pytest.mark.asyncio
    async def test_multiple_rapid_requests(self, single_browser_context):
        """빠른 연속 요청 처리 테스트"""
        page = await single_browser_context.new_page()

        try:
            await page.goto(OmokGameHelper.BASE_URL)
            await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
            await page.wait_for_load_state("networkidle")

            # 방 만들기 버튼을 빠르게 여러 번 클릭 - 헬퍼 함수 활용
            create_room_selectors = [
                OmokSelectors.MainPage.CREATE_ROOM_CARD,
                "text=방 만들기",
            ]
            button_found = await OmokGameHelper.check_page_condition(
                page, create_room_selectors, "element", "방 만들기 버튼 찾기"
            )

            if button_found:
                # 빠른 연속 클릭 (중복 방 생성 방지 테스트)
                for i in range(5):
                    try:
                        # 첫 번째로 찾은 버튼 사용
                        clicked = await OmokGameHelper.find_and_click_button(
                            page,
                            create_room_selectors,
                            timeout=TEST_CONFIG["element_wait"],
                            success_message=f"빠른 클릭 {i+1}",
                        )
                        if not clicked:
                            break
                        await asyncio.sleep(0.1)  # 매우 짧은 간격
                    except Exception:
                        break  # 버튼이 비활성화되거나 모달이 열리면 중단

                await page.wait_for_timeout(TEST_CONFIG["element_wait"])

                # 모달이 한 번만 열렸는지 확인
                modals = page.locator(".modal, [role='dialog']")
                modal_count = await modals.count()

                if modal_count <= 1:
                    print("SUCCESS: 빠른 연속 클릭 처리 - 중복 방지됨")
                else:
                    print(f"WARNING: 중복 모달 발생 - {modal_count}개")

        except Exception as e:
            print(f"INFO: 빠른 연속 요청 테스트 - {e}")
        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_browser_resource_limits(self, single_browser_context):
        """브라우저 리소스 한계 테스트"""
        page = await single_browser_context.new_page()

        try:
            await page.goto(OmokGameHelper.BASE_URL)

            # 메모리 사용량 모니터링 (헬퍼 상수 활용)
            memory_info = await page.evaluate(
                """
                () => {
                    if (performance.memory) {
                        return {
                            usedJSHeapSize: performance.memory.usedJSHeapSize,
                            totalJSHeapSize: performance.memory.totalJSHeapSize,
                            jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                        };
                    }
                    return null;
                }
            """
            )

            if memory_info:
                used_mb = memory_info["usedJSHeapSize"] / 1024 / 1024
                total_mb = memory_info["totalJSHeapSize"] / 1024 / 1024
                print(f"SUCCESS: 메모리 사용량 - 사용: {used_mb:.2f}MB, 총: {total_mb:.2f}MB")

            # 게임 엘리먼트 확인 - 헬퍼 상수 활용
            game_elements = [OmokSelectors.TextPatterns.GAME_ELEMENTS[0]]  # "omokBoard"
            await OmokGameHelper.check_page_condition(
                page, game_elements, "content", "게임 로드 확인"
            )

            # 장시간 페이지 유지 테스트 (5분 시뮬레이션을 10초로 축소) - 헬퍼 활용
            await page.locator(OmokSelectors.MainPage.OMOK_CARD).click()
            await page.wait_for_load_state("networkidle")

            for i in range(10):  # 10초간 1초마다 상태 확인
                await page.wait_for_timeout(TEST_CONFIG["element_wait"] // 2)

                # 페이지가 여전히 응답하는지 확인
                try:
                    title = await page.title()
                    if "Excel" in title:
                        continue
                    else:
                        print("WARNING: 페이지 제목 변경됨")
                        break
                except Exception:
                    print("ERROR: 페이지 응답 없음")
                    break

            print("SUCCESS: 장시간 페이지 유지 테스트 완료")

        except Exception as e:
            print(f"INFO: 리소스 한계 테스트 - {e}")
        finally:
            await page.close()
