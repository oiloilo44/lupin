/**
 * 게임용 채팅 모듈
 * 모든 게임에서 재사용 가능한 채팅 시스템
 */

class GameChat {
    constructor(options = {}) {
        this.chatMessagesId = options.chatMessagesId || 'chatMessages';
        this.chatInputId = options.chatInputId || 'chatInput';
        this.chatSendButtonId = options.chatSendButtonId || 'chatSendButton';
        this.myNickname = null;
        this.websocket = null;
        
        this.init();
    }
    
    init() {
        // Enter 키로 채팅 전송 설정
        const chatInput = document.getElementById(this.chatInputId);
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }
        
        // 전송 버튼 클릭 이벤트
        const sendButton = document.getElementById(this.chatSendButtonId);
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this.sendMessage();
            });
        }
    }
    
    /**
     * WebSocket과 닉네임 설정
     */
    setConnection(websocket, nickname) {
        this.websocket = websocket;
        this.myNickname = nickname;
    }
    
    /**
     * 채팅 메시지 전송
     */
    sendMessage() {
        const chatInput = document.getElementById(this.chatInputId);
        const message = chatInput?.value.trim();
        
        if (!message || !this.websocket || !this.myNickname) {
            return;
        }
        
        this.websocket.send(JSON.stringify({
            type: 'chat_message',
            nickname: this.myNickname,
            message: message
        }));
        
        chatInput.value = '';
    }
    
    /**
     * 채팅 메시지 표시
     */
    displayMessage(nickname, message, timestamp, playerNumber) {
        const chatMessages = document.getElementById(this.chatMessagesId);
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message';
        
        if (nickname === this.myNickname) {
            messageDiv.classList.add('my-message');
        }
        
        messageDiv.innerHTML = `
            <div class="timestamp">${timestamp}</div>
            <span class="nickname">${nickname}:</span>
            <div class="message">${this.escapeHtml(message)}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // 메시지가 너무 많으면 오래된 것 제거 (클라이언트 측에서도 최적화)
        if (chatMessages.children.length > 100) {
            chatMessages.removeChild(chatMessages.firstChild);
        }
    }
    
    /**
     * 채팅 히스토리 로드
     */
    loadHistory(chatHistory) {
        const chatMessages = document.getElementById(this.chatMessagesId);
        if (!chatMessages) return;
        
        chatMessages.innerHTML = '';
        
        chatHistory.forEach(msg => {
            this.displayMessage(msg.nickname, msg.message, msg.timestamp, msg.player_number);
        });
    }
    
    /**
     * 채팅창 초기화 (게임 재시작 시 등)
     */
    clear() {
        const chatMessages = document.getElementById(this.chatMessagesId);
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
    }
    
    /**
     * HTML 이스케이프 처리
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 채팅 입력 활성화/비활성화
     */
    setEnabled(enabled) {
        const chatInput = document.getElementById(this.chatInputId);
        const sendButton = document.getElementById(this.chatSendButtonId);
        
        if (chatInput) {
            chatInput.disabled = !enabled;
        }
        if (sendButton) {
            sendButton.disabled = !enabled;
        }
    }
    
    /**
     * WebSocket 메시지 처리 (게임에서 호출)
     */
    handleWebSocketMessage(data) {
        if (data.type === 'chat_broadcast') {
            this.displayMessage(data.nickname, data.message, data.timestamp, data.player_number);
        } else if (data.type === 'room_update' && data.room.chat_history) {
            this.loadHistory(data.room.chat_history);
        }
    }
}

// 전역 함수로도 제공 (기존 코드와의 호환성)
let gameChat = null;

function initGameChat(options = {}) {
    gameChat = new GameChat(options);
    return gameChat;
}

function sendChatMessage() {
    if (gameChat) {
        gameChat.sendMessage();
    }
}

function displayChatMessage(nickname, message, timestamp, playerNumber) {
    if (gameChat) {
        gameChat.displayMessage(nickname, message, timestamp, playerNumber);
    }
}

function loadChatHistory(chatHistory) {
    if (gameChat) {
        gameChat.loadHistory(chatHistory);
    }
}