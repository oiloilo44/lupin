"""게임 매니저 팩토리 패턴 구현"""

from typing import Dict, Type

from ..models import GameType
from .base import BaseGameManager
from .omok_manager import OmokManager


class GameManagerFactory:
    """게임 매니저 팩토리 클래스

    게임 타입에 따라 적절한 게임 매니저를 생성하고 반환
    새로운 게임 추가 시 등록만 하면 됨
    """

    _managers: Dict[GameType, Type[BaseGameManager]] = {}

    @classmethod
    def register_manager(
        cls, game_type: GameType, manager_class: Type[BaseGameManager]
    ) -> None:
        """게임 매니저 등록

        Args:
            game_type: 게임 타입
            manager_class: 게임 매니저 클래스
        """
        cls._managers[game_type] = manager_class

    @classmethod
    def get_manager(cls, game_type: GameType) -> BaseGameManager:
        """게임 타입에 따른 매니저 인스턴스 반환

        Args:
            game_type: 게임 타입

        Returns:
            게임 매니저 인스턴스

        Raises:
            KeyError: 등록되지 않은 게임 타입인 경우
        """
        if game_type not in cls._managers:
            raise KeyError(f"No manager registered for game type: {game_type}")

        manager_class = cls._managers[game_type]
        return manager_class()

    @classmethod
    def get_supported_games(cls) -> list[GameType]:
        """지원되는 게임 타입 목록 반환

        Returns:
            지원되는 게임 타입들의 리스트
        """
        return list(cls._managers.keys())

    @classmethod
    def is_game_supported(cls, game_type: GameType) -> bool:
        """게임 타입이 지원되는지 확인

        Args:
            game_type: 확인할 게임 타입

        Returns:
            지원 여부
        """
        return game_type in cls._managers


# 기본 게임 매니저들 등록
def register_default_managers() -> None:
    """기본 게임 매니저들을 팩토리에 등록"""
    GameManagerFactory.register_manager(GameType.OMOK, OmokManager)


# 모듈 로드 시 자동으로 기본 매니저들 등록
register_default_managers()
