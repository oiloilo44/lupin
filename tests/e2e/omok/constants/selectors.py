"""오목 E2E 테스트용 CSS 셀렉터 상수들

계획서(E2E-Test-Redesign-Plan.md)의 '확인된 CSS 셀렉터' 섹션을 기반으로 구현
실제 서버(localhost:8003)에서 Playwright MCP로 확인된 값들
"""


class OmokSelectors:
    """오목 게임 관련 CSS 셀렉터 상수 클래스"""

    class GameBoard:
        """게임 보드 관련 셀렉터"""

        CANVAS = "#omokBoard"  # 게임 보드 캔버스

    class Buttons:
        """버튼 관련 셀렉터"""

        UNDO = 'button:has-text("무르기")'
        RESTART = 'button:has-text("다시하기")'
        LEAVE_ROOM = 'button:has-text("방 나가기")'
        SEND_CHAT = 'button:has-text("전송")'
        STEALTH_MODE = 'button:has-text("업무모드")'  # .quick-hide 클래스

        # 게임 입장 관련
        GAME_ENTRY = 'button:has-text("게임 입장")'
        GAME_JOIN = 'button:has-text("게임 참여")'

    class Inputs:
        """입력 필드 관련 셀렉터"""

        NICKNAME = "#nicknameInput"
        CHAT_MESSAGE = "#chatInput"
        OPACITY_SLIDER = "#opacitySlider"

    class Modal:
        """모달 관련 셀렉터"""

        OVERLAY = ".modal-overlay"  # 모달 오버레이
        TITLE_UNDO_REQUEST = 'h3:has-text("무르기 요청")'  # .modal-title 클래스
        BUTTON_AGREE = ".modal-button.success"  # "동의" 버튼
        BUTTON_REJECT = ".modal-button.secondary"  # "거부" 버튼

    class GameRoom:
        """게임방 관련 셀렉터"""

        CURRENT_TURN = 'h4:has-text("현재 턴")'
        PLAYERS_HEADER = 'h4:has-text("플레이어")'
        ROOM_URL_INPUT = "input[readonly]"  # 방 URL 표시 필드

    class Homepage:
        """홈페이지 관련 셀렉터"""

        OMOK_GAME_CARD = '.game-card:has-text("오목")'
        CREATE_ROOM_OPTION = '.option-card:has-text("방 만들기")'
        JOIN_ROOM_OPTION = '.option-card:has-text("방 참여하기")'

    class GameFlow:
        """게임 플로우 관련 셀렉터"""

        GAME_PARTICIPATE_TITLE = 'h3:has-text("오목 게임 참여")'
        EXISTING_GAME_FOUND = 'h3:has-text("기존 게임 발견")'
        NEW_GAME_BUTTON = 'button:has-text("새 게임")'
        CONTINUE_GAME_BUTTON = 'button:has-text("이어하기")'
