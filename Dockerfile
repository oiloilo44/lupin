# Python 3.12 베이스 이미지
FROM python:3.12-slim as base

# 시스템 사용자 생성 (보안 강화)
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# 작업 디렉토리 설정
WORKDIR /app

# UV 설치 (고성능 Python 패키지 매니저)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 의존성 파일만 먼저 복사 (캐싱 최적화)
COPY pyproject.toml uv.lock ./

# 개발 스테이지
FROM base as development

# 개발 의존성 포함하여 설치 (애플리케이션 코드 복사 전)
RUN uv export --with dev > requirements-dev.txt && \
    uv pip install --system -r requirements-dev.txt

# 애플리케이션 코드 복사 (의존성 설치 후)
COPY . .

# 소유자 변경
RUN chown -R appuser:appuser /app

# 비특권 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8000 8003

# 애플리케이션 실행 (개발 모드)
CMD ["python", "main.py"]

# 운영 스테이지
FROM base as production

# 운영 의존성만 설치 (애플리케이션 코드 복사 전)
RUN uv export --no-dev > requirements.txt && \
    uv pip install --system -r requirements.txt

# 애플리케이션 코드 복사 (의존성 설치 후)
COPY . .

# 소유자 변경
RUN chown -R appuser:appuser /app

# 비특권 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# 애플리케이션 실행 (운영 모드)
CMD ["python", "main.py"]
