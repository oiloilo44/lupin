"""게임 레지스트리 - 게임 메타데이터 관리"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models import GameType


@dataclass
class GameInfo:
    """게임 정보 메타데이터"""
    
    game_type: GameType
    display_name: str
    description: str
    max_players: int
    min_players: int
    estimated_duration: str  # 예상 게임 시간
    difficulty: str  # 난이도
    is_active: bool = True  # 게임 활성화 상태


class GameRegistry:
    """게임 레지스트리 클래스
    
    게임들의 메타데이터를 중앙에서 관리
    게임 목록, 게임 정보 조회 등의 기능 제공
    """
    
    _games: Dict[GameType, GameInfo] = {}
    
    @classmethod
    def register_game(cls, game_info: GameInfo) -> None:
        """게임 정보 등록
        
        Args:
            game_info: 등록할 게임 정보
        """
        cls._games[game_info.game_type] = game_info
    
    @classmethod
    def get_game_info(cls, game_type: GameType) -> Optional[GameInfo]:
        """게임 정보 조회
        
        Args:
            game_type: 조회할 게임 타입
            
        Returns:
            게임 정보 또는 None
        """
        return cls._games.get(game_type)
    
    @classmethod
    def get_all_games(cls, active_only: bool = True) -> List[GameInfo]:
        """모든 게임 정보 목록 반환
        
        Args:
            active_only: 활성화된 게임만 반환할지 여부
            
        Returns:
            게임 정보 리스트
        """
        games = list(cls._games.values())
        
        if active_only:
            games = [game for game in games if game.is_active]
        
        return games
    
    @classmethod
    def get_active_games(cls) -> List[GameType]:
        """활성화된 게임 타입 목록 반환
        
        Returns:
            활성화된 게임 타입들의 리스트
        """
        return [
            game.game_type 
            for game in cls._games.values() 
            if game.is_active
        ]
    
    @classmethod
    def is_game_active(cls, game_type: GameType) -> bool:
        """게임이 활성화되어 있는지 확인
        
        Args:
            game_type: 확인할 게임 타입
            
        Returns:
            활성화 여부
        """
        game_info = cls._games.get(game_type)
        return game_info is not None and game_info.is_active
    
    @classmethod
    def set_game_status(cls, game_type: GameType, is_active: bool) -> bool:
        """게임 활성화 상태 변경
        
        Args:
            game_type: 대상 게임 타입
            is_active: 새로운 활성화 상태
            
        Returns:
            성공 여부
        """
        if game_type not in cls._games:
            return False
        
        cls._games[game_type].is_active = is_active
        return True


def register_default_games() -> None:
    """기본 게임들을 레지스트리에 등록"""
    
    # 오목 게임 등록
    omok_info = GameInfo(
        game_type=GameType.OMOK,
        display_name="오목",
        description="15x15 보드에서 5개의 돌을 연속으로 놓아 승리하는 게임",
        max_players=2,
        min_players=2,
        estimated_duration="10-30분",
        difficulty="중급",
        is_active=True
    )
    GameRegistry.register_game(omok_info)


# 모듈 로드 시 기본 게임들 등록
register_default_games()