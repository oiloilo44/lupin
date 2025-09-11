"""
오목 E2E 테스트용 액션 헬퍼 클래스

JavaScript 기반의 안정적인 DOM 조작 및 사용자 상호작용을 제공합니다.
모든 DOM 조작은 신뢰성 높은 JavaScript 실행 방식으로 구현됩니다.
"""

from playwright.async_api import Page


class ActionHelper:
    """JavaScript 기반 사용자 액션을 담당하는 헬퍼 클래스"""

    @staticmethod
    async def js_click(page: Page, selector: str) -> None:
        """JavaScript로 요소를 안정적으로 클릭합니다.

        Args:
            page: Playwright Page 객체
            selector: CSS 셀렉터

        Raises:
            TimeoutError: 요소 대기 시간 초과
        """
        from tests.conftest import TEST_CONFIG

        await page.wait_for_selector(
            selector, state="visible", timeout=TEST_CONFIG["element_wait"]
        )
        await page.evaluate(f"document.querySelector('{selector}').click()")

    @staticmethod
    async def type_text(page: Page, selector: str, text: str) -> None:
        """텍스트 입력 (기존 conftest.py 구조 활용)

        Args:
            page: Playwright Page 객체
            selector: CSS 셀렉터
            text: 입력할 텍스트

        Raises:
            TimeoutError: 요소 대기 시간 초과
        """
        from tests.conftest import TEST_CONFIG

        await page.wait_for_selector(selector, timeout=TEST_CONFIG["element_wait"])
        await page.fill(selector, text)

    @staticmethod
    async def place_stone_by_js(page: Page, x: int, y: int) -> None:
        """Canvas 좌표를 계산하여 JavaScript로 클릭 이벤트를 발생시킵니다.

        실제 확인된 Canvas 좌표 계산 공식을 사용합니다:
        - boardSize: 450px (고정)
        - cellSize: (450 - 60) / 14 = 27.857...
        - margin: 30px

        Args:
            page: Playwright Page 객체
            x: 보드 X 좌표 (0-14)
            y: 보드 Y 좌표 (0-14)
        """
        script = f"""
        const canvas = document.getElementById('omokBoard');
        const rect = canvas.getBoundingClientRect();
        const boardSize = Math.min(canvas.width, canvas.height);  // 450
        const cellSize = (boardSize - 60) / 14;  // 27.857...
        const margin = (boardSize - cellSize * 14) / 2;  // 30
        const clickX = rect.left + margin + {x} * cellSize;
        const clickY = rect.top + margin + {y} * cellSize;
        const clickEvent = new MouseEvent('click', {{
            clientX: clickX, clientY: clickY
        }});
        canvas.dispatchEvent(clickEvent);
        """
        await page.evaluate(script)
