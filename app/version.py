"""애플리케이션 버전 관리."""
import hashlib
import time
from pathlib import Path


def get_app_version() -> str:
    """애플리케이션 버전 반환."""
    # 현재 시간 기반 버전 (배포시 자동 갱신됨)
    return str(int(time.time()))


def get_static_file_version(file_path: str) -> str:
    """정적 파일의 해시 기반 버전 반환."""
    try:
        full_path = Path("static") / file_path.lstrip("/static/")
        if full_path.exists():
            content = full_path.read_bytes()
            return hashlib.md5(content).hexdigest()[:8]
    except Exception:
        pass
    return get_app_version()


def add_version_to_url(url: str) -> str:
    """URL에 버전 파라미터 추가."""
    if url.startswith("/static/"):
        version = get_static_file_version(url)
        return f"{url}?v={version}"
    return url


# 전역 버전
APP_VERSION = get_app_version()
