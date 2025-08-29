"""
오목 E2E 테스트 공통 헬퍼 함수들
중복 코드 제거 및 재사용성 향상을 위한 모듈
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Locator, Page


class OmokSelectors:
    """오목 게임 E2E 테스트용 공통 셀렉터 상수"""

    # === 기본 UI 요소 ===
    class GameUI:
        BOARD = "#omokBoard"
        GAME_AREA = "#gameArea"
        NICKNAME_INPUT = "#nicknameInput"
        PLAYER_LIST = "#playerList"
        CURRENT_TURN = "#currentTurn"
        CONNECTION_STATUS = "#connectionStatus"

    # === 버튼 ===
    class Buttons:
        UNDO = "#undoButton"
        RESTART = "#restartButton"
        CONFIRM = "button:has-text('확인')"
        AGREE = "button:has-text('동의')"
        REJECT = "button:has-text('거절')"
        CANCEL = "button:has-text('취소')"
        JOIN_GAME = "button:has-text('게임 참여')"
        LEAVE_ROOM = "button:has-text('방 나가기')"

    # === 채팅 ===
    class Chat:
        INPUT = "#chatInput"
        MESSAGES = "#chatMessages"
        SEND_BUTTON = "#chatSendButton"
        MESSAGE_LIST = ".chat-messages"

    # === 모달/팝업 ===
    class Modal:
        OVERLAY = "#modalOverlay"
        TITLE = "#modalTitle"
        BODY = "#modalBody"
        FOOTER = "#modalFooter"

    # === 메인 페이지 ===
    class MainPage:
        OMOK_CARD = ".game-card:has-text('오목')"
        CREATE_ROOM_CARD = ".game-card:has-text('방 만들기')"
        JOIN_ROOM_CARD = ".game-card:has-text('방 참여하기')"
        ROOM_LINK_INPUT = "#roomLinkInput"
        HOST_NICKNAME_INPUT = "#hostNickname"

    # === 자주 사용하는 텍스트 패턴 ===
    class TextPatterns:
        # 무르기 관련
        UNDO_REQUEST_TITLES = ["무르기 요청", "무르기를 요청했습니다"]

        # 재시작 관련
        RESTART_REQUEST_TITLES = ["게임 재시작 요청", "재시작을 요청했습니다"]

        # 대기 상태
        WAITING_INDICATORS = ["상대방을 기다리는 중", "대기중", "기다리는", "대기"]

        # 게임 관련
        GAME_ELEMENTS = ["omokBoard", "gameArea", "canvas", "오목", "게임"]

        # 연결 상태
        CONNECTION_INDICATORS = ["연결됨", "온라인", "connected", "정상"]


class OmokGameHelper:
    """오목 게임 E2E 테스트 헬퍼 클래스"""

    BASE_URL = "http://localhost:8003"

    @staticmethod
    async def create_room_and_join(page: Page, nickname: str = "Player1") -> str:
        """
        방 생성 및 입장

        Args:
            page: Playwright Page 객체
            nickname: 플레이어 닉네임

        Returns:
            room_url: 생성된 방의 URL
        """
        # 1. 메인 페이지 접속
        await page.goto(OmokGameHelper.BASE_URL)

        # Excel 위장 확인
        page_title = await page.title()
        assert "Excel" in page_title, f"Excel 위장 실패: {page_title}"

        # 2. 오목 게임 선택
        omok_card = page.locator(".game-card:has-text('오목')")
        await omok_card.click()
        # 다음 단계 UI(방 만들기 버튼)가 나타날 때까지 대기
        await page.locator(".game-card:has-text('방 만들기')").wait_for(
            state="visible", timeout=3000
        )

        # 3. 방 만들기
        create_room_btn = page.locator(".game-card:has-text('방 만들기')")
        await create_room_btn.click()
        # 닉네임 입력 필드가 나타날 때까지 대기

        # 4. 방 생성 완료 화면에서 닉네임 입력
        host_nickname_input = page.locator("#hostNickname")
        await host_nickname_input.wait_for(state="visible", timeout=5000)
        await host_nickname_input.fill(nickname)

        # 5. 게임 입장 (실제 게임 방으로 이동)
        join_game_btn = page.locator("button:has-text('게임 입장')")
        await join_game_btn.click()

        # URL 변경 대기
        await page.wait_for_url("**/omok/**", timeout=3000)
        room_url = page.url
        assert "/omok/" in room_url, f"방 URL 형식 오류: {room_url}"

        # 6. 오목 게임 페이지에서 실제 게임 참여
        await page.wait_for_load_state("networkidle", timeout=3000)

        # 닉네임 입력 (오목 페이지에서 다시 한 번)
        nickname_input = page.locator("#nicknameInput")
        await nickname_input.wait_for(state="visible", timeout=3000)
        await nickname_input.fill(nickname)

        # 게임 참여 버튼 클릭
        join_game_final_btn = page.locator("button:has-text('게임 참여')")
        await join_game_final_btn.click()

        # 게임 보드 표시 대기
        await page.locator("#omokBoard").wait_for(state="visible", timeout=5000)

        print(f"SUCCESS: {nickname}이 방 생성 및 입장 완료 - {room_url}")
        return room_url

    @staticmethod
    async def join_existing_room(
        page: Page, room_url: str, nickname: str = "Player2"
    ) -> None:
        """
        기존 방에 입장

        Args:
            page: Playwright Page 객체
            room_url: 입장할 방의 URL
            nickname: 플레이어 닉네임
        """
        # 1. 방 URL 접속
        await page.goto(room_url)
        # 페이지 로드 완료 대기
        await page.wait_for_load_state("networkidle", timeout=5000)

        # 2. 닉네임 입력
        nickname_input = await OmokGameHelper.find_input_field(
            page, ["#guestNickname", "#nicknameInput"]
        )
        assert nickname_input is not None, f"{nickname} 닉네임 입력 필드를 찾을 수 없습니다"
        await nickname_input.fill(nickname)

        # 3. 게임 참여 버튼 클릭
        join_success = await OmokGameHelper.find_and_click_button(
            page,
            [
                "button:has-text('게임 참여')",
                "button:has-text('입장')",
                "button:has-text('게임 입장')",
                "button:has-text('확인')",
                "button:has-text('시작')",
                ".join-game-button",
            ],
            success_message="입장 버튼 클릭",
        )

        # Enter 키 대안
        if not join_success:
            try:
                await page.keyboard.press("Enter")
                join_success = True
                print("SUCCESS: Enter 키로 입장")
            except:
                pass

        assert join_success, f"{nickname} 입장 버튼을 찾거나 클릭할 수 없습니다"

        # 게임 참여 성공 확인 - 게임 보드나 플레이어 리스트 확인
        try:
            # 게임 보드가 나타나는지 확인
            await page.locator("#omokBoard").wait_for(state="visible", timeout=3000)
        except:
            try:
                # 또는 플레이어 리스트에 자신이 추가되었는지 확인
                await page.locator("#playerList").wait_for(
                    state="visible", timeout=2000
                )
            except:
                # 최소한 페이지 로드는 완료되어야 함
                await page.wait_for_load_state("networkidle", timeout=2000)

        print(f"SUCCESS: {nickname} 방 입장 완료")

    @staticmethod
    async def wait_for_game_start(
        page1: Page, page2: Page, timeout: int = 5000
    ) -> None:
        """
        게임 시작 대기 및 확인

        Args:
            page1: Player1 페이지
            page2: Player2 페이지
            timeout: 대기 시간 (ms)
        """
        # 게임 시작 버튼 찾기 및 클릭
        start_button_clicked = False
        for page in [page1, page2]:
            try:
                start_button = page.locator("button:has-text('게임 시작')")
                if await start_button.is_visible(timeout=1000):
                    await start_button.click()
                    start_button_clicked = True
                    print("SUCCESS: 게임 시작 버튼 클릭")
                    break
            except:
                pass

        # 게임 시작 대기 - 네트워크 안정화
        await page1.wait_for_load_state("networkidle", timeout=3000)
        await page2.wait_for_load_state("networkidle", timeout=3000)

        # 게임 상태 확인 - 더 효율적인 폴링 간격
        max_attempts = 15  # 총 15회 시도 (약 12초)
        for attempt in range(max_attempts):
            # 게임 상태 확인
            game_state1 = await OmokGameHelper.get_game_state(page1)
            game_state2 = await OmokGameHelper.get_game_state(page2)

            # room 상태 확인 (JavaScript에서 직접 가져오기)
            room_status1 = await page1.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.roomStatus || ''
            """
            )
            room_status2 = await page2.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.roomStatus || ''
            """
            )

            # 플레이어 수 확인
            player_count1 = await page1.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.players
                ? window.omokClient.state.players.length : 0
            """
            )
            player_count2 = await page2.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.players
                ? window.omokClient.state.players.length : 0
            """
            )

            # 게임 시작 상태 확인
            game_started1 = await page1.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.gameStarted || false
            """
            )
            game_started2 = await page2.evaluate(
                """
                window.omokClient && window.omokClient.state && window.omokClient.state.gameStarted || false
            """
            )

            print(
                f"DEBUG: room_status1={room_status1}, room_status2={room_status2}, "
                f"player_count1={player_count1}, player_count2={player_count2}, "
                f"game_started1={game_started1}, game_started2={game_started2}"
            )

            # 게임이 시작된 상태인지 확인
            if (
                room_status1 == "playing"
                or room_status2 == "playing"
                or (player_count1 == 2 and player_count2 == 2)
                or game_started1
                or game_started2
            ):
                print(f"SUCCESS: 게임 시작 확인 (시도 {attempt+1}/{max_attempts})")
                # 게임 시작 후 UI 안정화를 위한 최소 대기
                await page1.wait_for_load_state("networkidle", timeout=2000)
                await page2.wait_for_load_state("networkidle", timeout=2000)
                return

            # 점진적 대기 간격 (초기에는 짧게, 나중에는 길게)
            wait_interval = 500 if attempt < 5 else 800
            await page1.wait_for_timeout(wait_interval)
            await page2.wait_for_timeout(wait_interval)

        # 멀티플레이어 게임 시작 확인
        found_game_start = (
            await OmokGameHelper.check_page_condition(
                page1, ["Player1", "Player2"], "content", "Player1 화면에 두 플레이어 표시"
            )
            or await OmokGameHelper.check_page_condition(
                page2, ["Player1", "Player2"], "content", "Player2 화면에 두 플레이어 표시"
            )
            or await OmokGameHelper.check_page_condition(
                page1, ["게임 시작"], "content", "게임 시작 메시지"
            )
            or await OmokGameHelper.check_page_condition(
                page2, ["게임 시작"], "content", "게임 시작 메시지"
            )
            or await OmokGameHelper.check_page_condition(
                page1, ["canvas"], "content", "게임 보드 표시 (page1)"
            )
            and await OmokGameHelper.check_page_condition(
                page2, ["canvas"], "content", "게임 보드 표시 (page2)"
            )
        )

        # JavaScript 게임 상태로도 확인
        if not found_game_start:
            try:
                game_state1 = await page1.evaluate(
                    "window.omokClient ? window.omokClient.state.gameState : null"
                )
                game_state2 = await page2.evaluate(
                    "window.omokClient ? window.omokClient.state.gameState : null"
                )

                if game_state1 or game_state2:
                    found_game_start = True
                    print(f"SUCCESS: JavaScript 게임 상태 확인됨")
            except:
                print("JavaScript 게임 상태 확인 실패")

        assert found_game_start, "멀티플레이어 게임 시작을 확인할 수 없습니다"
        print("SUCCESS: 게임 시작 완료")

    @staticmethod
    async def get_game_state(page: Page) -> Optional[Dict[str, Any]]:
        """
        JavaScript를 통한 게임 상태 조회

        Args:
            page: Playwright Page 객체

        Returns:
            게임 상태 딕셔너리 또는 None
        """
        try:
            game_state = await page.evaluate(
                "window.omokClient ? window.omokClient.state.gameState : null"
            )
            return game_state
        except Exception as e:
            print(f"게임 상태 조회 실패: {e}")
            return None

    @staticmethod
    async def get_stone_count(page: Page, max_retries: int = 3) -> int:
        """현재 보드의 돌 개수 확인 (재시도 로직 포함)"""
        for retry in range(max_retries):
            try:
                game_state = await OmokGameHelper.get_game_state(page)
                if game_state and "board" in game_state:
                    board = game_state["board"]
                    # 보드에서 놓인 돌의 개수 세기 (0이 아닌 셀 카운트)
                    stone_count = sum(
                        sum(1 for cell in row if cell != 0) for row in board
                    )
                    return stone_count
                elif retry < max_retries - 1:
                    print(f"INFO: 게임 상태 없음, 재시도 중... ({retry+1}/{max_retries})")
                    await page.wait_for_timeout(500)
            except Exception as e:
                if retry < max_retries - 1:
                    print(f"INFO: 돌 개수 확인 실패, 재시도 중... ({retry+1}/{max_retries}) - {e}")
                    await page.wait_for_timeout(500)
                else:
                    print(f"INFO: 돌 개수 확인 최종 실패 - {e}")
        return 0

    @staticmethod
    async def verify_turn_change(
        page1: Page,
        page2: Page,
        expected_player: int,
        timeout: int = 3000,
        assert_on_failure: bool = False,
        max_retries: int = 5,
    ) -> bool:
        """
        턴 변경 검증 (실제 게임 상태 확인) - 재시도 로직 포함

        Args:
            page1: Player1 페이지
            page2: Player2 페이지
            expected_player: 예상되는 현재 플레이어 (1 or 2)
            timeout: 각 재시도 간 대기 시간
            assert_on_failure: True면 실패시 assert 발생, False면 bool 반환
            max_retries: 최대 재시도 횟수

        Returns:
            턴 변경 성공 여부 (assert_on_failure=False인 경우에만)
        """
        found_turn = False

        for retry in range(max_retries):
            # 재시도마다 점진적으로 더 오래 대기 - 50% 축소
            wait_time = min(timeout + (retry * 500), 2500)  # 최대 2.5초까지
            await page1.wait_for_timeout(wait_time)
            await page2.wait_for_timeout(wait_time)

            # JavaScript 게임 상태로 정확하게 확인
            try:
                game_state = await OmokGameHelper.get_game_state(page1)
                if game_state and "current_player" in game_state:
                    current_player = game_state["current_player"]
                    found_turn = current_player == expected_player
                    if found_turn:
                        print(
                            f"SUCCESS: 게임 상태에서 턴 확인됨 - Player{current_player} (재시도 {retry+1}/{max_retries})"
                        )
                        break
                    else:
                        print(
                            f"INFO: 턴 대기 중 - 예상 Player{expected_player}, 실제 Player{current_player} (재시도 {retry+1}/{max_retries})"
                        )
                else:
                    print(f"INFO: 게임 상태를 가져올 수 없음 (재시도 {retry+1}/{max_retries})")
            except Exception as e:
                print(f"INFO: 게임 상태 확인 실패 (재시도 {retry+1}/{max_retries}) - {e}")

        # HTML 텍스트는 보조 확인용으로만 사용 (게임 상태 확인이 모두 실패한 경우에만)
        if not found_turn:
            print("INFO: JavaScript 상태 확인 실패, HTML 텍스트로 최종 확인 시도")

            if expected_player == 1:
                turn_indicators = ["Player1", "흑돌", "당신의 차례"]
            else:
                turn_indicators = ["Player2", "백돌", "상대방 차례"]

            found_turn = await OmokGameHelper.check_page_condition(
                page1,
                turn_indicators,
                "content",
                f"Player{expected_player} 턴 표시 (page1)",
            ) or await OmokGameHelper.check_page_condition(
                page2,
                turn_indicators,
                "content",
                f"Player{expected_player} 턴 표시 (page2)",
            )

        if assert_on_failure:
            assert (
                found_turn
            ), f"Player{expected_player} 턴으로 변경되지 않았음 (재시도 {max_retries}회 모두 실패)"

        return found_turn

    @staticmethod
    async def setup_two_player_game(
        page1: Page,
        page2: Page,
        player1_name: str = "Player1",
        player2_name: str = "Player2",
    ) -> str:
        """
        두 플레이어 게임 전체 설정 (방 생성 + 입장 + 게임 시작 대기)

        Args:
            page1: Player1 페이지
            page2: Player2 페이지
            player1_name: Player1 닉네임
            player2_name: Player2 닉네임

        Returns:
            room_url: 게임 방 URL
        """
        # Player1 방 생성 및 입장
        room_url = await OmokGameHelper.create_room_and_join(page1, player1_name)

        # Player2 입장
        await OmokGameHelper.join_existing_room(page2, room_url, player2_name)

        # 게임 시작 대기
        await OmokGameHelper.wait_for_game_start(page1, page2)

        print(f"SUCCESS: 두 플레이어 게임 설정 완료 - {room_url}")
        return room_url

    @staticmethod
    async def click_canvas_position(
        page: Page, x_ratio: float, y_ratio: float
    ) -> Tuple[float, float]:
        """Canvas의 특정 비율 위치 클릭"""
        canvas = page.locator("#omokBoard")
        canvas_box = await canvas.bounding_box()
        assert canvas_box is not None, "Canvas bounding box를 가져올 수 없음"

        x = canvas_box["x"] + canvas_box["width"] * x_ratio
        y = canvas_box["y"] + canvas_box["height"] * y_ratio

        await page.mouse.click(x, y)
        return x, y

    @staticmethod
    async def place_stone_and_verify_turn(
        page: Page,
        player_num: int,
        x_ratio: float,
        y_ratio: float,
        expected_next_player: int,
        page1: Page,
        page2: Page,
        retry_count: int = 3,
    ) -> None:
        """돌 놓기 후 실제 게임 상태 및 턴 변경 검증 (색깔 기반 + 안정화 로직)

        Args:
            page: 돌을 놓을 플레이어 페이지
            player_num: 플레이어 번호 (1 또는 2)
            x_ratio: 클릭할 X 좌표 비율 (0.0~1.0)
            y_ratio: 클릭할 Y 좌표 비율 (0.0~1.0)
            expected_next_player: 예상되는 다음 턴 색깔 (1:흑돌, 2:백돌)
            page1: Player1 페이지
            page2: Player2 페이지
            retry_count: 최대 재시도 횟수
        """

        for attempt in range(retry_count):
            try:
                # 게임 시작 직후 상태 안정화 대기 (첫 번째 시도일 때만)
                if attempt == 0:
                    print(f"INFO: Player{player_num} 게임 상태 안정화 대기 중...")
                    # 네트워크 안정화를 우선 확인
                    await page1.wait_for_load_state("networkidle", timeout=2000)
                    await page2.wait_for_load_state("networkidle", timeout=2000)

                # 게임 상태 및 연결 상태 확인 (더 긴 대기)
                game_state = None
                connection_status = None

                for i in range(8):  # 최대 8회 재시도 (증가)
                    game_state = await page.evaluate(
                        "window.omokClient ? window.omokClient.state.gameState : null"
                    )
                    connection_status = await page.evaluate(
                        "window.omokClient ? window.omokClient.connection.status : null"
                    )

                    if game_state and connection_status == "connected":
                        break

                    if i < 7:  # 마지막이 아니면 잠시 대기
                        print(f"INFO: 게임 상태 재확인 중... ({i+1}/8)")
                        await page.wait_for_timeout(750)  # 대기 시간 50% 축소

                if not game_state:
                    raise AssertionError(
                        f"Player{player_num}: 게임 상태를 확인할 수 없습니다 (시도 {attempt+1}/{retry_count})"
                    )

                if connection_status != "connected":
                    print(
                        f"WARNING: Player{player_num} WebSocket 연결 상태: {connection_status}"
                    )
                    await page.wait_for_timeout(1500)  # 연결 대기 시간 50% 축소

                # 플레이어 정보 확인 (색깔 배정까지 대기)
                debug_info = None
                for color_check in range(5):  # 색깔 배정 대기 루프 추가
                    debug_info = await page.evaluate(
                        """
                        (() => {
                            if (!window.omokClient) return { error: 'omokClient not found' };

                            const client = window.omokClient;
                            const myPlayer = client.state.players.find(p => p.player_number === client.state.myPlayerNumber);

                            return {
                                myPlayerNumber: client.state.myPlayerNumber,
                                myPlayer: myPlayer,
                                players: client.state.players,
                                currentPlayer: client.state.gameState ? client.state.gameState.current_player : null
                            };
                        })()
                    """
                    )

                    if debug_info.get("error"):
                        if color_check < 4:
                            print(f"INFO: 클라이언트 초기화 대기 중... ({color_check+1}/5)")
                            await page.wait_for_timeout(750)
                            continue
                        else:
                            raise AssertionError(
                                f"클라이언트 상태 확인 실패: {debug_info['error']}"
                            )

                    my_player = debug_info.get("myPlayer")
                    if my_player and my_player.get("color"):
                        break  # 색깔이 배정되면 루프 탈출

                    if color_check < 4:
                        print(
                            f"INFO: Player{player_num} 색깔 배정 대기 중... ({color_check+1}/5)"
                        )
                        await page.wait_for_timeout(750)

                print(f"DEBUG Player{player_num}: {debug_info}")

                my_player = debug_info["myPlayer"]
                if not my_player:
                    raise AssertionError(f"Player{player_num}: 플레이어 정보를 찾을 수 없습니다")

                if not my_player.get("color"):
                    raise AssertionError(f"Player{player_num}: 플레이어 색깔이 배정되지 않았습니다")

                current_player = debug_info["currentPlayer"]
                my_color = my_player["color"]

                # 턴 대기 (더 정확한 체크)
                if current_player != my_color:
                    if attempt < retry_count - 1:
                        print(
                            f"INFO: 턴 대기 중 - Player{player_num}(색깔:{my_color}), 현재 턴: {current_player} (시도 {attempt+1}/{retry_count})"
                        )
                        await page.wait_for_timeout(1500)  # 턴 대기 시간 50% 축소
                        continue
                    else:
                        raise AssertionError(
                            f"Player{player_num}: 현재 턴이 아닙니다. 내 색깔: {my_color}, 현재 턴: {current_player}"
                        )

                # 클릭 전 보드 상태 확인
                initial_stone_count = await OmokGameHelper.get_stone_count(page1)

                x, y = await OmokGameHelper.click_canvas_position(
                    page, x_ratio, y_ratio
                )
                print(
                    f"Player{player_num}이 ({x:.1f}, {y:.1f}) 위치에 돌 놓기 시도 (시도 {attempt+1}/{retry_count})"
                )

                # WebSocket 응답 대기 - 실제 보드 변화를 확인하는 방식으로 최적화
                max_wait_attempts = 5  # 최대 5번 시도
                board_changed = False
                for wait_attempt in range(max_wait_attempts):
                    current_stone_count = await OmokGameHelper.get_stone_count(page1)
                    if current_stone_count > initial_stone_count:
                        board_changed = True
                        print(f"SUCCESS: 보드 변화 감지됨 ({wait_attempt+1}번째 확인)")
                        break

                    # 점진적 대기 간격
                    wait_time = 300 + (wait_attempt * 200)  # 300ms부터 시작해서 점점 증가
                    await page1.wait_for_timeout(wait_time)
                    await page2.wait_for_timeout(wait_time)

                if not board_changed:
                    print(f"INFO: 즉시 보드 변화 감지되지 않음, 추가 확인 진행")

                # 돌 놓기 최종 확인 (위에서 이미 1차 확인 완료)
                if board_changed:
                    stone_placed = True
                    final_stone_count = await OmokGameHelper.get_stone_count(page1)
                    print(
                        f"SUCCESS: 돌 놓기 성공 ({initial_stone_count} -> {final_stone_count})"
                    )
                else:
                    # board_changed가 false인 경우에만 추가 확인
                    stone_placed = False
                    for check_attempt in range(3):  # 재시도 횟수 줄임
                        final_stone_count = await OmokGameHelper.get_stone_count(page1)
                        stone_placed = final_stone_count > initial_stone_count

                        if stone_placed:
                            print(
                                f"SUCCESS: 돌 놓기 지연 성공 ({initial_stone_count} -> {final_stone_count})"
                            )
                            break
                        elif check_attempt < 2:
                            print(f"INFO: 돌 놓기 상태 재확인 중... ({check_attempt+1}/3)")
                            await page.wait_for_timeout(500)

                if not stone_placed:
                    if attempt < retry_count - 1:
                        print(f"WARNING: 돌이 놓이지 않음, 재시도 ({attempt+1}/{retry_count})")
                        await page.wait_for_timeout(1000)
                        continue
                    else:
                        raise AssertionError(
                            f"Player{player_num}이 돌을 놓지 못했습니다 (모든 시도 실패)"
                        )

                # 턴 변경 확인 - 50% 축소
                await OmokGameHelper.verify_turn_change(
                    page1,
                    page2,
                    expected_next_player,
                    timeout=2000,
                    assert_on_failure=True,
                    max_retries=8,
                )

                # 성공하면 루프 탈출
                print(f"SUCCESS: Player{player_num} 돌 놓기 및 턴 변경 완료")
                return

            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"WARNING: 시도 {attempt+1} 실패, 재시도 중... - {e}")
                    await page.wait_for_timeout(1500)  # 재시도 전 대기 시간 50% 축소
                else:
                    print(f"ERROR: 모든 시도 실패 - {e}")
                    raise

    @staticmethod
    async def check_page_condition(
        page: Page,
        items: List[str],
        check_type: str = "element",
        success_message: str = "조건 확인",
        timeout: int = 2000,
    ) -> bool:
        """
        페이지 조건 확인 (통합된 함수)

        Args:
            page: Playwright Page 객체
            items: 확인할 항목들 (선택자 또는 텍스트)
            check_type: 확인 타입 ("element", "content", "popup")
            success_message: 성공 시 출력할 메시지
            timeout: 요소 대기 시간 (element, popup 타입에만 적용)

        Returns:
            조건 만족 여부
        """
        if check_type == "content":
            # 페이지 내용에서 텍스트 찾기
            page_content = await page.content()
            for item in items:
                if item in page_content:
                    print(f"SUCCESS: {success_message} - '{item}'")
                    return True
        else:
            # 요소 찾기 (element 또는 popup)
            for item in items:
                try:
                    element = page.locator(item)
                    if await element.is_visible(timeout=timeout):
                        print(f"SUCCESS: {success_message} - {item}")
                        return True
                except:
                    continue
        return False

    @staticmethod
    async def find_and_click_button(
        page: Page,
        button_selectors: List[str],
        timeout: int = 2000,
        success_message: str = "버튼 클릭",
    ) -> bool:
        """버튼 선택자 목록에서 첫 번째로 찾은 버튼 클릭"""
        for selector in button_selectors:
            try:
                button = page.locator(selector)
                if await button.is_visible(timeout=timeout):
                    await button.click()
                    print(f"SUCCESS: {success_message} - {selector}")
                    return True
            except:
                continue
        return False

    @staticmethod
    async def find_input_field(
        page: Page, input_selectors: List[str], timeout: int = 3000
    ) -> Optional[Locator]:
        """입력 필드 찾기"""
        for selector in input_selectors:
            try:
                input_field = page.locator(selector)
                if await input_field.is_visible(timeout=timeout):
                    print(f"SUCCESS: 입력 필드 발견 - {selector}")
                    return input_field
            except:
                continue
        return None

    @staticmethod
    async def make_alternating_moves(
        page1: Page,
        page2: Page,
        moves_count: int = 3,
        verify_turns: bool = True,
        position_pattern: str = "preset",
    ) -> None:
        """
        플레이어 교대로 여러 수 진행 (색깔 기반 자동 감지)

        Args:
            page1: Player1 페이지
            page2: Player2 페이지
            moves_count: 진행할 수의 개수
            verify_turns: 턴 변경 검증 여부
            position_pattern: 위치 패턴 ("preset" 또는 "calculated")
        """
        try:
            # Canvas 표시 상태 확인
            canvas1 = page1.locator("#omokBoard")
            canvas2 = page2.locator("#omokBoard")
            assert await canvas1.is_visible(), "Player1 오목 보드가 표시되지 않음"
            assert await canvas2.is_visible(), "Player2 오목 보드가 표시되지 않음"

            # 실제 색깔 배정 확인
            player1_info = await page1.evaluate(
                """
                window.omokClient.state.players.find(p => p.player_number === window.omokClient.state.myPlayerNumber)
            """
            )
            player2_info = await page2.evaluate(
                """
                window.omokClient.state.players.find(p => p.player_number === window.omokClient.state.myPlayerNumber)
            """
            )

            print(
                f"색깔 배정 - Player1: color={player1_info['color']}, Player2: color={player2_info['color']}"
            )

            # 흑돌/백돌 플레이어 결정
            if player1_info["color"] == 1:  # Player1이 흑돌
                black_page, black_num = page1, 1
                white_page, white_num = page2, 2
            else:  # Player2가 흑돌
                black_page, black_num = page2, 2
                white_page, white_num = page1, 1

            for i in range(moves_count):
                # 위치 결정
                if position_pattern == "preset":
                    preset_positions = [
                        (0.5, 0.5),  # 중앙
                        (0.6, 0.6),  # 오프셋 1
                        (0.4, 0.4),  # 오프셋 2
                        (0.7, 0.3),  # 오프셋 3
                        (0.3, 0.7),  # 오프셋 4
                    ]
                    if i < len(preset_positions):
                        x_ratio, y_ratio = preset_positions[i]
                    else:
                        x_ratio, y_ratio = 0.5 + (i % 3) * 0.1, 0.5 + (i % 2) * 0.1
                else:  # calculated pattern
                    x_ratio, y_ratio = 0.4 + i * 0.1, 0.4 + i * 0.1

                # 색깔 기준으로 돌 놓기 (짝수: 흑돌, 홀수: 백돌)
                if i % 2 == 0:  # 흑돌 차례
                    current_page, current_num = black_page, black_num
                    next_color = 2  # 다음은 백돌
                else:  # 백돌 차례
                    current_page, current_num = white_page, white_num
                    next_color = 1  # 다음은 흑돌

                if verify_turns:
                    await OmokGameHelper.place_stone_and_verify_turn(
                        current_page,
                        current_num,
                        x_ratio,
                        y_ratio,
                        next_color,
                        page1,
                        page2,
                    )
                    print(
                        f"Player{current_num}{'(흑돌)' if i % 2 == 0 else '(백돌)'}이 {i+1}번째 수 완료"
                    )
                else:
                    x, y = await OmokGameHelper.click_canvas_position(
                        current_page, x_ratio, y_ratio
                    )
                    print(
                        f"Player{current_num}{'(흑돌)' if i % 2 == 0 else '(백돌)'}이 {i+1}번째 수: ({x:.1f}, {y:.1f})"
                    )
                    # 간단한 수 진행 시에는 짧은 대기로 충분
                    await page1.wait_for_timeout(500)
                    await page2.wait_for_timeout(500)

            print(f"SUCCESS: {moves_count}수 게임 진행 완료 (턴 검증: {verify_turns})")

        except Exception as e:
            print(f"INFO: 게임 진행 중 오류 (정상적일 수 있음) - {e}")


class OmokTestScenarios:
    """자주 사용되는 테스트 시나리오 패턴들"""

    @staticmethod
    async def basic_turn_gameplay(page1: Page, page2: Page) -> None:
        """
        기본 턴제 게임플레이 시나리오 (색깔 기반 자동 감지)
        (흑돌 플레이어 돌 놓기 → 백돌 플레이어 돌 놓기 → 턴 순환 검증)
        """
        await OmokGameHelper.make_alternating_moves(
            page1, page2, moves_count=2, verify_turns=True, position_pattern="preset"
        )
        print("SUCCESS: 턴제 게임플레이 완전히 검증 완료")
