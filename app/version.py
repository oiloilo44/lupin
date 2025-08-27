"""애플리케이션 버전 관리."""
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# 버전 계산에 사용할 핵심 파일들
CORE_FILES = [
    "main.py",
    "app/routes.py",
    "app/websocket_handler.py",
    "app/room_manager.py",
    "app/models.py",
    "app/games/omok.py",
    "app/games/omok_manager.py",
    "static/js/omok.js",
    "static/js/base.js",
    "templates/base.html",
    "templates/omok.html",
]

# 앱 버전 캐시
_app_version_cache: Optional[str] = None


def get_app_version() -> str:
    """애플리케이션 버전 반환 (핵심 파일들의 해시 기반)."""
    global _app_version_cache

    if _app_version_cache is not None:
        return _app_version_cache

    try:
        # 모든 파일의 내용을 연결하여 해시 생성
        combined_content = b""
        for file_path in CORE_FILES:
            full_path = Path(file_path)
            if full_path.exists():
                combined_content += full_path.read_bytes()
            else:
                logger.warning(f"Core file not found: {file_path}")

        # SHA256 해시의 처음 8자리 사용
        app_hash = hashlib.sha256(combined_content).hexdigest()[:8]
        _app_version_cache = app_hash

        return app_hash

    except Exception as e:
        logger.error(f"앱 버전 생성 실패: {e}")
        # 실패시 현재 시간 기반 임시 버전
        return str(int(time.time()))[:8]


# 파일 해시 캐시 (파일경로 -> (수정시간, 해시값))
_file_version_cache: Dict[str, tuple[float, str]] = {}


def get_static_file_version(file_path: str) -> str:
    """정적 파일의 해시 기반 버전 반환 (캐싱 지원)."""
    try:
        full_path = Path("static") / file_path.lstrip("/static/")
        if not full_path.exists():
            return get_app_version()

        # 파일 수정 시간 확인
        mtime = full_path.stat().st_mtime

        # 캐시에서 확인
        if file_path in _file_version_cache:
            cached_mtime, cached_hash = _file_version_cache[file_path]
            if cached_mtime == mtime:
                return cached_hash

        # 새로운 해시 계산 (SHA256 사용)
        content = full_path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()[:12]  # 12자리로 증가

        # 캐시에 저장
        _file_version_cache[file_path] = (mtime, file_hash)

        return file_hash

    except (IOError, FileNotFoundError) as e:
        # 구체적인 예외 처리로 변경
        logger.warning(f"파일 버전 생성 실패 {file_path}: {e}")
        return get_app_version()
    except Exception as e:
        # 예상하지 못한 오류
        logger.error(f"예상치 못한 오류 {file_path}: {e}")
        return get_app_version()


def add_version_to_url(url: str) -> str:
    """URL에 버전 파라미터 추가."""
    if url.startswith("/static/"):
        version = get_static_file_version(url)
        return f"{url}?v={version}"
    return url


def clear_version_cache() -> None:
    """버전 캐시 클리어 (개발/테스트용)."""
    global _file_version_cache, _app_version_cache
    _file_version_cache = {}
    _app_version_cache = None


def get_current_app_version() -> str:
    """현재 앱 버전 반환 (동적)."""
    # 개발 모드에서는 매번 새로 계산 (환경변수로 제어 가능)
    import os

    if os.getenv("DEBUG", "false").lower() == "true":
        clear_version_cache()
    return get_app_version()
