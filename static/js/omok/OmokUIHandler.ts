/**
 * 오목 게임 UI 핸들러 - DOM 조작 전담
 * 모달, 토스트, UI 업데이트 등 DOM 관련 작업만 처리
 */

import type { PlayerInfo } from '../../types/game';

// OmokGameState interface는 omok.ts에서 정의되므로 여기서 재정의
interface OmokGameState {
    gameState: { current_player: number; board: number[][]; game_status: string };
    myPlayerNumber: number | null;
    players: PlayerInfo[];
    gameEnded: boolean;
    gameStarted: boolean;
    waitingForRestart: boolean;
    gameStats: { moves: number; startTime: number | null };
    waitingForUndo: boolean;
}

// Global functions declared elsewhere
declare function showGlobalToast(title: string, message: string, type: string, duration?: number): void;
declare function hideModal(): void;
declare function createConfetti(): void;

export class OmokUIHandler {

    constructor() {}

    // HTML 이스케이프 함수 (XSS 방지)
    escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 연결 상태 업데이트 UI
    updateConnectionStatus(status: 'connected' | 'connecting' | 'disconnected' | 'reconnecting', text?: string, reconnectAttempts: number = 0, maxReconnectAttempts: number = 5): void {
        const statusElement = document.getElementById('connectionStatus');
        const iconElement = document.getElementById('connectionIcon');
        const textElement = document.getElementById('connectionText');

        if (!statusElement || !iconElement || !textElement) return;

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
                if (reconnectAttempts >= 3) {
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
                if (reconnectAttempts > 0) {
                    const progress = Math.round((reconnectAttempts / maxReconnectAttempts) * 100);
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

    // UI 업데이트 - 플레이어 목록, 턴 표시, 게임 정보
    updateGameUI(state: OmokGameState): void {
        this.updatePlayerList(state.players, state.gameState.current_player, state.myPlayerNumber);
        this.updateCurrentTurn(state.players, state.gameState.current_player, state.myPlayerNumber, state.gameEnded);
        this.updateGameInfo(state.gameStats);
    }

    // 플레이어 목록 업데이트
    private updatePlayerList(players: PlayerInfo[], currentPlayer: number, myPlayerNumber: number | null): void {
        const playerList = document.getElementById('playerList');
        if (playerList) {
            playerList.innerHTML = players.map(p => {
                const isCurrentPlayer = p.color === currentPlayer;
                const isMe = p.player_number === myPlayerNumber;
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
    }

    // 현재 턴 표시 업데이트
    private updateCurrentTurn(players: PlayerInfo[], currentPlayer: number, myPlayerNumber: number | null, gameEnded: boolean): void {
        const currentTurn = document.getElementById('currentTurn');
        if (currentTurn) {
            // 플레이어가 2명이고 게임이 진행 중일 때만 표시
            if (players.length === 2 && !gameEnded) {
                const currentPlayerInfo = players.find((p: PlayerInfo) => p.color === currentPlayer);
                if (currentPlayerInfo) {
                    const isMyTurn = currentPlayerInfo.player_number === myPlayerNumber;
                    currentTurn.innerHTML = `
                        <div class="player-item ${isMyTurn ? 'my-turn' : 'active'}">
                            <div class="player-name">${this.escapeHtml(currentPlayerInfo.nickname)}${isMyTurn ? ' (나)' : ''}</div>
                            <div class="player-stone">
                                <span class="stone-indicator ${currentPlayerInfo.color === 1 ? 'black' : 'white'}"></span>
                                ${currentPlayerInfo.color === 1 ? '흑돌' : '백돌'}
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
    }

    // 게임 정보 업데이트
    private updateGameInfo(gameStats: { moves: number; startTime: number | null }): void {
        const moveCountEl = document.getElementById('moveCount');
        if (moveCountEl) {
            moveCountEl.textContent = gameStats.moves.toString();
        }

        const gameTimeEl = document.getElementById('gameTime');
        if (gameTimeEl && gameStats.startTime) {
            const elapsed = Math.floor((Date.now() - gameStats.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const seconds = (elapsed % 60).toString().padStart(2, '0');
            gameTimeEl.textContent = `${minutes}:${seconds}`;
        }
    }

    // 게임 영역 표시
    showGameArea(): void {
        const nicknameForm = document.getElementById('nicknameForm');
        const existingGameForm = document.getElementById('existingGameForm');
        const gameArea = document.getElementById('gameArea');

        if (nicknameForm) nicknameForm.style.display = 'none';
        if (existingGameForm) existingGameForm.style.display = 'none';
        if (gameArea) gameArea.style.display = 'block';
    }

    // 모달 시스템
    showModal(title: string, body: string, buttons: Array<{ text: string; class?: string; onclick: () => void }> = []): void {
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        const footer = document.getElementById('modalFooter');

        if (!modalTitle || !modalBody || !footer) return;

        modalTitle.textContent = title;
        modalBody.innerHTML = body;
        footer.innerHTML = '';

        buttons.forEach(button => {
            const btn = document.createElement('button');
            btn.className = `modal-button ${button.class || 'secondary'}`;
            btn.textContent = button.text;
            btn.onclick = button.onclick;
            footer.appendChild(btn);
        });

        const modalOverlay = document.getElementById('modalOverlay');
        if (modalOverlay) modalOverlay.classList.add('show');
    }

    hideModal(): void {
        const modalOverlay = document.getElementById('modalOverlay');
        if (modalOverlay) modalOverlay.classList.remove('show');
    }

    // 승리 모달
    showWinModal(winner: number, isMyWin: boolean): void {
        const modal = document.getElementById('modal');
        if (!modal) return;
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
    showToast(title: string, message: string, type: string = 'info', duration: number = 3000): void {
        if (typeof showGlobalToast === 'function') {
            showGlobalToast(title, message, type, duration);
        }
    }

    // 색종이 효과 (전역 함수 사용)
    createConfetti(): void {
        if (typeof createConfetti === 'function') {
            (window as any).createConfetti();
        }
    }

    // 기존 게임 프롬프트
    showExistingGamePrompt(sessionData: any): void {
        const nicknameForm = document.getElementById('nicknameForm');
        const existingGameForm = document.getElementById('existingGameForm');

        if (nicknameForm) nicknameForm.style.display = 'none';
        if (existingGameForm) existingGameForm.style.display = 'block';

        const paragraph = existingGameForm?.querySelector('p');
        if (paragraph) {
            paragraph.innerHTML = `진행 중인 게임이 있습니다. (${this.escapeHtml(sessionData.nickname)})<br>어떻게 하시겠습니까?`;
        }
    }

    // 새 게임 UI
    showNewGameForm(): void {
        const existingGameForm = document.getElementById('existingGameForm');
        const nicknameForm = document.getElementById('nicknameForm');
        if (existingGameForm) existingGameForm.style.display = 'none';
        if (nicknameForm) nicknameForm.style.display = 'block';
    }

    // 게임 버튼들 상태 업데이트
    updateGameButtons(state: OmokGameState, hasWebSocket: boolean): void {
        this.updateUndoButton(state, hasWebSocket);
        this.updateRestartButton(state, hasWebSocket);
        this.updateGameActionButtons(state);
    }

    // 무르기 버튼 업데이트
    private updateUndoButton(state: OmokGameState, hasWebSocket: boolean): void {
        const undoButton = document.getElementById('undoButton') as HTMLButtonElement;
        if (undoButton) {
            const myPlayer = state.players.find((p: PlayerInfo) => p.player_number === state.myPlayerNumber);
            const canUndo = hasWebSocket && !state.gameEnded && !state.waitingForUndo &&
                           state.gameStats.moves > 0 && myPlayer;
            undoButton.disabled = !canUndo;
            undoButton.style.opacity = canUndo ? '1' : '0.5';
        }
    }

    // 재시작 버튼 업데이트
    private updateRestartButton(state: OmokGameState, hasWebSocket: boolean): void {
        const restartButton = document.getElementById('restartButton') as HTMLButtonElement;
        if (restartButton) {
            const canRestart = hasWebSocket && (state.gameStarted || state.gameEnded) && !state.waitingForRestart;
            restartButton.disabled = !canRestart;
            restartButton.style.opacity = canRestart ? '1' : '0.5';

            if (state.waitingForRestart) {
                restartButton.textContent = '재시작 대기중...';
            } else {
                restartButton.textContent = '다시하기';
            }
        }
    }

    // 게임 액션 버튼들 업데이트
    private updateGameActionButtons(state: OmokGameState): void {
        const buttons = ['joinButton', 'continueButton', 'newGameButton'];
        const gameArea = document.getElementById('gameArea');
        const joinArea = document.getElementById('joinArea');

        buttons.forEach(buttonId => {
            const button = document.getElementById(buttonId) as HTMLButtonElement;
            if (button) {
                button.style.opacity = button.disabled ? '0.5' : '1';
            }
        });

        // 게임 영역 표시/숨김
        if (gameArea && joinArea) {
            const shouldShowGame = state.players.length > 0 && state.myPlayerNumber;
            gameArea.style.display = shouldShowGame ? 'block' : 'none';
            joinArea.style.display = shouldShowGame ? 'none' : 'block';
        }
    }

    // 모바일 확정 버튼 표시/숨김
    showConfirmButtons(): void {
        const buttonsElement = document.getElementById('mobileConfirmButtons');
        if (buttonsElement) {
            buttonsElement.style.display = 'flex';
        }
    }

    hideConfirmButtons(): void {
        const buttonsElement = document.getElementById('mobileConfirmButtons');
        if (buttonsElement) {
            buttonsElement.style.display = 'none';
        }
    }

    // 모바일 레이아웃 조정 (DOM 조작 부분만)
    adjustMobileLayoutDOM(): void {
        const gameLayout = document.getElementById('gameLayout');
        const isMobile = window.innerWidth <= 768;

        if (!gameLayout) return;

        // 모바일 감지 시 body에 클래스 추가
        if (isMobile) {
            document.body.classList.add('mobile-mode');
            gameLayout.style.flexDirection = 'column';
            gameLayout.style.gap = '10px';
        } else {
            document.body.classList.remove('mobile-mode');
            gameLayout.style.flexDirection = 'row';
            gameLayout.style.gap = '20px';
        }
    }

    // 게임 정보 패널 접기 기능 설정
    setupCollapsiblePanels(): void {
        const panels = document.querySelectorAll('.game-info-panel');
        panels.forEach(panel => {
            // 이미 이벤트가 등록되어 있는지 확인
            const htmlPanel = panel as HTMLElement;
            if (!htmlPanel.dataset.collapsible) {
                htmlPanel.dataset.collapsible = 'true';

                // 헤더만 클릭 가능하도록 설정 (채팅 패널 포함)
                const header = panel.querySelector('h4');
                if (header) {
                    (header as HTMLElement).style.cursor = 'pointer';
                    (header as HTMLElement).style.position = 'relative';
                    (panel as HTMLElement).style.position = 'relative';

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

    // 모바일 튜토리얼
    showMobileTutorial(): void {
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

        this.showModal('모바일 사용법 안내', tutorialContent, [
            {
                text: '다시 보지 않기',
                class: 'secondary',
                onclick: () => {
                    this.markTutorialAsShown();
                    this.hideModal();
                }
            },
            {
                text: '시작하기',
                class: 'primary',
                onclick: () => {
                    this.markTutorialAsShown();
                    this.hideModal();
                }
            }
        ]);
    }

    private markTutorialAsShown(): void {
        const TUTORIAL_STORAGE_KEY = 'omokMobileTutorialShown';
        localStorage.setItem(TUTORIAL_STORAGE_KEY, 'true');
    }

    // 모바일 튜토리얼 확인
    checkAndShowMobileTutorial(): void {
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
}
