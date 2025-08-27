/**
 * 오목 게임 클라이언트 - 모듈화된 JavaScript
 * 클래스 기반 상태 관리 및 서버-클라이언트 통신
 */

class OmokGameClient {
    constructor(roomId, sessionId, initialGameState = null, playerData = null) {
        this.roomId = roomId;
        this.sessionId = sessionId;
        this.ws = null;
        this.canvas = document.getElementById('omokBoard');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;

        // 게임 상태 - 서버에서 전달된 초기 상태 사용
        this.state = {
            gameState: initialGameState || {
                board: Array(15).fill(null).map(() => Array(15).fill(0)),
                current_player: 1
            },
            myPlayerNumber: playerData ? playerData.player_number : null,
            players: [],
            gameEnded: false,
            gameStarted: false,
            waitingForRestart: false,
            lastMove: null,
            hoverPosition: null,
            winningLine: null,
            gameStats: { moves: 0, startTime: null },
            waitingForUndo: false,
            winnerNumber: null,
            myNickname: playerData ? playerData.nickname : null,
            moveHistory: [], // 수 기록 관리
            // 모바일 터치 미리보기 시스템
            previewStone: null,  // {x, y, color}
            isDragging: false,
            showingConfirmButtons: false
        };

        // 연결 상태
        this.connection = {
            status: 'disconnected',
            reconnectAttempts: 0,
            maxReconnectAttempts: 5,
            reconnectTimeout: null
        };

        // 게임 타이머
        this.gameTimer = null;

        // 세션 데이터
        this.pendingSessionData = null;
    }

    initialize() {
        if (!this.canvas || !this.ctx) {
            console.error('Canvas element not found');
            return;
        }

        this.setupEventListeners();
        this.checkExistingSession();
        this.drawBoard();
        this.startGameTimer();
        this.adjustMobileLayout();
    }

    setupEventListeners() {
        // 캔버스 이벤트
        this.canvas.addEventListener('click', (e) => this.handleGameMove(e));
        this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
        this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
        this.canvas.addEventListener('mousemove', (e) => this.handleHover(e));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
        this.canvas.addEventListener('mouseleave', () => this.clearHover());
        this.canvas.addEventListener('touchcancel', () => this.clearHover());

        // 우클릭 메뉴 방지 (모바일에서 롱터치 메뉴 방지)
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

        // 윈도우 이벤트
        window.addEventListener('resize', () => this.adjustMobileLayout());
        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.adjustMobileLayout(), 100);
        });

        // 페이지 이동 전 정리 작업
        this.handleBeforeUnload = () => this.cleanup();
        window.addEventListener('beforeunload', this.handleBeforeUnload);

        // 터치 위치 추적용 변수
        this.touchStartPos = null;
        this.touchStartTime = null;

        // 모바일 확정 버튼 이벤트
        const confirmButton = document.getElementById('confirmMoveButton');
        const cancelButton = document.getElementById('cancelMoveButton');

        if (confirmButton) {
            confirmButton.addEventListener('click', () => this.confirmMove());
        }
        if (cancelButton) {
            cancelButton.addEventListener('click', () => this.cancelMove());
        }
    }

    // HTML 이스케이프 함수 (XSS 방지)
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 연결 상태 업데이트 - 개선된 UI
    updateConnectionStatus(status, text) {
        this.connection.status = status;
        const statusElement = document.getElementById('connectionStatus');
        const iconElement = document.getElementById('connectionIcon');
        const textElement = document.getElementById('connectionText');

        if (status === 'connected') {
            statusElement.style.display = 'none';
        } else {
            statusElement.style.display = 'block';
            statusElement.className = `connection-status ${status}`;

            // 이모지 대신 CSS 스타일로 상태 표시
            if (status === 'disconnected') {
                iconElement.className = 'status-icon disconnected';
                iconElement.textContent = '●';
                textElement.textContent = text || '연결 끊김';

                // 심각한 연결 문제인 경우 추가 정보 제공
                if (this.connection.reconnectAttempts >= 3) {
                    textElement.innerHTML = `
                        ${text || '연결 끊김'}<br>
                        <small class="connection-help">네트워크 상태를 확인하거나 페이지를 새로고침해주세요</small>
                    `;
                }
            } else if (status === 'reconnecting') {
                iconElement.className = 'status-icon reconnecting';
                iconElement.textContent = '●';
                textElement.textContent = text || '재연결 시도 중...';

                // 재연결 진행률 표시
                if (this.connection.reconnectAttempts > 0) {
                    const progress = Math.round((this.connection.reconnectAttempts / this.connection.maxReconnectAttempts) * 100);
                    textElement.innerHTML = `
                        ${text || '재연결 시도 중...'}<br>
                        <div class="reconnect-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${progress}%"></div>
                            </div>
                        </div>
                    `;
                }
            } else if (status === 'connecting') {
                iconElement.className = 'status-icon connecting';
                iconElement.textContent = '●';
                textElement.textContent = text || '연결 중...';
            }
        }
    }

    // WebSocket 연결
    connectWebSocket(isReconnect = false) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${this.roomId}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.updateConnectionStatus('connected');
                this.connection.reconnectAttempts = 0;

                // 채팅 연결 설정
                if (this.state.myNickname && typeof setupChatConnection === 'function') {
                    setupChatConnection(this.ws, this.state.myNickname);
                }

                if (isReconnect) {
                    const message = {
                        type: 'reconnect',
                        session_id: this.sessionId
                    };
                    this.ws.send(JSON.stringify(message));
                }
            };

            this.ws.onmessage = (event) => this.handleWebSocketMessage(event);
            this.ws.onclose = (event) => this.handleWebSocketClose(event);
            this.ws.onerror = (error) => this.handleWebSocketError(error);

        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.handleConnectionFailure();
        }
    }

    // 재연결 로직 - 개선된 지수 백오프
    attemptReconnect() {
        if (this.connection.reconnectAttempts >= this.connection.maxReconnectAttempts) {
            this.updateConnectionStatus('disconnected', '재연결 실패');
            this.showReconnectionFailedDialog();
            return;
        }

        this.connection.reconnectAttempts++;
        // 개선된 지수 백오프: 1s, 2s, 4s, 8s, 15s, 30s
        const baseDelay = 1000;
        const exponentialDelay = baseDelay * Math.pow(2, this.connection.reconnectAttempts - 1);
        const jitterDelay = exponentialDelay + Math.random() * 1000; // 지터 추가
        const finalDelay = Math.min(jitterDelay, 30000); // 최대 30초

        this.updateConnectionStatus('reconnecting',
            `재연결 시도 중... (${this.connection.reconnectAttempts}/${this.connection.maxReconnectAttempts})`
        );

        // 재연결 진행 상황을 토스트로 표시
        const delaySeconds = Math.ceil(finalDelay / 1000);
        showGlobalToast(
            '재연결 시도',
            `${delaySeconds}초 후 다시 연결을 시도합니다`,
            'info',
            Math.min(finalDelay - 500, 4000)
        );

        this.connection.reconnectTimeout = setTimeout(() => {
            this.connectWebSocket(true);
        }, finalDelay);
    }

    // 재연결 실패 다이얼로그
    showReconnectionFailedDialog() {
        this.showModal('연결 실패',
            `서버와의 연결을 복구할 수 없습니다.<br><br>` +
            `<strong>해결 방법:</strong><br>` +
            `• 네트워크 연결 상태를 확인해주세요<br>` +
            `• 페이지를 새로고침하거나 잠시 후 다시 시도해주세요`,
            [
                {
                    text: '수동 재시도',
                    class: 'secondary',
                    onclick: () => {
                        hideModal();
                        this.manualReconnect();
                    }
                },
                { text: '새로고침', class: 'primary', onclick: () => location.reload() },
                { text: '메인으로', class: 'secondary', onclick: () => window.location.href = '/' }
            ]
        );
    }

    // 수동 재연결
    manualReconnect() {
        // 재연결 상태 초기화
        this.connection.reconnectAttempts = 0;
        if (this.connection.reconnectTimeout) {
            clearTimeout(this.connection.reconnectTimeout);
            this.connection.reconnectTimeout = null;
        }

        showGlobalToast('재연결 시도', '수동으로 재연결을 시도합니다', 'info');
        this.connectWebSocket(true);
    }

    // WebSocket 정리 메서드
    cleanupWebSocket() {
        if (this.ws) {
            // 이벤트 핸들러 제거
            this.ws.onopen = null;
            this.ws.onmessage = null;
            this.ws.onclose = null;
            this.ws.onerror = null;

            // WebSocket 상태가 연결 중이거나 열린 상태인 경우에만 close 호출
            if (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN) {
                try {
                    this.ws.close(1000, 'Client cleanup');
                } catch (error) {
                    console.warn('WebSocket close error during cleanup:', error);
                }
            }

            this.ws = null;
        }

        // 재연결 타이머 정리
        if (this.connection.reconnectTimeout) {
            clearTimeout(this.connection.reconnectTimeout);
            this.connection.reconnectTimeout = null;
        }

        // 연결 상태 초기화
        this.connection.status = 'disconnected';
        this.connection.reconnectAttempts = 0;
    }

    // 게임 정리 메서드 (페이지 이동 시 호출)
    cleanup() {
        this.cleanupWebSocket();

        // 게임별 정리 작업
        if (this.gameState && this.gameState.status === 'playing') {
            this.saveGameSession({
                nickname: this.nickname,
                sessionId: this.sessionId,
                player_number: this.state.myPlayerNumber,
                roomId: this.roomId,
                joinedAt: Date.now()
            });
        }

        // 이벤트 리스너 제거
        this.removeEventListeners();
    }

    // 이벤트 리스너 제거
    removeEventListeners() {
        if (this.canvas) {
            this.canvas.removeEventListener('click', this.handleCanvasClick);
            this.canvas.removeEventListener('touchstart', this.handleTouchStart);
            this.canvas.removeEventListener('touchmove', this.handleTouchMove);
            this.canvas.removeEventListener('touchend', this.handleTouchEnd);
        }

        window.removeEventListener('beforeunload', this.handleBeforeUnload);
        window.removeEventListener('resize', this.handleResize);
    }

    handleWebSocketClose(event) {

        if (event.code === 1000) {
            this.updateConnectionStatus('disconnected', '연결 종료');
            return;
        }

        this.updateConnectionStatus('disconnected', '연결 끊김');

        if (this.connection.reconnectTimeout) {
            clearTimeout(this.connection.reconnectTimeout);
        }

        setTimeout(() => this.attemptReconnect(), 1000);
    }

    handleWebSocketError(error) {
        console.error('WebSocket error:', error);
    }

    handleConnectionFailure() {
        this.updateConnectionStatus('disconnected', '연결 실패');
        setTimeout(() => this.attemptReconnect(), 2000);
    }

    // 오목판 그리기
    drawBoard() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        const boardSize = Math.min(this.canvas.width, this.canvas.height);
        const cellSize = (boardSize - 60) / 14;
        const margin = (boardSize - cellSize * 14) / 2;

        // 배경
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // 격자 그리기
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = Math.max(1, cellSize / 30);

        for (let i = 0; i < 15; i++) {
            // 세로선
            this.ctx.beginPath();
            this.ctx.moveTo(margin + i * cellSize, margin);
            this.ctx.lineTo(margin + i * cellSize, boardSize - margin);
            this.ctx.stroke();

            // 가로선
            this.ctx.beginPath();
            this.ctx.moveTo(margin, margin + i * cellSize);
            this.ctx.lineTo(boardSize - margin, margin + i * cellSize);
            this.ctx.stroke();
        }

        // 중심점 그리기
        const centerPoints = [[7, 7], [3, 3], [3, 11], [11, 3], [11, 11]];
        this.ctx.fillStyle = '#000';
        centerPoints.forEach(([x, y]) => {
            this.ctx.beginPath();
            this.ctx.arc(margin + x * cellSize, margin + y * cellSize, Math.max(2, cellSize / 10), 0, 2 * Math.PI);
            this.ctx.fill();
        });

        // 모바일 터치 미리보기 돌
        if (this.state.previewStone) {
            const px = this.state.previewStone.x;
            const py = this.state.previewStone.y;
            if (px >= 0 && px < 15 && py >= 0 && py < 15 && this.state.gameState.board[py][px] === 0) {
                const stoneRadius = Math.max(8, cellSize * 0.4);
                this.ctx.beginPath();
                this.ctx.arc(margin + px * cellSize, margin + py * cellSize, stoneRadius, 0, 2 * Math.PI);
                this.ctx.fillStyle = this.state.previewStone.color === 1 ? 'rgba(0, 0, 0, 0.5)' : 'rgba(255, 255, 255, 0.7)';
                this.ctx.fill();
                this.ctx.strokeStyle = this.state.previewStone.color === 1 ? 'rgba(0, 0, 0, 0.7)' : 'rgba(51, 51, 51, 0.7)';
                this.ctx.lineWidth = Math.max(2, cellSize / 20);
                this.ctx.stroke();
            }
        }

        // 마우스 오버 미리보기 (데스크톱용)
        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
        if (this.state.hoverPosition && !this.state.gameEnded && this.state.players.length === 2 &&
            myPlayer && this.state.gameState.current_player === myPlayer.color && !this.state.previewStone) {
            const [hx, hy] = this.state.hoverPosition;
            if (this.state.gameState.board[hy][hx] === 0) {
                const stoneRadius = Math.max(8, cellSize * 0.4);
                this.ctx.beginPath();
                this.ctx.arc(margin + hx * cellSize, margin + hy * cellSize, stoneRadius, 0, 2 * Math.PI);
                this.ctx.fillStyle = this.state.gameState.current_player === 1 ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.5)';
                this.ctx.fill();
                this.ctx.strokeStyle = this.state.gameState.current_player === 1 ? 'rgba(0, 0, 0, 0.5)' : 'rgba(51, 51, 51, 0.5)';
                this.ctx.lineWidth = Math.max(1, cellSize / 30);
                this.ctx.stroke();
            }
        }

        // 돌 그리기
        const stoneRadius = Math.max(8, cellSize * 0.4);
        for (let y = 0; y < 15; y++) {
            for (let x = 0; x < 15; x++) {
                if (this.state.gameState.board[y][x] !== 0) {
                    this.ctx.save();

                    const centerX = margin + x * cellSize;
                    const centerY = margin + y * cellSize;

                    this.ctx.beginPath();
                    this.ctx.arc(centerX, centerY, stoneRadius, 0, 2 * Math.PI);
                    this.ctx.fillStyle = this.state.gameState.board[y][x] === 1 ? '#000' : '#fff';
                    this.ctx.fill();
                    this.ctx.strokeStyle = '#333';
                    this.ctx.lineWidth = Math.max(1, cellSize / 30);
                    this.ctx.stroke();

                    // 최근 둔 수 강조
                    if (this.state.lastMove && this.state.lastMove.x === x && this.state.lastMove.y === y) {
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * 1.25, 0, 2 * Math.PI);
                        this.ctx.strokeStyle = '#ff4444';
                        this.ctx.lineWidth = Math.max(2, cellSize / 15);
                        this.ctx.stroke();
                    }

                    // 승리 라인 강조
                    if (this.state.winningLine && this.state.winningLine.some(pos => pos.x === x && pos.y === y)) {
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * 1.5, 0, 2 * Math.PI);
                        this.ctx.strokeStyle = '#ffd700';
                        this.ctx.lineWidth = Math.max(3, cellSize / 10);
                        this.ctx.stroke();

                        // 반짝이는 효과
                        const time = Date.now();
                        const pulse = Math.sin(time / 200) * 0.3 + 0.7;
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * pulse, 0, 2 * Math.PI);
                        this.ctx.fillStyle = this.state.gameState.board[y][x] === 1 ?
                            `rgba(255, 215, 0, ${0.3 * pulse})` :
                            `rgba(255, 215, 0, ${0.2 * pulse})`;
                        this.ctx.fill();
                    }

                    this.ctx.restore();
                }
            }
        }
    }

    // 이벤트 위치 계산
    getEventPosition(e) {
        const rect = this.canvas.getBoundingClientRect();
        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);

        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        const canvasX = (clientX - rect.left) * scaleX;
        const canvasY = (clientY - rect.top) * scaleY;

        const boardSize = Math.min(this.canvas.width, this.canvas.height);
        const cellSize = (boardSize - 60) / 14;
        const margin = (boardSize - cellSize * 14) / 2;

        return {
            x: Math.round((canvasX - margin) / cellSize),
            y: Math.round((canvasY - margin) / cellSize)
        };
    }

    // 마우스 호버 처리
    handleHover(e) {
        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
        if (!this.ws || this.state.players.length < 2 || !myPlayer ||
            this.state.gameState.current_player !== myPlayer.color || this.state.gameEnded) {
            this.state.hoverPosition = null;
            this.drawBoard();
            return;
        }

        const pos = this.getEventPosition(e);
        const x = pos.x;
        const y = pos.y;

        if (x >= 0 && x < 15 && y >= 0 && y < 15) {
            this.state.hoverPosition = [x, y];
            this.drawBoard();
        }
    }

    clearHover() {
        this.state.hoverPosition = null;
        this.drawBoard();
    }

    // 터치 시작 처리
    handleTouchStart(e) {
        e.preventDefault();
        const touch = e.touches[0];
        this.touchStartPos = this.getEventPosition(touch);
        this.touchStartTime = Date.now();
        this.state.isDragging = false;
    }

    // 터치 이동 처리
    handleTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const currentPos = this.getEventPosition(touch);

            // 미리보기 돌이 있는 경우 드래그로 위치 조정
            if (this.state.previewStone && this.touchStartPos) {
                const dragDistance = Math.abs(currentPos.x - this.touchStartPos.x) +
                                   Math.abs(currentPos.y - this.touchStartPos.y);

                // 드래그가 시작되었거나 이미 드래그 중이면 위치 업데이트
                if (dragDistance > 0 || this.state.isDragging) {
                    this.state.isDragging = true;
                    this.updatePreviewStone(currentPos.x, currentPos.y);
                }
            } else {
                // 일반 호버 효과 (데스크톱 호환)
                this.handleHover(touch);
            }
        }
    }

    // 터치 종료 처리
    handleTouchEnd(e) {
        e.preventDefault();

        // 터치 시작 위치와 시간 확인
        if (!this.touchStartPos || !this.touchStartTime) return;

        const touchDuration = Date.now() - this.touchStartTime;
        const endTouch = e.changedTouches[0];
        const endPos = this.getEventPosition(endTouch);

        // 미리보기 돌이 있는 경우 처리
        if (this.state.previewStone) {
            // 드래그 중이었다면 위치만 업데이트
            if (this.state.isDragging) {
                this.updatePreviewStone(endPos.x, endPos.y);
            } else {
                // 드래그가 아닌 단순 터치의 경우 미리보기 해제
                const isDrag = Math.abs(endPos.x - this.touchStartPos.x) > 1 ||
                               Math.abs(endPos.y - this.touchStartPos.y) > 1;

                if (!isDrag && touchDuration < 500) {
                    // 미리보기 해제
                    this.cancelMove();
                }
            }
        } else {
            // 새로운 미리보기 돌 생성 (탭 동작)
            const isDrag = Math.abs(endPos.x - this.touchStartPos.x) > 1 ||
                           Math.abs(endPos.y - this.touchStartPos.y) > 1;

            if (!isDrag && touchDuration < 500) {
                this.showPreviewStone(endPos.x, endPos.y);
                this.showTouchFeedback(endPos.x, endPos.y);
            }
        }

        this.touchStartPos = null;
        this.touchStartTime = null;
        this.state.isDragging = false;
        this.clearHover();
    }

    // 터치 피드백 애니메이션
    showTouchFeedback(x, y) {
        if (x >= 0 && x < 15 && y >= 0 && y < 15) {
            // Canvas에 임시 하이라이트 효과
            const boardSize = Math.min(this.canvas.width, this.canvas.height);
            const cellSize = (boardSize - 60) / 14;
            const margin = (boardSize - cellSize * 14) / 2;

            const pixelX = margin + x * cellSize;
            const pixelY = margin + y * cellSize;

            this.ctx.save();
            this.ctx.strokeStyle = '#3b82f6';
            this.ctx.lineWidth = 3;
            this.ctx.globalAlpha = 0.5;
            this.ctx.beginPath();
            this.ctx.arc(pixelX, pixelY, cellSize / 3, 0, Math.PI * 2);
            this.ctx.stroke();
            this.ctx.restore();

            // 200ms 후 보드 다시 그리기
            setTimeout(() => this.drawBoard(), 200);
        }
    }

    // 게임 이동 처리
    handleGameMove(e) {
        // 터치 디바이스에서는 미리보기 시스템 사용, 마우스 클릭에서는 즉시 이동
        if (e.type === 'touchend' || e.type === 'touchstart') {
            return; // 터치 이벤트는 별도 핸들러에서 처리
        }

        e.preventDefault();
        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
        if (!this.ws || this.state.players.length < 2 || !myPlayer ||
            this.state.gameState.current_player !== myPlayer.color || this.state.gameEnded) {
            return;
        }

        const pos = this.getEventPosition(e);
        const x = pos.x;
        const y = pos.y;

        if (x >= 0 && x < 15 && y >= 0 && y < 15 && this.state.gameState.board[y][x] === 0) {
            // 서버에 이동 정보만 전송 (데스크톱은 즉시 이동)
            const message = {
                type: 'move',
                move: {x, y},
                session_id: this.sessionId
            };
            this.ws.send(JSON.stringify(message));
        }
    }

    // WebSocket 메시지 처리
    handleWebSocketMessage(event) {
        const serverData = JSON.parse(event.data);

        // 서버의 snake_case 데이터를 그대로 사용 (필요시 개별 변환)
        const data = serverData;

        // 채팅 메시지 처리 (원본 서버 데이터 사용)
        if (typeof handleChatWebSocketMessage === 'function') {
            handleChatWebSocketMessage(serverData);
        }

        switch (data.type) {
            case 'room_update':
                this.handleRoomUpdate(data);
                break;
            case 'reconnect_success':
                this.handleReconnectSuccess(data);
                break;
            case 'player_disconnected':
                this.showToast('플레이어 연결 끊김', `${this.escapeHtml(data.nickname)}님의 연결이 끊어졌습니다.`, 'warning', 5000);
                break;
            case 'player_reconnected':
                this.showToast('플레이어 재연결', `${this.escapeHtml(data.nickname)}님이 다시 연결되었습니다.`, 'success', 3000);
                break;
            case 'game_update':
                this.handleGameUpdate(data);
                break;
            case 'game_end':
                this.handleGameEnd(data);
                break;
            case 'restart_request':
                this.handleRestartRequest(data);
                break;
            case 'restart_accepted':
                this.handleRestartAccepted(data);
                break;
            case 'restart_rejected':
                this.handleRestartRejected();
                break;
            case 'undo_request':
                this.handleUndoRequest(data);
                break;
            case 'undo_accepted':
                this.handleUndoAccepted(data);
                break;
            case 'undo_rejected':
                this.handleUndoRejected();
                break;
            case 'error':
                this.handleError(data);
                break;
        }
    }

    handleRoomUpdate(data) {
        this.state.players = data.room.players;

        // 게임 상태 업데이트
        if (data.room.game_state) {
            this.state.gameState = data.room.game_state;
        }

        // myPlayerNumber 설정 (항상 확인)
        if (this.state.myPlayerNumber === null || this.state.myPlayerNumber === undefined) {
            const currentNickname = this.state.myNickname || document.getElementById('nicknameInput')?.value?.trim();
            if (currentNickname) {
                const myPlayer = this.state.players.find(p => p.nickname === currentNickname);
                if (myPlayer) {
                    this.state.myPlayerNumber = myPlayer.player_number;
                    this.saveGameSession({
                        nickname: currentNickname,
                        sessionId: this.sessionId,
                        player_number: this.state.myPlayerNumber,
                        color: myPlayer.color,
                        joinedAt: Date.now()
                    });
                }
            }
        }

        this.updateUI();

        if (this.state.players.length === 1) {
            this.showToast('입장 완료', '상대방을 기다리고 있습니다...', 'info', 5000);
            this.showGameArea();
            this.drawBoard();
        } else if (this.state.players.length === 2) {
            this.showGameArea();
            this.state.gameStarted = true;
            this.state.gameStats.startTime = Date.now();
            this.showToast('게임 시작', '모든 플레이어가 참여했습니다. 게임을 시작합니다!', 'success');
            this.drawBoard();

            // myPlayerNumber 설정 후 현재 턴 표시
            setTimeout(() => {
                this.showTurnIndicator();
            }, 100);
        }
    }

    handleReconnectSuccess(data) {
        if (data.room && data.room.game_state) {
            this.state.gameState = data.room.game_state;
        }
        if (data.room && data.room.players) {
            this.state.players = data.room.players;
            // 재연결 시 플레이어가 2명이면 게임이 시작된 상태
            if (this.state.players.length === 2) {
                this.state.gameStarted = true;
            }
        }
        if (data.player) {
            this.state.myPlayerNumber = data.player.player_number;
        }
        if (data.room && data.room.gameEnded !== undefined) {
            this.state.gameEnded = data.room.gameEnded;
        }
        if (data.room && data.room.winner) {
            this.state.winnerNumber = data.room.winner;
        }

        // 채팅 히스토리 복원
        if (data.room && data.room.chatHistory && typeof displayChatMessage === 'function') {
            data.room.chatHistory.forEach(msg => {
                displayChatMessage(msg.nickname, msg.message, msg.timestamp, msg.player_number);
            });
        }

        // 무브 히스토리 복원
        if (data.moveHistory) {
            this.state.moveHistory = data.moveHistory;
            // 마지막 수 복원
            if (data.moveHistory.length > 0) {
                const lastMoveEntry = data.moveHistory[data.moveHistory.length - 1];
                this.state.lastMove = lastMoveEntry.move;
            }
        }

        // 총 수 횟수 계산
        this.recalculateMoveCount();

        this.showGameArea();
        this.drawBoard();
        this.updateUI();
        this.updateUndoButton();

        // 재접속 시에도 현재 턴 표시 (게임이 진행 중일 때만)
        if (!this.state.gameEnded && this.state.players.length === 2) {
            // UI 업데이트가 완료된 후 턴 표시
            setTimeout(() => {
                this.showTurnIndicator();
            }, 100);
        }

        this.showToast('재연결 성공', '게임 상태가 복원되었습니다.', 'success');
    }

    handleGameUpdate(data) {
        const previousPlayer = this.state.gameState.current_player;
        this.state.gameState = data.game_state;

        if (data.lastMove) {
            this.state.lastMove = data.lastMove;

            // moveHistory에 새로운 수 추가
            const newMoveEntry = {
                move: data.lastMove,
                player: previousPlayer // 이전 플레이어가 방금 둔 수
            };
            this.state.moveHistory.push(newMoveEntry);

            this.recalculateMoveCount();
        }
        this.drawBoard();
        this.updateUI();
        this.updateUndoButton();

        // 턴이 바뀌었을 때 UI 업데이트 및 턴 표시
        if (previousPlayer !== this.state.gameState.current_player) {
            // UI 업데이트가 완료된 후 턴 표시
            setTimeout(() => {
                this.showTurnIndicator();
            }, 50);
        }
    }

    handleGameEnd(data) {
        this.state.gameEnded = true;
        this.state.gameState = data.game_state;
        if (data.lastMove) {
            this.state.lastMove = data.lastMove;
        }
        if (data.winningLine) {
            this.state.winningLine = data.winningLine;
        }

        this.recalculateMoveCount();

        this.state.winnerNumber = data.winner;
        const isMyWin = data.winner === this.state.myPlayerNumber;
        if (isMyWin) {
            this.createConfetti();
        }

        this.startWinAnimation();
        setTimeout(() => this.showWinModal(data.winner, isMyWin), 1500);
    }

    handleError(data) {
        console.error('서버 오류:', data.message);

        // 오류 타입별 처리
        switch(data.error_type) {
            case 'validation':
                showGlobalToast('입력 오류', data.message, 'warning', 4000);
                break;
            case 'server':
                showGlobalToast('서버 오류', data.message, 'error', 5000);
                break;
            case 'game':
                showGlobalToast('게임 오류', data.message, 'warning', 3000);

                // 잘못된 수에 대한 시각적 피드백
                const isInvalidMove = data.message.includes('올바르지 않은') ||
                                     data.message.includes('이미 놓인') ||
                                     data.message.includes('차례가 아닙니다') ||
                                     data.message.includes('유효하지 않은');

                if (isInvalidMove) {
                    this.showInvalidMoveAnimation();
                }
                break;
            default:
                showGlobalToast('오류', data.message, 'error', 4000);
        }

        // 심각한 오류의 경우 추가 처리
        const isCriticalError = data.message.includes('세션') ||
                               data.message.includes('플레이어 정보') ||
                               data.message.includes('연결');

        if (isCriticalError && data.error_type === 'server') {
            this.showModal('심각한 오류', data.message, [
                { text: '메인으로', class: 'primary', onclick: () => {
                    this.hideModal();
                    window.location.href = '/';
                }}
            ]);
        }
    }

    // 총 수 횟수 재계산
    recalculateMoveCount() {
        this.state.gameStats.moves = 0;
        for (let y = 0; y < 15; y++) {
            for (let x = 0; x < 15; x++) {
                if (this.state.gameState.board[y][x] !== 0) {
                    this.state.gameStats.moves++;
                }
            }
        }
    }

    // UI 업데이트
    updateUI() {
        // 플레이어 목록 업데이트
        const playerList = document.getElementById('playerList');
        if (playerList) {
            playerList.innerHTML = this.state.players.map(p => {
                const isCurrentPlayer = p.color === this.state.gameState.current_player;
                const isMe = p.player_number === this.state.myPlayerNumber;
                let itemClass = 'player-item';
                if (isCurrentPlayer) itemClass += ' active';
                if (isMe && isCurrentPlayer) itemClass += ' my-turn';

                return `
                    <div class="${itemClass}">
                        <div class="player-name">${this.escapeHtml(p.nickname)}${isMe ? ' (나)' : ''}</div>
                        <div class="player-stone">
                            <span class="stone-indicator ${p.color === 1 ? 'black' : 'white'}"></span>
                            ${p.color === 1 ? '흑돌' : '백돌'}
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 현재 턴 표시
        const currentTurn = document.getElementById('currentTurn');
        if (currentTurn) {
            // 플레이어가 2명이고 게임이 진행 중일 때만 표시
            if (this.state.players.length === 2 && !this.state.gameEnded) {
                const currentPlayer = this.state.players.find(p => p.color === this.state.gameState.current_player);
                if (currentPlayer) {
                    const isMyTurn = currentPlayer.player_number === this.state.myPlayerNumber;
                    currentTurn.innerHTML = `
                        <div class="player-item ${isMyTurn ? 'my-turn' : 'active'}">
                            <div class="player-name">${this.escapeHtml(currentPlayer.nickname)}${isMyTurn ? ' (나)' : ''}</div>
                            <div class="player-stone">
                                <span class="stone-indicator ${currentPlayer.color === 1 ? 'black' : 'white'}"></span>
                                ${currentPlayer.color === 1 ? '흑돌' : '백돌'}
                            </div>
                        </div>
                    `;
                } else {
                    currentTurn.textContent = '-';
                }
            } else {
                currentTurn.textContent = '-';
            }
        }

        // 게임 정보 업데이트
        const moveCountEl = document.getElementById('moveCount');
        if (moveCountEl) {
            moveCountEl.textContent = this.state.gameStats.moves;
        }

        const gameTimeEl = document.getElementById('gameTime');
        if (gameTimeEl && this.state.gameStats.startTime) {
            const elapsed = Math.floor((Date.now() - this.state.gameStats.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            gameTimeEl.textContent = `${minutes}:${seconds}`;
        }

        // 사용자 경험 개선 기능들 호출
        this.updateGameButtons();
    }

    // 게임 영역 표시
    showGameArea() {
        const nicknameForm = document.getElementById('nicknameForm');
        const existingGameForm = document.getElementById('existingGameForm');
        const gameArea = document.getElementById('gameArea');

        if (nicknameForm) nicknameForm.style.display = 'none';
        if (existingGameForm) existingGameForm.style.display = 'none';
        if (gameArea) gameArea.style.display = 'block';
    }

    // 모달 시스템
    showModal(title, body, buttons = []) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = body;

        const footer = document.getElementById('modalFooter');
        footer.innerHTML = '';

        buttons.forEach(button => {
            const btn = document.createElement('button');
            btn.className = `modal-button ${button.class || 'secondary'}`;
            btn.textContent = button.text;
            btn.onclick = button.onclick;
            footer.appendChild(btn);
        });

        document.getElementById('modalOverlay').classList.add('show');
    }

    hideModal() {
        document.getElementById('modalOverlay').classList.remove('show');
    }

    showWinModal(winner, isMyWin) {
        const modal = document.getElementById('modal');
        modal.className = 'modal win-modal';

        const icon = isMyWin ? '🎉' : '😔';
        const iconClass = isMyWin ? 'victory' : 'defeat';
        const messageClass = isMyWin ? 'victory' : 'defeat';
        const message = isMyWin ? '승리!' : '패배';
        const submessage = isMyWin ? '축하합니다!' : '다음에 더 잘해보세요!';

        const body = `
            <div class="win-icon ${iconClass}">${icon}</div>
            <div class="win-message ${messageClass}">${message}</div>
            <div class="win-submessage">${submessage}</div>
        `;

        this.showModal('게임 종료', body, [
            {
                text: '확인',
                class: 'primary',
                onclick: () => {
                    this.hideModal();
                    modal.className = 'modal';
                }
            }
        ]);
    }

    // 토스트 알림 시스템 (전역 함수 사용)
    showToast(title, message, type = 'info', duration = 3000) {
        if (typeof showGlobalToast === 'function') {
            showGlobalToast(title, message, type, duration);
        }
    }

    // 색종이 효과 (전역 함수 사용)
    createConfetti() {
        if (typeof createConfetti === 'function') {
            window.createConfetti();
        }
    }

    // 승리 애니메이션
    startWinAnimation() {
        let animationFrame = 0;
        const animate = () => {
            this.drawBoard();
            animationFrame++;
            if (animationFrame < 100) {
                requestAnimationFrame(animate);
            }
        };
        animate();
    }

    // 게임 타이머
    startGameTimer() {
        if (this.gameTimer) clearInterval(this.gameTimer);
        this.gameTimer = setInterval(() => {
            if (this.state.gameStats.startTime && !this.state.gameEnded) {
                this.updateUI();
            }
        }, 1000);
    }

    // 모바일 레이아웃 조정
    adjustMobileLayout() {
        const gameLayout = document.getElementById('gameLayout');
        const isMobile = window.innerWidth <= 768;

        if (!this.canvas) return;

        // 모바일 감지 시 body에 클래스 추가
        if (isMobile) {
            document.body.classList.add('mobile-mode');
            gameLayout.style.flexDirection = 'column';
            gameLayout.style.gap = '10px';

            // Canvas 크기 최적화
            const maxSize = Math.min(window.innerWidth - 40, window.innerHeight * 0.4, 320);
            this.canvas.style.width = maxSize + 'px';
            this.canvas.style.height = maxSize + 'px';
            this.canvas.width = maxSize;
            this.canvas.height = maxSize;

            this.canvas.style.transform = '';
            this.canvas.style.transformOrigin = '';

            // 게임 정보 패널 접기 기능 추가 (채팅 패널 포함)
            this.setupCollapsiblePanels();

            this.drawBoard();

            // 모바일 튜토리얼 확인 및 표시
            this.checkAndShowMobileTutorial();
        } else {
            document.body.classList.remove('mobile-mode');
            gameLayout.style.flexDirection = 'row';
            gameLayout.style.gap = '20px';

            this.canvas.style.width = '450px';
            this.canvas.style.height = '450px';
            this.canvas.width = 450;
            this.canvas.height = 450;
            this.canvas.style.transform = '';
            this.canvas.style.transformOrigin = '';

            // PC에서도 채팅 패널 접기 기능 적용
            this.setupCollapsiblePanels();

            this.drawBoard();
        }
    }

    // 게임 정보 패널 접기 기능 설정
    setupCollapsiblePanels() {
        const panels = document.querySelectorAll('.game-info-panel');
        panels.forEach(panel => {
            // 이미 이벤트가 등록되어 있는지 확인
            if (!panel.dataset.collapsible) {
                panel.dataset.collapsible = 'true';

                // 헤더만 클릭 가능하도록 설정 (채팅 패널 포함)
                const header = panel.querySelector('h4');
                if (header) {
                    header.style.cursor = 'pointer';
                    header.style.position = 'relative';
                    panel.style.position = 'relative';

                    header.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log(`패널 헤더 클릭됨: ${header.textContent}`); // 디버깅용
                        panel.classList.toggle('collapsed');
                    });

                    // 채팅 패널인 경우 입력창과 버튼 클릭 시 이벤트 전파 방지
                    if (panel.classList.contains('chat-panel')) {
                        const chatInput = panel.querySelector('#chatInput');
                        const chatButton = panel.querySelector('#chatSendButton');

                        if (chatInput) {
                            chatInput.addEventListener('click', (e) => {
                                e.stopPropagation();
                            });
                        }

                        if (chatButton) {
                            chatButton.addEventListener('click', (e) => {
                                e.stopPropagation();
                            });
                        }
                    }
                }
            }
        });
    }


    // 게임 참여
    joinGame() {
        const nickname = document.getElementById('nicknameInput').value.trim();
        if (!nickname) {
            this.showModal('알림', '닉네임을 입력해주세요.', [
                { text: '확인', class: 'primary', onclick: () => this.hideModal() }
            ]);
            return;
        }

        this.state.myNickname = nickname;
        this.connectWebSocket();

        const waitForConnection = () => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                if (typeof setupChatConnection === 'function') {
                    setupChatConnection(this.ws, nickname);
                }
                const message = {
                    type: 'join',
                    nickname: nickname,
                    session_id: this.sessionId
                };
                this.ws.send(JSON.stringify(message));

                this.saveGameSession({
                    nickname: nickname,
                    sessionId: this.sessionId,
                    joinedAt: Date.now()
                });
            } else {
                setTimeout(waitForConnection, 100);
            }
        };

        waitForConnection();
    }

    // 무르기 버튼 업데이트
    updateUndoButton() {
        const undoButton = document.getElementById('undoButton');
        if (undoButton) {
            const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
            // 무르기는 자신의 턴과 상대방 턴 모두에서 가능
            // 케이스 1: 자신의 턴에 상대방 마지막 수 무르기 요청
            // 케이스 2: 상대방 턴에 자신의 마지막 수 무르기 요청
            const canUndo = this.ws && !this.state.gameEnded && !this.state.waitingForUndo &&
                           this.state.gameStats.moves > 0 && myPlayer;
            undoButton.disabled = !canUndo;
            undoButton.style.opacity = canUndo ? '1' : '0.5';
        }
    }

    // 게임 버튼들 상태 업데이트
    updateGameButtons() {
        this.updateUndoButton();
        this.updateRestartButton();
        this.updateGameActionButtons();
    }

    // 재시작 버튼 업데이트
    updateRestartButton() {
        const restartButton = document.getElementById('restartButton');
        if (restartButton) {
            // 게임이 시작되었거나 끝났을 때 다시하기 가능 (대기 중이 아닌 경우)
            const canRestart = this.ws && (this.state.gameStarted || this.state.gameEnded) && !this.state.waitingForRestart;
            restartButton.disabled = !canRestart;
            restartButton.style.opacity = canRestart ? '1' : '0.5';

            if (this.state.waitingForRestart) {
                restartButton.textContent = '재시작 대기중...';
            } else {
                restartButton.textContent = '다시하기';
            }
        }
    }

    // 게임 액션 버튼들 업데이트
    updateGameActionButtons() {
        const buttons = ['joinButton', 'continueButton', 'newGameButton'];
        const gameArea = document.getElementById('gameArea');
        const joinArea = document.getElementById('joinArea');

        buttons.forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.style.opacity = button.disabled ? '0.5' : '1';
            }
        });

        // 게임 영역 표시/숨김
        if (gameArea && joinArea) {
            const shouldShowGame = this.state.players.length > 0 && this.state.myPlayerNumber;
            gameArea.style.display = shouldShowGame ? 'block' : 'none';
            joinArea.style.display = shouldShowGame ? 'none' : 'block';
        }
    }

    // 잘못된 수에 대한 시각적 피드백 (보드 흔들림 효과)
    showInvalidMoveAnimation() {
        if (!this.canvas) return;

        const originalTransform = this.canvas.style.transform;
        this.canvas.style.transition = 'transform 0.1s ease-in-out';

        // 흔들림 애니메이션
        const shakeIntensity = 5;
        const shakeDuration = 300;
        const shakeCount = 6;
        const shakeInterval = shakeDuration / shakeCount;

        let shakeStep = 0;
        const shakeAnimation = () => {
            if (shakeStep >= shakeCount) {
                this.canvas.style.transform = originalTransform;
                this.canvas.style.transition = '';
                return;
            }

            const offset = shakeStep % 2 === 0 ? shakeIntensity : -shakeIntensity;
            this.canvas.style.transform = `${originalTransform} translateX(${offset}px)`;
            shakeStep++;

            setTimeout(shakeAnimation, shakeInterval);
        };

        shakeAnimation();

        // 붉은 테두리 효과
        const originalBorder = this.canvas.style.border;
        this.canvas.style.border = '3px solid #ff4444';
        this.canvas.style.boxShadow = '0 0 10px rgba(255, 68, 68, 0.5)';

        setTimeout(() => {
            this.canvas.style.border = originalBorder;
            this.canvas.style.boxShadow = '';
        }, shakeDuration);
    }


    // 턴 표시 강화
    showTurnIndicator() {
        // 플레이어 수와 게임 상태 확인
        if (this.state.players.length !== 2 || this.state.gameEnded) return;

        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
        if (!myPlayer || this.state.myPlayerNumber === null || this.state.myPlayerNumber === undefined) return;

        const currentPlayer = this.state.players.find(p => p.color === this.state.gameState.current_player);
        if (!currentPlayer) return;

        const isMyTurn = this.state.gameState.current_player === myPlayer.color;

        if (isMyTurn) {
            this.showToast('당신의 차례', '돌을 놓을 위치를 선택하세요', 'info', 3000);

            // 보드에 미묘한 하이라이트 효과
            if (this.canvas) {
                this.canvas.style.boxShadow = '0 0 15px rgba(0, 150, 255, 0.3)';
                setTimeout(() => {
                    this.canvas.style.boxShadow = '';
                }, 3000);
            }
        } else {
            // 상대방 턴일 때도 알림 표시
            const currentPlayerName = currentPlayer.nickname;
            const stoneColor = this.state.gameState.current_player === 1 ? '흑돌' : '백돌';
            this.showToast('상대방 차례', `${currentPlayerName}님(${stoneColor})의 차례입니다`, 'info', 3000);
        }
    }

    // 게임 재시작 요청
    requestRestart() {
        if (!this.ws || this.state.waitingForRestart) {
            return;
        }

        // 게임이 시작되지 않았다면 재시작 불가
        if (!this.state.gameStarted) {
            this.showModal('알림', '게임이 시작되지 않았습니다.', [
                { text: '확인', class: 'primary', onclick: () => this.hideModal() }
            ]);
            return;
        }

        this.state.waitingForRestart = true;
        const message = {
            type: 'restart_request',
            from: this.state.myPlayerNumber,
            session_id: this.sessionId
        };
        this.ws.send(JSON.stringify(message));
    }

    // 무르기 요청
    requestUndo() {
        if (!this.ws || this.state.waitingForUndo || this.state.gameEnded || this.state.gameStats.moves === 0) {
            return;
        }

        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);

        // 무르기 가능한 상황인지 확인 (자신/상대방 수 모두 무르기 가능)
        // 케이스 1: 자신의 턴에 상대방 마지막 수 무르기 요청
        // 케이스 2: 상대방 턴에 자신의 마지막 수 무르기 요청

        this.state.waitingForUndo = true;
        const message = {
            type: 'undo_request',
            from: this.state.myPlayerNumber,
            session_id: this.sessionId
        };
        this.ws.send(JSON.stringify(message));
    }

    // 로컬 스토리지 관리
    saveGameSession(sessionData) {
        try {
            localStorage.setItem('omokGameSession', JSON.stringify({
                ...sessionData,
                timestamp: Date.now(),
                roomId: this.roomId
            }));
        } catch (error) {
            // 세션 저장 실패 시 무시
        }
    }

    loadGameSession() {
        try {
            const data = localStorage.getItem('omokGameSession');
            if (!data) return null;

            const session = JSON.parse(data);

            if (Date.now() - session.timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem('omokGameSession');
                return null;
            }

            if (session.roomId !== this.roomId) {
                return null;
            }

            return session;
        } catch (error) {
            // 세션 로드 실패 시 null 반환
            return null;
        }
    }

    clearGameSession() {
        try {
            localStorage.removeItem('omokGameSession');
        } catch (error) {
            // 세션 정리 실패 시 무시
        }
    }

    // 기존 세션 확인
    checkExistingSession() {
        const hostNickname = sessionStorage.getItem('hostNickname');
        const localSession = this.loadGameSession();

        if (localSession && localSession.nickname && localSession.sessionId) {
            this.showExistingGamePrompt(localSession);
            return;
        }

        if (hostNickname) {
            const nicknameInput = document.getElementById('nicknameInput');
            if (nicknameInput) {
                nicknameInput.value = hostNickname;
                setTimeout(() => {
                    this.showToast('자동 입장', '방 생성자로 게임에 입장합니다...', 'info', 2000);
                    setTimeout(() => this.joinGame(), 1000);
                }, 500);
            }
            sessionStorage.removeItem('hostNickname');
        }
    }

    showExistingGamePrompt(sessionData) {
        document.getElementById('nicknameForm').style.display = 'none';
        document.getElementById('existingGameForm').style.display = 'block';

        const existingGameForm = document.getElementById('existingGameForm');
        existingGameForm.querySelector('p').innerHTML =
            `진행 중인 게임이 있습니다. (${this.escapeHtml(sessionData.nickname)})<br>어떻게 하시겠습니까?`;

        this.pendingSessionData = sessionData;
    }

    // 기존 게임 이어하기
    continueExistingGame() {
        if (this.pendingSessionData) {
            this.state.myNickname = this.pendingSessionData.nickname;
            this.state.myPlayerNumber = this.pendingSessionData.player_number;

            this.connectWebSocket();

            const waitForConnection = () => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    const message = {
                        type: 'reconnect',
                        session_id: this.pendingSessionData.sessionId
                    };
                    this.ws.send(JSON.stringify(message));
                } else {
                    setTimeout(waitForConnection, 100);
                }
            };

            waitForConnection();
        }
    }

    // 새 게임 시작
    startNewGame() {
        this.clearGameSession();
        document.getElementById('existingGameForm').style.display = 'none';
        document.getElementById('nicknameForm').style.display = 'block';
        this.pendingSessionData = null;
    }

    // 방 나가기
    confirmLeaveRoom() {
        this.showModal(
            '방 나가기',
            '정말로 게임에서 나가시겠습니까?<br>진행 중인 게임이 종료됩니다.',
            [
                {
                    text: '취소',
                    class: 'secondary',
                    onclick: () => this.hideModal()
                },
                {
                    text: '확인',
                    class: 'primary',
                    onclick: () => {
                        this.clearGameSession();
                        if (this.ws) {
                            this.ws.close();
                        }
                        window.location.href = '/';
                    }
                }
            ]
        );
    }

    // 나머지 핸들러들 (간소화된 버전)
    handleRestartRequest(data) {
        const requesterName = this.state.players.find(p => p.player_number === data.from)?.nickname || '상대방';

        if (data.isRequester) {
            // 요청자에게는 모달 대신 토스트로 알림
            this.showToast('재시작 요청', '상대방에게 재시작 요청을 보냈습니다.', 'info', 3000);
            this.updateUI(); // 버튼 상태 업데이트
        } else {
            this.showModal('게임 재시작 요청',
                `${requesterName}님이 게임 재시작을 요청했습니다.<br>재시작하시겠습니까?`, [
                {
                    text: '거부',
                    class: 'secondary',
                    onclick: () => {
                        this.hideModal();
                        const message = {
                            type: 'restart_response',
                            accepted: false,
                            session_id: this.sessionId
                        };
                        this.ws.send(JSON.stringify(message));
                    }
                },
                {
                    text: '동의',
                    class: 'success',
                    onclick: () => {
                        this.hideModal();
                        const message = {
                            type: 'restart_response',
                            accepted: true,
                            session_id: this.sessionId
                        };
                        this.ws.send(JSON.stringify(message));
                    }
                }
            ]);
        }
    }

    handleRestartAccepted(data) {
        this.state.gameEnded = false;
        this.state.gameStarted = true;
        this.state.waitingForRestart = false;
        this.state.lastMove = null;
        this.state.winningLine = null;
        this.state.winnerNumber = null;
        this.state.gameStats = { moves: 0, startTime: Date.now() };
        this.state.gameState = data.game_state;
        this.state.moveHistory = []; // 게임 재시작 시 히스토리 초기화

        if (data.players) {
            this.state.players = data.players;
        }

        this.hideModal();
        this.drawBoard();
        this.updateUI();

        // 재시작 후 턴 표시
        setTimeout(() => {
            this.showTurnIndicator();
        }, 100);

        const gameNum = data.games_played || 1;
        this.showToast('게임 재시작', `${gameNum}번째 게임이 시작되었습니다!`, 'success');
    }

    handleRestartRejected() {
        this.state.waitingForRestart = false;
        this.showModal('알림', '상대방이 재시작을 거부했습니다.', [
            { text: '확인', class: 'primary', onclick: () => this.hideModal() }
        ]);
    }

    handleUndoRequest(data) {
        const requesterName = this.state.players.find(p => p.player_number === data.from)?.nickname || '상대방';

        if (data.isRequester) {
            // 요청자에게는 토스트 메시지로만 알림 (팝업 없음)
            this.showToast('무르기 요청', '상대방에게 무르기 요청을 보냈습니다. 응답을 기다리는 중...', 'info');
        } else {
            // 무르기 대상 수 확인 (마지막 수가 누구 것인지)
            const lastMove = this.state.moveHistory?.[this.state.moveHistory.length - 1];
            const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
            let message;

            if (lastMove && myPlayer && lastMove.player === myPlayer.color) {
                // 내 수를 무르기 요청받음 (상대방이 내 수를 무르자고 요청)
                message = `${requesterName}님이 무르기를 요청했습니다.<br>내가 둔 마지막 수를 취소하시겠습니까?`;
            } else {
                // 상대방 수를 무르기 요청받음 (상대방이 자신의 수를 무르자고 요청)
                message = `${requesterName}님이 무르기를 요청했습니다.<br>${requesterName}님이 둔 마지막 수를 취소하시겠습니까?`;
            }

            this.showModal('무르기 요청', message, [
                {
                    text: '거부',
                    class: 'secondary',
                    onclick: () => {
                        this.hideModal();
                        const message = {
                            type: 'undo_response',
                            accepted: false,
                            session_id: this.sessionId
                        };
                        this.ws.send(JSON.stringify(message));
                    }
                },
                {
                    text: '동의',
                    class: 'success',
                    onclick: () => {
                        this.hideModal();
                        const message = {
                            type: 'undo_response',
                            accepted: true,
                            session_id: this.sessionId
                        };
                        this.ws.send(JSON.stringify(message));
                    }
                }
            ]);
        }
    }

    handleUndoAccepted(data) {
        this.state.gameState = data.game_state;
        this.recalculateMoveCount();
        this.state.waitingForUndo = false;
        this.state.lastMove = null;

        // moveHistory에서 마지막 수 제거
        if (this.state.moveHistory.length > 0) {
            this.state.moveHistory.pop();
        }

        this.hideModal();
        this.drawBoard();
        this.updateUI();
        this.updateUndoButton();
        this.showToast('무르기 성공', '마지막 수가 취소되었습니다.', 'success');
    }

    handleUndoRejected() {
        this.state.waitingForUndo = false;
        this.showModal('알림', '상대방이 무르기를 거부했습니다.', [
            { text: '확인', class: 'primary', onclick: () => this.hideModal() }
        ]);
    }

    // 모바일 터치 미리보기 시스템
    showPreviewStone(x, y) {
        const myPlayer = this.state.players.find(p => p.player_number === this.state.myPlayerNumber);
        if (!myPlayer || this.state.gameState.current_player !== myPlayer.color ||
            this.state.gameEnded || this.state.gameState.board[y][x] !== 0) {
            return false;
        }

        this.state.previewStone = {
            x: x,
            y: y,
            color: myPlayer.color
        };

        this.showConfirmButtons();
        this.drawBoard();
        return true;
    }

    updatePreviewStone(x, y) {
        if (!this.state.previewStone) return false;

        if (x >= 0 && x < 15 && y >= 0 && y < 15 && this.state.gameState.board[y][x] === 0) {
            this.state.previewStone.x = x;
            this.state.previewStone.y = y;
            this.drawBoard();
            return true;
        }
        return false;
    }

    showConfirmButtons() {
        const buttonsElement = document.getElementById('mobileConfirmButtons');
        if (buttonsElement) {
            buttonsElement.style.display = 'flex';
            this.state.showingConfirmButtons = true;
        }
    }

    hideConfirmButtons() {
        const buttonsElement = document.getElementById('mobileConfirmButtons');
        if (buttonsElement) {
            buttonsElement.style.display = 'none';
            this.state.showingConfirmButtons = false;
        }
    }

    confirmMove() {
        if (!this.state.previewStone || !this.ws) return;

        const { x, y } = this.state.previewStone;

        // 서버에 이동 정보만 전송 (서버가 모든 로직 처리)
        const message = {
            type: 'move',
            move: {x, y},
            session_id: this.sessionId
        };
        this.ws.send(JSON.stringify(message));

        // 미리보기 정리
        this.cancelMove();
    }

    cancelMove() {
        this.state.previewStone = null;
        this.state.isDragging = false;
        this.hideConfirmButtons();
        this.drawBoard();
    }

    // 모바일 튜토리얼 관련 메서드들
    checkAndShowMobileTutorial() {
        const TUTORIAL_STORAGE_KEY = 'omokMobileTutorialShown';
        const isMobile = window.innerWidth <= 768;
        const tutorialShown = localStorage.getItem(TUTORIAL_STORAGE_KEY);

        if (isMobile && !tutorialShown) {
            // 게임 영역이 완전히 로드된 후 약간의 지연을 두고 표시
            setTimeout(() => {
                this.showMobileTutorial();
            }, 800);
        }
    }

    showMobileTutorial() {
        const tutorialContent = `
            <div style="text-align: center; line-height: 1.6; padding: 10px;">
                <div style="font-size: 18px; margin-bottom: 15px;">📱 모바일 오목 사용법</div>

                <div style="text-align: left; margin-bottom: 15px;">
                    <div style="margin-bottom: 12px;">
                        <strong>🎯 돌 놓기</strong><br>
                        <span style="color: #666; font-size: 14px;">• 터치 → 미리보기 표시<br>
                        • 확정/취소 버튼으로 결정</span>
                    </div>

                    <div style="margin-bottom: 12px;">
                        <strong>🎯 위치 조정</strong><br>
                        <span style="color: #666; font-size: 14px;">• 미리보기 상태에서 드래그<br>
                        • 원하는 위치로 이동</span>
                    </div>

                    <div style="margin-bottom: 12px;">
                        <strong>🎯 미리보기 해제</strong><br>
                        <span style="color: #666; font-size: 14px;">• 미리보기 상태에서 다시 터치</span>
                    </div>
                </div>

                <div style="color: #3b82f6; font-weight: 600;">시작할 준비가 되셨나요?</div>
            </div>
        `;

        showModal('모바일 사용법 안내', tutorialContent, [
            {
                text: '다시 보지 않기',
                class: 'secondary',
                onclick: () => {
                    this.markTutorialAsShown();
                    hideModal();
                }
            },
            {
                text: '시작하기',
                class: 'primary',
                onclick: () => {
                    this.markTutorialAsShown();
                    hideModal();
                }
            }
        ]);
    }

    markTutorialAsShown() {
        const TUTORIAL_STORAGE_KEY = 'omokMobileTutorialShown';
        localStorage.setItem(TUTORIAL_STORAGE_KEY, 'true');
    }
}

// HTML에서 호출되는 전역 함수들
function joinGame() {
    if (window.omokClient) {
        window.omokClient.joinGame();
    }
}

function continueExistingGame() {
    if (window.omokClient) {
        window.omokClient.continueExistingGame();
    }
}

function startNewGame() {
    if (window.omokClient) {
        window.omokClient.startNewGame();
    }
}

function requestRestart() {
    if (window.omokClient) {
        window.omokClient.requestRestart();
    }
}

function requestUndo() {
    if (window.omokClient) {
        window.omokClient.requestUndo();
    }
}

function confirmLeaveRoom() {
    if (window.omokClient) {
        window.omokClient.confirmLeaveRoom();
    }
}
