/**
 * OmokRenderer - 오목 게임 렌더링 전담 클래스
 * 캔버스 렌더링, 좌표 변환, 시각적 효과 처리
 */

import type { GameState, PlayerInfo } from '../../types/game';

interface OmokGameState {
    gameState: GameState;
    myPlayerNumber: number | null;
    players: PlayerInfo[];
    gameEnded: boolean;
    gameStarted: boolean;
    lastMove: { x: number; y: number } | null;
    hoverPosition: [number, number] | null;
    winningLine: Array<{ x: number; y: number }> | null;
    previewStone: { x: number; y: number; color: number } | null;
    isDragging: boolean;
}

export class OmokRenderer {
    private canvas: HTMLCanvasElement;
    private ctx: CanvasRenderingContext2D;

    constructor(canvas: HTMLCanvasElement) {
        this.canvas = canvas;
        const context = canvas.getContext('2d');
        if (!context) {
            throw new Error('Failed to get canvas 2d context');
        }
        this.ctx = context;
    }

    /**
     * 오목판 그리기 - 메인 렌더링 메서드
     */
    drawBoard(state: OmokGameState): void {
        if (!this.ctx || !this.canvas) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        const boardSize = Math.min(this.canvas.width, this.canvas.height);
        const margin = boardSize * 0.05;
        const cellSize = (boardSize - 2 * margin) / 14;

        // 배경 그리기
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // 격자 그리기
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = Math.max(1, cellSize / 30);

        // 세로선 그리기
        for (let i = 0; i < 15; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(margin + i * cellSize, margin);
            this.ctx.lineTo(margin + i * cellSize, boardSize - margin);
            this.ctx.stroke();
        }
        // 가로선 그리기
        for (let i = 0; i < 15; i++) {
            this.ctx.beginPath();
            this.ctx.moveTo(margin, margin + i * cellSize);
            this.ctx.lineTo(boardSize - margin, margin + i * cellSize);
            this.ctx.stroke();
        }

        // 화점 그리기 (5개 지점)
        const starPoints = [[3, 3], [3, 11], [11, 3], [11, 11], [7, 7]];
        this.ctx.fillStyle = '#000';
        for (const [x, y] of starPoints) {
            if (state.gameState.board[y][x] === 0) {
                this.ctx.beginPath();
                this.ctx.arc(margin + x * cellSize, margin + y * cellSize, Math.max(2, cellSize / 10), 0, 2 * Math.PI);
                this.ctx.fill();
            }
        }

        const stoneRadius = cellSize * 0.4;

        // 미리보기 돌 그리기 (모바일 터치용)
        if (state.previewStone) {
            const { x: px, y: py } = state.previewStone;
            if (px >= 0 && px < 15 && py >= 0 && py < 15 && state.gameState.board[py][px] === 0) {
                this.ctx.beginPath();
                this.ctx.arc(margin + px * cellSize, margin + py * cellSize, stoneRadius, 0, 2 * Math.PI);
                this.ctx.fillStyle = state.previewStone.color === 1 ? 'rgba(0, 0, 0, 0.5)' : 'rgba(255, 255, 255, 0.7)';
                this.ctx.fill();
                this.ctx.strokeStyle = state.previewStone.color === 1 ? 'rgba(0, 0, 0, 0.7)' : 'rgba(51, 51, 51, 0.7)';
                this.ctx.lineWidth = Math.max(2, cellSize / 20);
                this.ctx.stroke();
            }
        }

        // 호버 효과 그리기 (데스크톱용)
        if (state.hoverPosition && !state.previewStone) {
            const [hx, hy] = state.hoverPosition;
            if (hx >= 0 && hx < 15 && hy >= 0 && hy < 15 && state.gameState.board[hy][hx] === 0) {
                this.ctx.beginPath();
                this.ctx.arc(margin + hx * cellSize, margin + hy * cellSize, stoneRadius, 0, 2 * Math.PI);
                this.ctx.fillStyle = state.gameState.current_player === 1 ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.5)';
                this.ctx.fill();
                this.ctx.strokeStyle = state.gameState.current_player === 1 ? 'rgba(0, 0, 0, 0.5)' : 'rgba(51, 51, 51, 0.5)';
                this.ctx.lineWidth = Math.max(1, cellSize / 30);
                this.ctx.stroke();
            }
        }

        // 바둑돌 그리기
        for (let y = 0; y < 15; y++) {
            for (let x = 0; x < 15; x++) {
                if (state.gameState.board[y][x] !== 0) {
                    const centerX = margin + x * cellSize;
                    const centerY = margin + y * cellSize;

                    this.ctx.save();

                    // 승리 라인 강조 및 애니메이션
                    const isWinningStone = state.winningLine?.some(pos => pos.x === x && pos.y === y);

                    // 기본 바둑돌 그리기
                    this.ctx.beginPath();
                    this.ctx.arc(centerX, centerY, stoneRadius, 0, 2 * Math.PI);
                    this.ctx.fillStyle = state.gameState.board[y][x] === 1 ? '#000' : '#fff';
                    this.ctx.fill();
                    this.ctx.strokeStyle = '#333';
                    this.ctx.lineWidth = Math.max(1, cellSize / 30);
                    this.ctx.stroke();

                    // 마지막 수 표시
                    if (state.lastMove && state.lastMove.x === x && state.lastMove.y === y) {
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * 1.25, 0, 2 * Math.PI);
                        this.ctx.strokeStyle = '#ff4444';
                        this.ctx.lineWidth = Math.max(2, cellSize / 15);
                        this.ctx.stroke();
                    }

                    // 승리 라인 강조
                    if (isWinningStone) {
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * 1.5, 0, 2 * Math.PI);
                        this.ctx.strokeStyle = '#ffd700';
                        this.ctx.lineWidth = Math.max(3, cellSize / 10);
                        this.ctx.stroke();

                        // 승리 애니메이션 (펄스 효과)
                        const time = Date.now() * 0.005;
                        const pulse = 1.2 + 0.3 * Math.sin(time);
                        this.ctx.beginPath();
                        this.ctx.arc(centerX, centerY, stoneRadius * pulse, 0, 2 * Math.PI);
                        this.ctx.fillStyle = state.gameState.board[y][x] === 1 ?
                            'rgba(255, 215, 0, 0.3)' : 'rgba(255, 215, 0, 0.5)';
                        this.ctx.fill();
                    }

                    this.ctx.restore();
                }
            }
        }
    }

    /**
     * 이벤트 위치를 보드 좌표로 변환
     */
    getEventPosition(e: MouseEvent | Touch): { x: number; y: number } {
        if (!this.canvas) throw new Error('Canvas not initialized');

        const rect = this.canvas.getBoundingClientRect();
        const clientX = 'clientX' in e ? e.clientX : 0;
        const clientY = 'clientY' in e ? e.clientY : 0;

        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        const canvasX = (clientX - rect.left) * scaleX;
        const canvasY = (clientY - rect.top) * scaleY;

        const boardSize = Math.min(this.canvas.width, this.canvas.height);
        const margin = boardSize * 0.05;
        const cellSize = (boardSize - 2 * margin) / 14;

        return {
            x: Math.round((canvasX - margin) / cellSize),
            y: Math.round((canvasY - margin) / cellSize)
        };
    }

    /**
     * 터치 피드백 애니메이션 표시
     */
    showTouchFeedback(x: number, y: number): void {
        if (!this.canvas || !this.ctx) return;

        if (x >= 0 && x < 15 && y >= 0 && y < 15) {
            const boardSize = Math.min(this.canvas.width, this.canvas.height);
            const margin = boardSize * 0.05;
            const cellSize = (boardSize - 2 * margin) / 14;
            const pixelX = margin + x * cellSize;
            const pixelY = margin + y * cellSize;

            // 터치 위치에 파란색 원 표시
            this.ctx.save();
            this.ctx.strokeStyle = '#3b82f6';
            this.ctx.lineWidth = 3;
            this.ctx.globalAlpha = 0.5;
            this.ctx.beginPath();
            this.ctx.arc(pixelX, pixelY, cellSize / 3, 0, Math.PI * 2);
            this.ctx.stroke();
            this.ctx.restore();
        }
    }

    /**
     * Canvas 크기 조정
     */
    adjustCanvasSize(width: number, height: number): void {
        this.canvas.style.width = width + 'px';
        this.canvas.style.height = height + 'px';
        this.canvas.width = width;
        this.canvas.height = height;
        this.canvas.style.transform = '';
        this.canvas.style.transformOrigin = '';
    }

    /**
     * Canvas 하이라이트 효과 (연결 성공시)
     */
    highlightCanvas(success: boolean = true): void {
        if (!this.canvas) return;

        if (success) {
            this.canvas.style.boxShadow = '0 0 15px rgba(0, 150, 255, 0.3)';
            setTimeout(() => {
                if (this.canvas) {
                    this.canvas.style.boxShadow = '';
                }
            }, 1000);
        } else {
            const originalBorder = this.canvas.style.border;
            this.canvas.style.border = '3px solid #ff4444';
            this.canvas.style.boxShadow = '0 0 10px rgba(255, 68, 68, 0.5)';

            setTimeout(() => {
                if (this.canvas) {
                    this.canvas.style.border = originalBorder;
                    this.canvas.style.boxShadow = '';
                }
            }, 2000);
        }
    }

    /**
     * Canvas 흔들림 애니메이션 (잘못된 이동시)
     */
    shakeCanvas(): void {
        if (!this.canvas) return;

        const originalTransform = this.canvas.style.transform;
        this.canvas.style.transition = 'transform 0.1s ease-in-out';

        let shakeCount = 0;
        const maxShakes = 4;
        const shakeIntensity = 5;

        const shake = () => {
            shakeCount++;
            const offset = shakeCount % 2 === 0 ? -shakeIntensity : shakeIntensity;

            setTimeout(() => {
                if (this.canvas) {
                    this.canvas.style.transform = originalTransform;
                    this.canvas.style.transition = '';
                }
            }, 50);

            if (this.canvas && shakeCount <= maxShakes) {
                this.canvas.style.transform = `${originalTransform} translateX(${offset}px)`;
            }

            if (shakeCount < maxShakes) {
                setTimeout(shake, 100);
            }
        };

        shake();
    }
}
