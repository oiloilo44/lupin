// 서버 응답 타입만 정의 (기존 로직 변경 없음)
export interface GameState {
  board: number[][];
  current_player: number;
  game_status: string;
  winner?: number;
  last_move?: { x: number; y: number };
  players?: PlayerInfo[];
}

export interface PlayerInfo {
  session_id: string;
  nickname: string;
  is_connected: boolean;
  player_number?: number;
  color: number;  // 1 for black, 2 for white - matches server logic
}

export interface RoomState {
  room_id: string;
  players: PlayerInfo[];
  game_state?: GameState;
  game_type?: string;
}

export interface WebSocketMessage {
  type: string;
  [key: string]: any;  // 유연성 유지
}

export interface JoinMessage extends WebSocketMessage {
  type: 'join';
  nickname: string;
}

export interface MoveMessage extends WebSocketMessage {
  type: 'move';
  move: { x: number; y: number };
}

export interface ChatMessage extends WebSocketMessage {
  type: 'chat';
  message: string;
  nickname?: string;
}

export interface GameUpdateMessage extends WebSocketMessage {
  type: 'game_update';
  game_state: GameState;
  room_state?: RoomState;
}
