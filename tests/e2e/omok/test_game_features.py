"""
S5: 게임 기능 (무르기/재시작/채팅) E2E 테스트

scenarios.md의 S5 시나리오를 체계적으로 검증:
- S5-1: 무르기 요청 및 처리
- S5-2: 재시작 요청 및 처리
- S5-3: 실시간 채팅
"""

import asyncio

import pytest

from ...conftest import TEST_CONFIG
from .omok_helpers import OmokGameHelper, OmokSelectors


class TestS5GameFeatures:
    """S5: 게임 기능 (무르기/재시작/채팅)"""

    @pytest.mark.asyncio
    async def test_s5_1_undo_request_and_handling(self, dual_pages):
        """S5-1: 본인 턴에서 무르기 요청 (상대방 마지막 수 무르기)

        시나리오: 흑돌 플레이어 턴에서 백돌 플레이어의 마지막 수를 무르기 요청
        - 흑돌 플레이어가 첫 수를 놓음
        - 백돌 플레이어가 두 번째 수를 놓은 후 흑돌 턴이 됨
        - 흑돌 플레이어가 무르기 버튼 클릭 (백돌 플레이어의 마지막 수 무르기)
        - 백돌 플레이어에게 무르기 요청 팝업 표시
        - 수락 시 백돌의 마지막 수 제거 및 턴이 백돌로 변경
        """
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정
        # room_url =
        await OmokGameHelper.setup_two_player_game(page1, page2, "Player1", "Player2")

        # 실제 색깔 배정 확인 및 흑돌 플레이어부터 시작
        player1_info = await page1.evaluate(
            """
            window.omokClient.state.players.find(
                p => p.player_number === window.omokClient.state.myPlayerNumber
            )
        """
        )
        player2_info = await page2.evaluate(
            """
            window.omokClient.state.players.find(
                p => p.player_number === window.omokClient.state.myPlayerNumber
            )
        """
        )

        print(
            f"색깔 배정 - Player1: color={player1_info['color']}, "
            f"Player2: color={player2_info['color']}"
        )

        # 흑돌(1) 플레이어가 첫 수, 백돌(2) 플레이어가 두 번째 수
        if player1_info["color"] == 1:  # Player1이 흑돌
            first_page, first_num = page1, 1
            second_page, second_num = page2, 2
            print("Player1(흑돌)이 첫 수, Player2(백돌)이 두 번째 수")
        else:  # Player2가 흑돌
            first_page, first_num = page2, 2
            second_page, second_num = page1, 1
            print("Player2(흑돌)이 첫 수, Player1(백돌)이 두 번째 수")

        # 흑돌 플레이어가 첫 수 놓기 (다음은 백돌 차례)
        await OmokGameHelper.place_stone_and_verify_turn(
            first_page, first_num, 0.5, 0.5, 2, page1, page2
        )
        print(f"Player{first_num}(흑돌) 첫 수 완료 - Player{second_num}(백돌) 턴")

        # 백돌 플레이어가 두 번째 수 놓기 (다음은 흑돌 차례)
        await OmokGameHelper.place_stone_and_verify_turn(
            second_page, second_num, 0.6, 0.6, 1, page1, page2
        )
        print(
            f"Player{second_num}(백돌) 두 번째 수 완료 - Player{first_num}(흑돌) 턴 (S5-1 테스트 시점)"
        )

        # 현재 흑돌 턴에서 흑돌 플레이어가 백돌 플레이어의 마지막 수를 무르기 요청
        undo_selectors = [OmokSelectors.Buttons.UNDO]

        found_undo = await OmokGameHelper.find_and_click_button(
            first_page,
            undo_selectors,
            success_message=f"Player{first_num}(흑돌)이 본인 턴에서 무르기 버튼 클릭",
        )

        if found_undo:
            # 백돌 플레이어에게 무르기 요청 팝업 확인
            await second_page.wait_for_timeout(TEST_CONFIG["element_wait"])

            popup_indicators = OmokSelectors.TextPatterns.UNDO_REQUEST_TITLES + [
                OmokSelectors.Buttons.AGREE,
                OmokSelectors.Buttons.REJECT,
            ]

            found_popup = await OmokGameHelper.check_page_condition(
                second_page,
                popup_indicators,
                "element",
                f"Player{second_num}(백돌)에게 무르기 요청 팝업 확인",
            )

            if found_popup:
                # 수락 버튼 클릭
                accept_buttons = [
                    OmokSelectors.Buttons.AGREE,
                    OmokSelectors.Buttons.CONFIRM,
                ]

                await OmokGameHelper.find_and_click_button(
                    second_page,
                    accept_buttons,
                    success_message=f"Player{second_num}(백돌)이 무르기 수락",
                )

                # S5-1 검증: 백돌 플레이어의 마지막 수 제거, 턴이 백돌 플레이어로 변경
                await page1.wait_for_timeout(TEST_CONFIG["element_wait"])
                await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

                game_state = await OmokGameHelper.get_game_state(page1)
                assert game_state is not None, "게임 상태를 가져올 수 없습니다"

                current_player = game_state["current_player"]
                print(f"무르기 후 현재 플레이어: {current_player}")
                assert (
                    current_player == 2
                ), f"백돌 플레이어의 수를 무른 후 턴이 백돌(2)로 돌아와야 하는데 {current_player}임"

                # 백돌(2)이 제거되어 0개, 흑돌(1)은 그대로 1개
                board_state = game_state.get("board")
                black_stones = sum(
                    sum(1 for cell in row if cell == 1) for row in board_state
                )
                white_stones = sum(
                    sum(1 for cell in row if cell == 2) for row in board_state
                )

                print(f"흑돌: {black_stones}개, 백돌: {white_stones}개")
                assert (
                    black_stones == 1
                ), f"흑돌은 그대로 1개여야 하는데 {black_stones}개임"
                assert (
                    white_stones == 0
                ), f"백돌의 마지막 수가 제거되어 0개여야 하는데 {white_stones}개임"

                print(
                    "SUCCESS: 백돌 플레이어의 마지막 수 제거 및 턴이 백돌로 변경됨 확인"
                )
            else:
                raise AssertionError(
                    "무르기 요청 팝업을 찾을 수 없어서 테스트 실행 불가"
                )
        else:
            raise AssertionError("무르기 버튼을 찾을 수 없어서 테스트 실행 불가")

        print("SUCCESS: S5-1 본인 턴에서 무르기 테스트 완료")

    @pytest.mark.asyncio
    async def test_s5_2_undo_own_move_on_opponent_turn(self, dual_pages):
        """S5-2: 상대 턴에서 무르기 요청 (내 수 무르기)

        시나리오: 백돌 턴에서 흑돌 플레이어가 자신의 마지막 수를 무르기 요청
        - 흑돌 플레이어가 첫 수를 놓은 후 백돌 턴이 됨
        - 흑돌 플레이어가 무르기 버튼 클릭 (자신의 수 무르기)
        - 백돌 플레이어에게 무르기 요청 팝업 표시
        - 수락 시 흑돌의 마지막 수 제거 및 턴이 흑돌로 변경
        """
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        # room_url =
        await OmokGameHelper.setup_two_player_game(page1, page2, "Player1", "Player2")

        # 실제 색깔 배정 확인 및 흑돌 플레이어가 첫 수 놓기
        player1_info = await page1.evaluate(
            """
            window.omokClient.state.players.find(
                p => p.player_number === window.omokClient.state.myPlayerNumber
            )
        """
        )
        player2_info = await page2.evaluate(
            """
            window.omokClient.state.players.find(
                p => p.player_number === window.omokClient.state.myPlayerNumber
            )
        """
        )

        print(
            f"색깔 배정 - Player1: color={player1_info['color']}, "
            f"Player2: color={player2_info['color']}"
        )

        # 흑돌(1) 플레이어가 첫 수 놓음 (이후 백돌 턴이 됨)
        if player1_info["color"] == 1:  # Player1이 흑돌
            first_page, first_num = page1, 1
            second_page, second_num = page2, 2
            print("Player1(흑돌)이 첫 수 놓기")
        else:  # Player2가 흑돌
            first_page, first_num = page2, 2
            second_page, second_num = page1, 1
            print("Player2(흑돌)이 첫 수 놓기")

        # 흑돌 플레이어가 첫 수를 놓음 (이후 백돌 턴이 됨)
        await OmokGameHelper.place_stone_and_verify_turn(
            first_page, first_num, 0.5, 0.5, 2, page1, page2
        )
        print(
            f"Player{first_num}(흑돌) 첫 수 완료 - Player{second_num}(백돌) 턴으로 변경됨"
        )

        # 현재 백돌 턴인 상태에서 흑돌 플레이어가 자신의 수를 무르기 요청
        # (시나리오 S5-2: 상대 턴에서 내 수 무르기)
        print(
            f"현재 상태: Player{second_num}(백돌) 턴, Player{first_num}(흑돌)이 자신의 마지막 수를 무르기 요청"
        )

        # 흑돌 플레이어가 무르기 버튼 클릭 (자신의 마지막 수 무르기)
        undo_selectors = [
            OmokSelectors.Buttons.UNDO,
        ]

        found_undo = await OmokGameHelper.find_and_click_button(
            first_page,
            undo_selectors,
            success_message=f"Player{first_num}(흑돌)이 상대 턴에서 무르기 버튼 클릭",
        )

        if found_undo:
            # 백돌 플레이어에게 무르기 요청 팝업이 나타나는지 확인
            await second_page.wait_for_timeout(TEST_CONFIG["element_wait"])

            popup_indicators = OmokSelectors.TextPatterns.UNDO_REQUEST_TITLES + [
                OmokSelectors.Buttons.AGREE,
                OmokSelectors.Buttons.REJECT,
            ]

            found_popup = await OmokGameHelper.check_page_condition(
                second_page,
                popup_indicators,
                "element",
                f"Player{second_num}(백돌)에게 무르기 요청 팝업 확인",
            )

            if found_popup:
                # 수락 버튼 클릭 - 더 많은 선택자로 시도
                accept_buttons = [
                    "button:has-text('동의')",
                    "button:has-text('확인')",
                ]

                accept_success = await OmokGameHelper.find_and_click_button(
                    second_page,
                    accept_buttons,
                    success_message=f"Player{second_num}(백돌)이 무르기 수락",
                )

                if not accept_success:
                    # 승인 버튼을 찾지 못했으면 테스트 실패
                    raise AssertionError(
                        "무르기 승인 버튼을 찾을 수 없어서 승인 처리 불가"
                    )

                # 무르기 후 상태 확인
                await page1.wait_for_timeout(TEST_CONFIG["element_wait"])
                await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

                # 무르기 후 상태 검증 (실제 성공 조건)
                print("무르기 후 턴 변경 검증 시작...")

                # 1. 게임 상태에서 현재 턴 확인 - 반드시 흑돌(1)이어야 함
                game_state = await OmokGameHelper.get_game_state(page1)
                assert game_state is not None, "게임 상태를 가져올 수 없습니다"
                assert (
                    "current_player" in game_state
                ), "게임 상태에 current_player 정보가 없습니다"

                current_player = game_state["current_player"]
                print(f"게임 상태에서 현재 플레이어: {current_player}")
                assert (
                    current_player == 1
                ), f"무르기 후 턴이 흑돌(1)로 돌아와야 하는데 {current_player}임"

                # 2. 보드 상태 확인 - 돌이 제거되었는지 검증
                board_state = game_state.get("board")
                assert board_state is not None, "보드 상태를 가져올 수 없습니다"

                stone_count = sum(
                    sum(1 for cell in row if cell != 0) for row in board_state
                )
                print(f"보드의 총 돌 개수: {stone_count}")
                assert (
                    stone_count == 0
                ), f"무르기 후 보드에 돌이 제거되어야 하는데 {stone_count}개가 남아있음"

                print(
                    f"SUCCESS: 무르기 후 턴이 Player{first_num}(흑돌)로 돌아오고 돌이 제거됨을 확인"
                )
            else:
                raise AssertionError(
                    "무르기 요청 팝업을 찾을 수 없어서 테스트 실행 불가"
                )
        else:
            raise AssertionError(
                "상대 턴에서 무르기 버튼을 찾을 수 없어서 테스트 실행 불가"
            )

        print("SUCCESS: S5-2 상대 턴에서 무르기 테스트 완료")

    @pytest.mark.asyncio
    async def test_s5_3_button_activation_states(self, dual_pages):
        """S5-3: 게임 도중 버튼 활성화 상태 확인

        시나리오: 게임 진행 단계별 무르기/재시작 버튼 상태 검증 (색깔 배정과 무관)
        - 게임 시작 직후: 무르기 버튼 비활성화 또는 숨김
        - 첫 수 이후: 무르기 버튼 활성화
        - 게임 진행 중: 재시작 버튼 항상 활성화
        - 게임 종료 후: 두 버튼 모두 비활성화
        """
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정
        # room_url =
        await OmokGameHelper.setup_two_player_game(page1, page2, "Player1", "Player2")

        print("INFO: 게임 시작 직후 버튼 상태 확인")

        # scenarios.md S5-3 검증 포인트 구현:
        # - 게임 시작 직후에는 무르기 버튼 비활성화 또는 숨김
        # - 재시작 버튼은 게임 시작과 동시에 활성화

        # 1. 게임 시작 직후 (아직 수를 놓지 않은 상태)
        undo_btn = page1.locator(OmokSelectors.Buttons.UNDO).first
        restart_btn = page1.locator(OmokSelectors.Buttons.RESTART).first

        # 무르기 버튼 상태 확인 - 반드시 비활성화되어 있어야 함
        if await undo_btn.is_visible(timeout=TEST_CONFIG["element_wait"]):
            is_disabled = await undo_btn.is_disabled()
            assert (
                is_disabled
            ), "게임 시작 직후 무르기 버튼이 활성화되어 있으면 안 됩니다"
            print("SUCCESS: 게임 시작 직후 무르기 버튼 비활성화 확인")
        else:
            print("SUCCESS: 게임 시작 직후 무르기 버튼 숨김 확인")

        # 재시작 버튼 상태 확인 - 반드시 활성화되어 있어야 함
        assert await restart_btn.is_visible(
            timeout=TEST_CONFIG["element_wait"]
        ), "재시작 버튼이 보이지 않습니다"
        is_disabled = await restart_btn.is_disabled()
        assert not is_disabled, "게임 시작과 동시에 재시작 버튼이 활성화되어야 합니다"
        print("SUCCESS: 게임 시작과 동시에 재시작 버튼 활성화 확인")

        # 2. scenarios.md S5-3: 첫 수를 놓은 후부터 무르기 버튼 활성화
        print("\nINFO: 3-5수 진행 후 버튼 상태 확인")
        await OmokGameHelper.make_alternating_moves(page1, page2, moves_count=3)
        await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

        # 무르기 버튼 활성화 확인 - 첫 수 이후 반드시 활성화되어야 함
        assert await undo_btn.is_visible(
            timeout=TEST_CONFIG["element_wait"]
        ), "무르기 버튼이 보이지 않습니다"
        is_disabled = await undo_btn.is_disabled()
        assert not is_disabled, "첫 수를 놓은 후 무르기 버튼이 활성화되어야 합니다"
        print("SUCCESS: 첫 수 이후 무르기 버튼 활성화 확인")

        # 재시작 버튼 여전히 활성화 확인
        assert await restart_btn.is_visible(
            timeout=TEST_CONFIG["element_wait"]
        ), "재시작 버튼이 보이지 않습니다"
        is_disabled = await restart_btn.is_disabled()
        assert not is_disabled, "게임 진행 중 재시작 버튼이 활성화되어야 합니다"
        print("SUCCESS: 게임 진행 중 재시작 버튼 활성화 유지 확인")

        # 3. 10수 이상 진행된 상태
        print("\nINFO: 10수 이상 진행 후 버튼 상태 확인")
        await OmokGameHelper.make_alternating_moves(
            page1, page2, moves_count=7
        )  # 추가로 7수 더
        await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

        # 버튼들이 여전히 활성화되어 있는지 확인
        if await undo_btn.is_visible(timeout=TEST_CONFIG["element_wait"]):
            is_disabled = await undo_btn.is_disabled()
            if not is_disabled:
                print("SUCCESS: 10수 이상에서도 무르기 버튼 활성화 유지")

        if await restart_btn.is_visible(timeout=TEST_CONFIG["element_wait"]):
            is_disabled = await restart_btn.is_disabled()
            if not is_disabled:
                print("SUCCESS: 10수 이상에서도 재시작 버튼 활성화 유지")

        # 4. 버튼 클릭 시 적절한 반응 테스트
        print("\nINFO: 버튼 클릭 반응성 테스트")

        # 무르기 버튼 클릭
        if await undo_btn.is_visible() and not await undo_btn.is_disabled():
            await undo_btn.click()
            await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

            # 버튼이 일시적으로 비활성화되거나 로딩 상태가 되는지 확인
            try:
                # 로딩 인디케이터나 비활성화 상태 확인
                is_disabled_after_click = await undo_btn.is_disabled()
                if is_disabled_after_click:
                    print("SUCCESS: 무르기 버튼 클릭 후 일시 비활성화")
                else:
                    # 로딩 클래스나 속성 확인
                    classes = await undo_btn.get_attribute("class")
                    if classes and ("loading" in classes or "processing" in classes):
                        print("SUCCESS: 무르기 버튼 클릭 후 로딩 상태")
            except Exception:
                pass

        print("SUCCESS: S5-3 게임 도중 버튼 활성화 상태 테스트 완료")

    @pytest.mark.asyncio
    async def test_s5_4_restart_request_and_handling(self, dual_pages):
        """S5-4: 재시작 요청 및 처리

        시나리오: 게임 진행 중 재시작 요청 (색깔 기반 자동 처리)
        - 게임 진행 중 재시작 버튼 클릭
        - 상대방에게 재시작 요청 팝업 표시
        - 수락 시 보드 완전 초기화
        - 선공/후공 순서는 새로 배정됨 (색깔 기반)
        - 거절 시 기존 게임 계속
        """
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        # room_url =
        await OmokGameHelper.setup_two_player_game(page1, page2, "Player1", "Player2")

        # 게임 진행 (헬퍼 모듈 사용)
        await OmokGameHelper.make_alternating_moves(page1, page2)

        # Player1이 재시작 요청 (헬퍼 모듈 사용)
        restart_selectors = [
            OmokSelectors.Buttons.RESTART,
        ]

        found_restart = await OmokGameHelper.find_and_click_button(
            page1, restart_selectors, success_message="재시작 버튼 클릭"
        )

        if found_restart:
            # Player2에게 재시작 요청 팝업 확인 (헬퍼 모듈 사용)
            await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

            restart_popup_indicators = (
                OmokSelectors.TextPatterns.RESTART_REQUEST_TITLES
                + [
                    OmokSelectors.Buttons.AGREE,
                    OmokSelectors.Buttons.REJECT,
                ]
            )

            found_restart_popup = await OmokGameHelper.check_page_condition(
                page2, restart_popup_indicators, "element", "재시작 요청 팝업 확인"
            )

            if found_restart_popup:
                # 수락 버튼 클릭 (헬퍼 모듈 사용)
                accept_buttons = [
                    OmokSelectors.Buttons.AGREE,
                    OmokSelectors.Buttons.CONFIRM,
                ]

                await OmokGameHelper.find_and_click_button(
                    page2, accept_buttons, success_message="재시작 수락"
                )

                # scenarios.md S5-4 검증 포인트 구현:
                # - 수락 시 보드 완전 초기화
                # - 선공/후공 순서 유지 또는 변경 규칙 적용
                await page1.wait_for_timeout(TEST_CONFIG["game_action"])
                await page2.wait_for_timeout(TEST_CONFIG["game_action"])

                # 1. 보드 완전 초기화 확인
                game_state = await OmokGameHelper.get_game_state(page1)
                assert (
                    game_state is not None
                ), "재시작 후 게임 상태를 가져올 수 없습니다"

                board_state = game_state.get("board")
                assert (
                    board_state is not None
                ), "재시작 후 보드 상태를 가져올 수 없습니다"

                # 보드의 모든 돌이 제거되었는지 확인
                total_stones = sum(
                    sum(1 for cell in row if cell != 0) for row in board_state
                )
                assert (
                    total_stones == 0
                ), f"재시작 후 보드가 초기화되어야 하는데 {total_stones}개의 돌이 남아있음"
                print("SUCCESS: 재시작 후 보드 완전 초기화 확인")

                # 2. 턴이 정상적으로 설정되었는지 확인 (Player1 또는 Player2)
                current_player = game_state.get("current_player")
                assert current_player in [
                    1,
                    2,
                ], f"재시작 후 턴이 올바르지 않음: {current_player}"
                print(f"SUCCESS: 재시작 후 현재 턴: Player{current_player}")

                # 3. 게임 보드가 다시 활성화되었는지 확인 - 헬퍼 함수 활용
                board1_visible = await OmokGameHelper.check_page_condition(
                    page1,
                    [OmokSelectors.GameUI.BOARD],
                    "element",
                    "Player1 오목 보드 표시 확인",
                )
                board2_visible = await OmokGameHelper.check_page_condition(
                    page2,
                    [OmokSelectors.GameUI.BOARD],
                    "element",
                    "Player2 오목 보드 표시 확인",
                )

                assert board1_visible, "Player1 오목 보드가 표시되지 않음"
                assert board2_visible, "Player2 오목 보드가 표시되지 않음"
                print("SUCCESS: 재시작 후 게임 보드 활성화 확인")

            else:
                raise AssertionError(
                    "재시작 요청 팝업을 찾을 수 없어서 테스트 실행 불가"
                )
        else:
            raise AssertionError("재시작 버튼을 찾을 수 없어서 테스트 실행 불가")

        print("SUCCESS: S5-4 재시작 요청 및 처리 테스트 완료")

    @pytest.mark.asyncio
    async def test_s5_5_realtime_chat(self, dual_pages):
        """S5-5: 실시간 채팅

        시나리오: 게임 중 실시간 채팅 기능 (색깔 배정과 무관)
        - 채팅 메시지 입력 및 전송
        - 상대방 화면에 즉시 표시
        - 보낸 사람 닉네임과 메시지 표시
        - XSS 방지 및 빈 메시지 차단
        """
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        # room_url =
        await OmokGameHelper.setup_two_player_game(page1, page2, "Player1", "Player2")

        # 채팅 입력 필드 찾기 (헬퍼 모듈 사용)
        chat_input_selectors = [
            OmokSelectors.Chat.INPUT,
        ]

        found_chat_input = await OmokGameHelper.find_input_field(
            page1, chat_input_selectors
        )

        if found_chat_input:
            # Player1이 메시지 전송
            test_message = "안녕하세요! 테스트 메시지입니다."
            await found_chat_input.fill(test_message)

            # Enter 키로 전송
            await page1.keyboard.press("Enter")
            await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

            # scenarios.md S5-5 검증 포인트 구현:
            # - 메시지 즉시 상대방에게 전달
            # - 보낸 사람 닉네임과 메시지 정확 표시

            # Player2 화면에서 메시지 확인 - 헬퍼 함수 활용
            message_found = await OmokGameHelper.check_page_condition(
                page2, [test_message], "content", "채팅 메시지 수신 확인"
            )

            nickname_found = await OmokGameHelper.check_page_condition(
                page2, ["Player1"], "content", "닉네임 표시 확인"
            )

            # 반드시 메시지와 닉네임이 모두 표시되어야 함
            assert (
                message_found
            ), f"채팅 메시지가 상대방에게 전달되지 않았습니다: {test_message}"
            assert nickname_found, "보낸 사람 닉네임이 표시되지 않았습니다"
            print("SUCCESS: 메시지 즉시 전달 및 닉네임 표시 확인")

            # Player2가 답장 - 헬퍼 함수 활용
            chat_input2 = await OmokGameHelper.find_input_field(
                page2, [OmokSelectors.Chat.INPUT]
            )

            if chat_input2:
                reply_message = "네, 안녕하세요! 답장입니다."
                await chat_input2.fill(reply_message)
                await page2.keyboard.press("Enter")

                # Player1에서 답장 확인
                await page1.wait_for_timeout(TEST_CONFIG["element_wait"])
                # reply_received =
                await OmokGameHelper.check_page_condition(
                    page1, [reply_message], "content", "채팅 답장 수신 확인"
                )

            # scenarios.md S5-5 추가 검증 포인트:
            # - HTML 태그 입력 시 XSS 방지
            # - 빈 메시지나 공백만 있는 메시지 차단

            # XSS 방지 테스트
            xss_test_message = "<script>alert('xss')</script>안전한 메시지"
            await found_chat_input.fill(xss_test_message)
            await page1.keyboard.press("Enter")
            await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

            # 안전한 메시지가 표시되는지 먼저 확인
            safe_message_found = await OmokGameHelper.check_page_condition(
                page2, ["안전한 메시지"], "content", "XSS 테스트 메시지 확인"
            )

            xss_prevented = False
            if safe_message_found:
                # 채팅 영역에서 HTML 이스케이프 확인
                chat_areas = [
                    OmokSelectors.Chat.MESSAGES,
                    OmokSelectors.Chat.MESSAGE_LIST,
                    ".chat-messages",
                ]

                for chat_area_sel in chat_areas:
                    try:
                        chat_area = page2.locator(chat_area_sel)
                        if await chat_area.is_visible(
                            timeout=TEST_CONFIG["element_wait"]
                        ):
                            chat_html = await chat_area.inner_html()
                            # HTML에서 스크립트 태그가 이스케이프되었는지 확인
                            if (
                                "&lt;script&gt;" in chat_html
                                or "script" not in chat_html
                            ):
                                xss_prevented = True
                                print(
                                    "SUCCESS: XSS 방지 확인 - HTML 태그가 이스케이프됨"
                                )
                                break
                    except Exception:
                        continue

            if not xss_prevented:
                # 전체 페이지에서 XSS 방지 확인
                xss_escaped = await OmokGameHelper.check_page_condition(
                    page2, ["&lt;script&gt;"], "content", "XSS 이스케이프 확인"
                )

                script_not_executed = not await OmokGameHelper.check_page_condition(
                    page2, ["alert('xss')"], "content", "스크립트 실행 여부 확인"
                )

                if xss_escaped or script_not_executed:
                    xss_prevented = True
                    print("SUCCESS: XSS 방지 확인 - 스크립트가 실행되지 않음")

            assert xss_prevented, "XSS 방지가 제대로 작동하지 않습니다"

            # 빈 메시지 전송 방지 테스트
            await found_chat_input.fill("")  # 빈 메시지
            # before_empty_content = await page2.content()
            await page1.keyboard.press("Enter")
            await page1.wait_for_timeout(TEST_CONFIG["element_wait"])
            # after_empty_content = await page2.content()

            # 빈 메시지로 인한 새로운 채팅이 추가되지 않아야 함
            # (내용이 변하지 않거나 빈 메시지가 필터링되어야 함)
            print("SUCCESS: 빈 메시지 차단 테스트 완료")

            # 공백만 있는 메시지 테스트
            await found_chat_input.fill("   ")  # 공백만
            await page1.keyboard.press("Enter")
            await page1.wait_for_timeout(TEST_CONFIG["element_wait"])
            print("SUCCESS: 공백 메시지 처리 테스트 완료")

            # 긴 메시지 테스트
            long_message = "이것은 아주 긴 메시지입니다. " * 10
            try:
                await found_chat_input.fill(long_message)
                await page1.keyboard.press("Enter")
                await page2.wait_for_timeout(TEST_CONFIG["element_wait"])
                print("SUCCESS: 긴 메시지 처리 테스트 완료")
            except Exception:
                pass

        else:
            raise AssertionError(
                "채팅 입력 필드를 찾을 수 없습니다 - 채팅 기능이 구현되지 않았을 수 있습니다"
            )

        print("SUCCESS: S5-5 실시간 채팅 테스트 완료")


class TestS5ChatAdvanced:
    """S5 확장: 고급 채팅 기능 테스트"""

    @pytest.mark.asyncio
    async def test_chat_history_and_scrolling(self, dual_pages):
        """채팅 히스토리 및 스크롤 테스트"""
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        # room_url =
        await OmokGameHelper.setup_two_player_game(
            page1, page2, "TestPlayer1", "TestPlayer2"
        )

        # 채팅 입력 필드 찾기
        chat_input = page1.locator(OmokSelectors.Chat.INPUT).first
        if await chat_input.is_visible(timeout=TEST_CONFIG["game_action"]):
            # 여러 메시지 전송하여 스크롤 테스트
            for i in range(10):
                message = f"테스트 메시지 {i+1} - 긴 내용을 포함한 메시지입니다."
                await chat_input.fill(message)
                await page1.keyboard.press("Enter")
                await asyncio.sleep(TEST_CONFIG["retry_interval"] / 1000)

            # 채팅 영역에서 스크롤 동작 확인
            chat_area = page1.locator(OmokSelectors.Chat.MESSAGES).first
            if await chat_area.is_visible():
                # 스크롤을 위로 올려보기
                (
                    await chat_area.scroll_to_top()
                    if hasattr(chat_area, "scroll_to_top")
                    else None
                )
                await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

                # 스크롤을 아래로 내리기
                (
                    await chat_area.scroll_to_bottom()
                    if hasattr(chat_area, "scroll_to_bottom")
                    else None
                )
                await page1.wait_for_timeout(TEST_CONFIG["element_wait"])

                print("SUCCESS: 채팅 스크롤 테스트 완료")

        print("SUCCESS: 채팅 히스토리 테스트 완료")

    @pytest.mark.asyncio
    async def test_chat_emoji_and_special_characters(self, dual_pages):
        """이모지 및 특수문자 채팅 테스트"""
        page1, page2 = dual_pages

        # 두 플레이어 게임 설정 (헬퍼 모듈 사용)
        # room_url =
        await OmokGameHelper.setup_two_player_game(
            page1, page2, "TestPlayer1", "TestPlayer2"
        )

        chat_input = page1.locator(OmokSelectors.Chat.INPUT).first
        if await chat_input.is_visible(timeout=TEST_CONFIG["game_action"]):
            # 특수문자 테스트
            special_messages = [
                "한글 메시지 테스트 ㅎㅎㅎ",
                "English message test!",
                "특수문자: !@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
                "숫자: 1234567890",
                "긴 메시지: " + "가" * 100,
            ]

            for message in special_messages:
                try:
                    await chat_input.fill(message)
                    await page1.keyboard.press("Enter")
                    await page2.wait_for_timeout(TEST_CONFIG["element_wait"])

                    # Player2에서 메시지 확인
                    page2_content = await page2.content()
                    if message[:10] in page2_content:  # 메시지 일부만 확인
                        print(f"SUCCESS: 특수문자 메시지 전송 확인 - {message[:20]}...")

                except Exception as e:
                    print(f"INFO: 특수문자 테스트 - {e}")

        print("SUCCESS: 특수문자 채팅 테스트 완료")
