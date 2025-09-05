// 전역 타입 정의
declare global {
  interface Window {
    omokClient?: any; // WebSocket 클라이언트
    setupChatConnection?: (ws: WebSocket, nickname: string) => void;
    handleChatWebSocketMessage?: (data: any) => void;
    createConfetti?: () => void;
  }
}

// 브라우저용 타이머 타입
declare type TimerId = number;

// 전역 함수 선언
declare function setupChatConnection(roomId: string): void;
declare function showGlobalToast(title: string, message: string, type?: string): void;
declare function showModal(title: string, content: string, buttons?: any[]): void;
declare function saveGameSession(sessionId: string, roomId: string, nickname: string): void;
declare function loadGameSession(): { sessionId: string; roomId: string; nickname: string } | null;
declare function handleChatWebSocketMessage(msg: any): void;

export {};
