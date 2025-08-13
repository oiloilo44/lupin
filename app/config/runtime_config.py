"""런타임 설정 변경 지원."""
import logging
from typing import Any, Dict, Optional

from .config_loader import get_config_loader
from .constants import OMOK_CONSTANTS, SERVER_CONSTANTS

logger = logging.getLogger(__name__)


class RuntimeConfigManager:
    """런타임 설정 변경을 관리하는 클래스."""

    def __init__(self) -> None:
        self._config_loader = get_config_loader()
        self._overrides: Dict[str, Dict[str, Any]] = {}
        # 설정 로더에 자신을 등록 (순환 import 방지)
        self._config_loader.set_runtime_manager(self)

    def set_game_config(self, game_name: str, config_path: str, value: Any) -> bool:
        """게임 설정 값을 런타임에 변경

        Args:
            game_name: 게임 이름 (예: "omok")
            config_path: 설정 경로 (예: "timeouts.move_timeout")
            value: 새로운 값

        Returns:
            성공 여부
        """
        try:
            # 오버라이드 저장
            if game_name not in self._overrides:
                self._overrides[game_name] = {}

            self._set_nested_value(self._overrides[game_name], config_path, value)

            # 설정 캐시 갱신
            self._config_loader.clear_cache()

            # 상수 객체들 갱신
            if game_name == "omok":
                self._refresh_omok_constants()

            logger.info(f"Runtime config updated: {game_name}.{config_path} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update runtime config: {e}")
            return False

    def set_server_config(self, config_path: str, value: Any) -> bool:
        """서버 설정 값을 런타임에 변경

        Args:
            config_path: 설정 경로 (예: "websocket.max_connections")
            value: 새로운 값

        Returns:
            성공 여부
        """
        try:
            # 오버라이드 저장
            if "server" not in self._overrides:
                self._overrides["server"] = {}

            self._set_nested_value(self._overrides["server"], config_path, value)

            # 설정 캐시 갱신
            self._config_loader.clear_cache()

            # 서버 상수 객체 갱신
            self._refresh_server_constants()

            logger.info(f"Runtime server config updated: {config_path} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update server config: {e}")
            return False

    def get_runtime_overrides(self) -> Dict[str, Dict[str, Any]]:
        """현재 런타임 오버라이드 설정 반환."""
        return self._overrides.copy()

    def clear_overrides(self, config_name: Optional[str] = None) -> None:
        """런타임 오버라이드 제거

        Args:
            config_name: 특정 설정만 제거. None이면 모든 오버라이드 제거
        """
        if config_name:
            if config_name in self._overrides:
                del self._overrides[config_name]
                logger.info(f"Cleared runtime overrides for {config_name}")
        else:
            self._overrides.clear()
            logger.info("Cleared all runtime overrides")

        # 설정 캐시 갱신
        self._config_loader.clear_cache()

        # 상수 객체들 갱신
        self._refresh_omok_constants()
        self._refresh_server_constants()

    def apply_overrides_to_config(
        self, config: Dict[str, Any], config_name: str
    ) -> Dict[str, Any]:
        """설정에 런타임 오버라이드 적용

        Args:
            config: 기본 설정
            config_name: 설정 이름

        Returns:
            오버라이드가 적용된 설정
        """
        if config_name not in self._overrides:
            return config

        result = config.copy()
        overrides = self._overrides[config_name]

        return self._deep_merge(result, overrides)

    def _set_nested_value(
        self, target_dict: Dict[str, Any], path: str, value: Any
    ) -> None:
        """중첩된 딕셔너리에 값 설정

        Args:
            target_dict: 대상 딕셔너리
            path: 점으로 구분된 경로 (예: "timeouts.move_timeout")
            value: 설정할 값
        """
        keys = path.split(".")
        current = target_dict

        # 마지막 키를 제외하고 경로 생성
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # 마지막 키에 값 설정
        current[keys[-1]] = value

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """두 딕셔너리를 깊이 병합."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _refresh_omok_constants(self) -> None:
        """OMOK_CONSTANTS 갱신."""
        try:
            # 현재 설정 다시 로드
            config = self._config_loader.get_game_config("omok")

            # 오버라이드 적용
            if "omok" in self._overrides:
                config = self._deep_merge(config, self._overrides["omok"])

            # 상수 객체의 설정 갱신
            OMOK_CONSTANTS._config = config

        except Exception as e:
            logger.error(f"Failed to refresh OMOK constants: {e}")

    def _refresh_server_constants(self) -> None:
        """SERVER_CONSTANTS 갱신."""
        try:
            # 현재 설정 다시 로드
            config = self._config_loader.get_server_config()

            # 오버라이드 적용
            if "server" in self._overrides:
                config = self._deep_merge(config, self._overrides["server"])

            # 상수 객체의 설정 갱신
            SERVER_CONSTANTS._config = config

        except Exception as e:
            logger.error(f"Failed to refresh SERVER constants: {e}")


# 전역 런타임 설정 매니저 인스턴스
_runtime_config_manager: Optional[RuntimeConfigManager] = None


def get_runtime_config_manager() -> RuntimeConfigManager:
    """전역 런타임 설정 매니저 인스턴스 반환."""
    global _runtime_config_manager
    if _runtime_config_manager is None:
        _runtime_config_manager = RuntimeConfigManager()
    return _runtime_config_manager


# 편의 함수들
def set_game_config(game_name: str, config_path: str, value: Any) -> bool:
    """게임 설정 값을 런타임에 변경."""
    return get_runtime_config_manager().set_game_config(game_name, config_path, value)


def set_server_config(config_path: str, value: Any) -> bool:
    """서버 설정 값을 런타임에 변경."""
    return get_runtime_config_manager().set_server_config(config_path, value)


def clear_runtime_overrides(config_name: Optional[str] = None) -> None:
    """런타임 오버라이드 제거."""
    get_runtime_config_manager().clear_overrides(config_name)
