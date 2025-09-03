"""설정 파일 로더 및 관리 시스템 (Pydantic 기반)."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from .schemas import AppConfig

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """설정 관련 오류."""

    pass


class ConfigLoader:
    """설정 파일을 로드하고 관리하는 클래스 (Pydantic 검증 포함)."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: 설정 파일 디렉토리 경로. None이면 기본 경로 사용
        """
        if config_dir is None:
            # 프로젝트 루트의 config 디렉토리
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._cache: Dict[str, AppConfig] = {}
        self._raw_cache: Dict[str, Dict[str, Any]] = {}
        self._environment = os.getenv("LUPIN_ENV", "development")
        self._runtime_manager: Optional[Any] = None

        if not self.config_dir.exists():
            raise ConfigurationError(
                f"설정 디렉토리를 찾을 수 없습니다: {self.config_dir}"
            )

    def load_config(
        self, config_name: str = "default", use_cache: bool = True
    ) -> AppConfig:
        """
        설정 파일을 로드하고 Pydantic으로 검증합니다.

        Args:
            config_name: 설정 파일 이름 (확장자 제외)
            use_cache: 캐시 사용 여부

        Returns:
            검증된 AppConfig 인스턴스

        Raises:
            ConfigurationError: 설정 파일을 찾을 수 없거나 파싱/검증 오류
        """
        if use_cache and config_name in self._cache:
            return self._cache[config_name]

        # Raw 설정 로드
        raw_config = self._load_raw_config(config_name, use_cache)

        # Pydantic 모델로 검증 및 변환
        try:
            validated_config = AppConfig(**raw_config)
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")
            raise ConfigurationError("설정 검증 실패:\n" + "\n".join(error_messages))

        if use_cache:
            self._cache[config_name] = validated_config

        return validated_config

    def load_raw_config(
        self, config_name: str = "default", use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        기존 방식과의 호환성을 위한 raw 설정 로드 (딕셔너리 반환).

        Args:
            config_name: 설정 파일 이름 (확장자 제외)
            use_cache: 캐시 사용 여부

        Returns:
            로드된 설정 딕셔너리

        Raises:
            ConfigurationError: 설정 파일을 찾을 수 없거나 파싱 오류
        """
        return self._load_raw_config(config_name, use_cache)

    def _load_raw_config(
        self, config_name: str, use_cache: bool = True
    ) -> Dict[str, Any]:
        """내부 메서드: raw 설정 로드."""
        if use_cache and config_name in self._raw_cache:
            config = self._raw_cache[config_name].copy()
        else:
            config = self._load_and_merge_configs(config_name)
            if use_cache:
                self._raw_cache[config_name] = config.copy()

        # 런타임 오버라이드 적용 (캐시된 설정에도 적용)
        config = self._apply_runtime_overrides(config, config_name)

        return config

    def _load_and_merge_configs(self, config_name: str) -> Dict[str, Any]:
        """설정 파일들을 로드하고 병합합니다."""
        # 1. 기본 설정 로드
        base_config = self._load_yaml_file("default.yaml")

        # 2. 환경별 설정 로드 및 병합
        env_file = f"{self._environment}.yaml"
        env_config_path = self.config_dir / env_file

        if env_config_path.exists():
            env_config = self._load_yaml_file(env_file)
            base_config = self._deep_merge(base_config, env_config)

        # 3. 특정 설정 파일 로드 및 병합 (게임별 설정 등)
        if config_name != "default" and config_name != self._environment:
            # games/ 디렉토리에서 먼저 찾기
            game_config_path = self.config_dir / "games" / f"{config_name}.yaml"
            if game_config_path.exists():
                game_config = self._load_yaml_file(f"games/{config_name}.yaml")
                base_config = self._deep_merge(base_config, game_config)
            else:
                # 루트 디렉토리에서 찾기
                config_file = f"{config_name}.yaml"
                config_path = self.config_dir / config_file
                if config_path.exists():
                    specific_config = self._load_yaml_file(config_file)
                    base_config = self._deep_merge(base_config, specific_config)

        return base_config

    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """YAML 파일을 로드합니다."""
        file_path = self.config_dir / filename

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if content is None:
                    return {}
                if not isinstance(content, dict):
                    raise ConfigurationError(
                        f"설정 파일 내용이 딕셔너리가 아닙니다: {file_path}. "
                        f"YAML 파일은 키-값 쌍을 포함해야 합니다."
                    )
                return content
        except FileNotFoundError:
            raise ConfigurationError(f"설정 파일을 찾을 수 없습니다: {file_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML 파싱 오류 in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"설정 파일 로드 오류 {file_path}: {e}")

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """두 딕셔너리를 깊이 병합합니다."""
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

    def get_game_config(self, game_name: str) -> Dict[str, Any]:
        """게임별 설정을 가져옵니다 (하위 호환성)."""
        config = self.load_config()
        game_configs = config.games.model_dump()
        return game_configs.get(game_name, {})

    def get_server_config(self) -> AppConfig:
        """서버 설정을 가져옵니다 (Pydantic 모델)."""
        return self.load_config("default")

    def get_raw_server_config(self) -> Dict[str, Any]:
        """서버 설정을 딕셔너리로 가져옵니다 (하위 호환성)."""
        return self.load_raw_config("default")

    def reload_config(self, config_name: str = "default") -> AppConfig:
        """설정을 다시 로드합니다 (캐시 무시)."""
        if config_name in self._cache:
            del self._cache[config_name]
        if config_name in self._raw_cache:
            del self._raw_cache[config_name]
        return self.load_config(config_name, use_cache=False)

    def clear_cache(self) -> None:
        """모든 설정 캐시를 지웁니다."""
        self._cache.clear()
        self._raw_cache.clear()

    def _apply_runtime_overrides(
        self, config: Dict[str, Any], config_name: str
    ) -> Dict[str, Any]:
        """런타임 오버라이드를 설정에 적용합니다."""
        # 런타임 오버라이드 매니저가 이미 초기화되어 있고 None이 아닌지 확인
        if hasattr(self, "_runtime_manager") and self._runtime_manager is not None:
            return self._runtime_manager.apply_overrides_to_config(config, config_name)
        return config

    def set_runtime_manager(self, runtime_manager: Any) -> None:
        """런타임 매니저 설정 (순환 import 방지)."""
        self._runtime_manager = runtime_manager

    @property
    def environment(self) -> str:
        """현재 환경을 반환합니다."""
        return self._environment

    def validate_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """딕셔너리 설정을 검증하고 AppConfig 인스턴스를 반환합니다."""
        try:
            return AppConfig(**config_dict)
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_messages.append(f"  - {loc}: {msg}")
            raise ConfigurationError("설정 검증 실패:\n" + "\n".join(error_messages))


# 전역 설정 로더 인스턴스
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """전역 설정 로더 인스턴스를 반환합니다."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_config(config_name: str = "default") -> Dict[str, Any]:
    """편의 함수: 설정을 딕셔너리로 가져옵니다 (하위 호환성)."""
    return get_config_loader().load_raw_config(config_name)


def get_validated_config(config_name: str = "default") -> AppConfig:
    """편의 함수: 검증된 설정을 가져옵니다."""
    return get_config_loader().load_config(config_name)


def get_game_config(game_name: str) -> Dict[str, Any]:
    """편의 함수: 게임 설정을 가져옵니다."""
    return get_config_loader().get_game_config(game_name)
