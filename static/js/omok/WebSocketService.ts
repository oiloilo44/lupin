/**
 * WebSocket 서비스 - 통신 로직 전담
 * 기존 WebSocket 로직을 단순 래핑 (절대 변경 없음)
 */

import type { GameState, WebSocketMessage } from '../../types/game';

interface ConnectionState {
    status: 'connected' | 'connecting' | 'disconnected' | 'reconnecting';
    reconnectAttempts: number;
    maxReconnectAttempts: number;
    reconnectTimeout: number | null;
}

// WebSocket 이벤트 콜백 타입 정의
interface WebSocketCallbacks {
    onConnectionStatusUpdate: (status: ConnectionState['status'], text?: string) => void;
    onMessage: (event: MessageEvent) => void;
    onReconnectionFailed: () => void;
    setupChatConnection: (ws: WebSocket, nickname: string) => void;
}

export class WebSocketService {
    private ws: WebSocket | null = null;
    private roomId: string;
    private sessionId: string;
    private connection: ConnectionState;
    private callbacks: WebSocketCallbacks;

    constructor(roomId: string, sessionId: string, callbacks: WebSocketCallbacks) {
        this.roomId = roomId;
        this.sessionId = sessionId;
        this.callbacks = callbacks;

        // 연결 상태 초기화 (기존과 동일)
        this.connection = {
            status: 'disconnected',
            reconnectAttempts: 0,
            maxReconnectAttempts: 5,
            reconnectTimeout: null
        };
    }

    // WebSocket 연결 (기존 connectWebSocket 로직 래핑)
    connect(isReconnect: boolean = false): void {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${this.roomId}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.callbacks.onConnectionStatusUpdate('connected');
                this.connection.reconnectAttempts = 0;

                // 채팅 연결 설정 (기존 로직 그대로)
                if (this.ws && typeof this.callbacks.setupChatConnection === 'function') {
                    const nickname = (window as any).currentNickname; // 임시로 글로벌에서 가져옴
                    if (nickname) {
                        this.callbacks.setupChatConnection(this.ws, nickname);
                    }
                }

                if (isReconnect && this.ws) {
                    const message = {
                        type: 'reconnect',
                        session_id: this.sessionId
                    };
                    if (this.ws) {
                        this.ws.send(JSON.stringify(message));
                    }
                }
            };

            this.ws.onmessage = (event) => this.callbacks.onMessage(event);
            this.ws.onclose = (event) => this.handleClose(event);
            this.ws.onerror = (error) => this.handleError(error);

        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.handleConnectionFailure();
        }
    }

    // WebSocket 종료 처리 (기존 handleWebSocketClose 로직)
    private handleClose(event: CloseEvent): void {
        if (event.code === 1000) {
            this.callbacks.onConnectionStatusUpdate('disconnected', '연결 종료');
            return;
        }

        this.callbacks.onConnectionStatusUpdate('disconnected', '연결 끊김');

        if (this.connection.reconnectTimeout) {
            clearTimeout(this.connection.reconnectTimeout);
        }

        setTimeout(() => this.attemptReconnect(), 1000);
    }

    // WebSocket 에러 처리 (기존 handleWebSocketError 로직)
    private handleError(error: Event): void {
        console.error('WebSocket error:', error);
    }

    // 연결 실패 처리 (기존 handleConnectionFailure 로직)
    private handleConnectionFailure(): void {
        this.callbacks.onConnectionStatusUpdate('disconnected', '연결 실패');
        setTimeout(() => this.attemptReconnect(), 2000);
    }

    // 재연결 시도 (기존 attemptReconnect 로직)
    private attemptReconnect(): void {
        if (this.connection.reconnectAttempts >= this.connection.maxReconnectAttempts) {
            this.callbacks.onConnectionStatusUpdate('disconnected', '재연결 실패');
            this.callbacks.onReconnectionFailed();
            return;
        }

        this.connection.reconnectAttempts++;
        // 개선된 지수 백오프: 1s, 2s, 4s, 8s, 15s, 30s (기존 로직 그대로)
        const baseDelay = 1000;
        const exponentialDelay = baseDelay * Math.pow(2, this.connection.reconnectAttempts - 1);
        const jitterDelay = exponentialDelay + Math.random() * 1000; // 지터 추가
        const finalDelay = Math.min(jitterDelay, 30000); // 최대 30초

        this.callbacks.onConnectionStatusUpdate('reconnecting',
            `재연결 시도 중... (${this.connection.reconnectAttempts}/${this.connection.maxReconnectAttempts})`
        );

        // 재연결 진행 상황을 토스트로 표시 (기존 로직 그대로)
        const delaySeconds = Math.ceil(finalDelay / 1000);
        if (typeof (window as any).showGlobalToast === 'function') {
            (window as any).showGlobalToast(
                '재연결 시도',
                `${delaySeconds}초 후 다시 연결을 시도합니다`,
                'info',
                Math.min(finalDelay - 500, 4000)
            );
        }

        this.connection.reconnectTimeout = setTimeout(() => {
            this.connect(true);
        }, finalDelay);
    }

    // 수동 재연결 (기존 manualReconnect 로직)
    manualReconnect(): void {
        // 재연결 상태 초기화
        this.connection.reconnectAttempts = 0;
        if (this.connection.reconnectTimeout) {
            clearTimeout(this.connection.reconnectTimeout);
            this.connection.reconnectTimeout = null;
        }

        if (typeof (window as any).showGlobalToast === 'function') {
            (window as any).showGlobalToast('재연결 시도', '수동으로 재연결을 시도합니다', 'info');
        }
        this.connect(true);
    }

    // 메시지 전송
    sendMessage(message: any): boolean {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            return true;
        }
        return false;
    }

    // WebSocket 정리 (기존 cleanupWebSocket 로직)
    cleanup(): void {
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

    // WebSocket 상태 확인
    isConnected(): boolean {
        return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
    }

    getConnectionStatus(): ConnectionState['status'] {
        return this.connection.status;
    }

    getReconnectAttempts(): number {
        return this.connection.reconnectAttempts;
    }

    getMaxReconnectAttempts(): number {
        return this.connection.maxReconnectAttempts;
    }
}
