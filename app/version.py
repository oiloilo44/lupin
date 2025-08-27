"""애플리케이션 버전 관리."""
import hashlib
import time
from pathlib import Path
from typing import Dict


def get_app_version() -> str:
    """애플리케이션 버전 반환."""
    # 현재 시간 기반 버전 (배포시 자동 갱신됨)
    return str(int(time.time()))


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
        print(f"파일 버전 생성 실패 {file_path}: {e}")
        return get_app_version()
    except Exception as e:
        # 예상하지 못한 오류
        print(f"예상치 못한 오류 {file_path}: {e}")
        return get_app_version()


def add_version_to_url(url: str) -> str:
    """URL에 버전 파라미터 추가."""
    if url.startswith("/static/"):
        version = get_static_file_version(url)
        return f"{url}?v={version}"
    return url


def clear_version_cache() -> None:
    """버전 캐시 클리어 (테스트용)."""
    global _file_version_cache
    _file_version_cache.clear()


def get_current_app_version() -> str:
    """현재 앱 버전 반환 (동적)."""
    return get_app_version()


# 전역 버전
APP_VERSION = get_app_version()
