"""Pydantic 기반 설정 스키마 정의"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class OmokConfig(BaseModel):
    """오목 게임 설정"""

    board_size: int = Field(default=15, gt=0, le=19, description="오목판 크기")
    win_condition: int = Field(
        default=5, ge=3, le=7, description="승리 조건 (연속된 돌의 수)"
    )
    allow_undo: bool = Field(default=True, description="무르기 허용 여부")
    turn_timeout: int = Field(default=30, gt=0, description="턴 타임아웃 (초)")


class JanggiConfig(BaseModel):
    """장기 게임 설정"""

    board_width: int = Field(default=9, gt=0, description="장기판 가로 크기")
    board_height: int = Field(default=10, gt=0, description="장기판 세로 크기")
    turn_timeout: int = Field(default=60, gt=0, description="턴 타임아웃 (초)")


class WormGameConfig(BaseModel):
    """지렁이 게임 설정"""

    grid_size: int = Field(default=20, gt=0, description="게임 그리드 크기")
    initial_length: int = Field(default=3, gt=0, description="초기 지렁이 길이")
    speed: float = Field(default=1.0, gt=0, description="게임 속도")


class GameConfig(BaseModel):
    """게임 관련 설정"""

    omok: OmokConfig = Field(default_factory=OmokConfig)
    janggi: JanggiConfig = Field(default_factory=JanggiConfig)
    worm: WormGameConfig = Field(default_factory=WormGameConfig)
    max_players: int = Field(default=2, ge=2, description="최대 플레이어 수")
    room_cleanup_delay: int = Field(
        default=300, gt=0, description="빈 방 정리 지연 시간 (초)"
    )
    max_chat_history: int = Field(default=50, gt=0, description="최대 채팅 기록 수")


class ServerConfig(BaseModel):
    """서버 설정"""

    host: str = Field(default="0.0.0.0", description="서버 호스트")
    port: int = Field(default=8002, gt=0, le=65535, description="서버 포트")
    debug: bool = Field(default=False, description="디버그 모드")
    cors_origins: list[str] = Field(default=["*"], description="CORS 허용 오리진")
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="로그 레벨",
    )


class SecurityConfig(BaseModel):
    """보안 설정"""

    max_nickname_length: int = Field(default=20, gt=0, description="최대 닉네임 길이")
    max_message_length: int = Field(default=500, gt=0, description="최대 메시지 길이")
    rate_limit_per_minute: int = Field(default=60, gt=0, description="분당 요청 제한")
    session_timeout: int = Field(default=3600, gt=0, description="세션 타임아웃 (초)")


class AppConfig(BaseModel):
    """애플리케이션 전체 설정"""

    server: ServerConfig = Field(default_factory=ServerConfig)
    games: GameConfig = Field(default_factory=GameConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    version: str = Field(default="1.0.0", description="애플리케이션 버전")
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
        description="실행 환경",
    )

    class Config:
        """Pydantic 모델 설정"""

        validate_assignment = True
        use_enum_values = True
        json_encoders: Dict[type, type] = {
            # 필요한 경우 커스텀 인코더 추가
        }

    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """딕셔너리에서 설정 생성"""
        return cls(**data)
