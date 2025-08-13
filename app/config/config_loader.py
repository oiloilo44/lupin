"""설정 파일 로더 및 관리 시스템."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """설정 관련 오류."""

    pass


class ConfigLoader:
    """설정 파일을 로드하고 관리하는 클래스."""

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
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._environment = os.getenv("LUPIN_ENV", "development")

        if not self.config_dir.exists():
            raise ConfigurationError(f"설정 디렉토리를 찾을 수 없습니다: {self.config_dir}")

    def load_config(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        설정 파일을 로드합니다.

        Args:
            config_name: 설정 파일 이름 (확장자 제외)
            use_cache: 캐시 사용 여부

        Returns:
            로드된 설정 딕셔너리

        Raises:
            ConfigurationError: 설정 파일을 찾을 수 없거나 파싱 오류
        """
        if use_cache and config_name in self._cache:
            config = self._cache[config_name].copy()
        else:
            config = self._load_and_merge_configs(config_name)
            if use_cache:
                self._cache[config_name] = config.copy()

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
                if isinstance(content, dict):
                    return content
                return {}
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
        """게임별 설정을 가져옵니다."""
        config = self.load_config(game_name)
        game_config = config.get(game_name, {})
        if isinstance(game_config, dict):
            return game_config
        return {}

    def get_server_config(self) -> Dict[str, Any]:
        """서버 설정을 가져옵니다."""
        config = self.load_config("default")
        return config

    def reload_config(self, config_name: str) -> Dict[str, Any]:
        """설정을 다시 로드합니다 (캐시 무시)."""
        if config_name in self._cache:
            del self._cache[config_name]
        return self.load_config(config_name, use_cache=False)

    def clear_cache(self) -> None:
        """모든 설정 캐시를 지웁니다."""
        self._cache.clear()

    def _apply_runtime_overrides(
        self, config: Dict[str, Any], config_name: str
    ) -> Dict[str, Any]:
        """런타임 오버라이드를 설정에 적용합니다."""
        # 런타임 오버라이드 매니저가 이미 초기화되어 있는지 확인
        if hasattr(self, "_runtime_manager"):
            return self._runtime_manager.apply_overrides_to_config(config, config_name)
        return config

    def set_runtime_manager(self, runtime_manager: Any) -> None:
        """런타임 매니저 설정 (순환 import 방지)."""
        self._runtime_manager = runtime_manager

    @property
    def environment(self) -> str:
        """현재 환경을 반환합니다."""
        return self._environment


# 전역 설정 로더 인스턴스
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """전역 설정 로더 인스턴스를 반환합니다."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_config(config_name: str = "default") -> Dict[str, Any]:
    """편의 함수: 설정을 가져옵니다."""
    return get_config_loader().load_config(config_name)


def get_game_config(game_name: str) -> Dict[str, Any]:
    """편의 함수: 게임 설정을 가져옵니다."""
    return get_config_loader().get_game_config(game_name)
