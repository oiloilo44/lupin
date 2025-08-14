# Docker 환경 구성 가이드

## 📋 개요

Lupin 프로젝트는 개발/운영 환경을 분리하여 Docker로 실행할 수 있습니다.

## 🚀 빠른 시작

### 개발 환경

```bash
# 개발 환경 실행 (핫 리로드 지원)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# 빌드 후 실행
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

개발 환경 특징:
- 코드 변경시 자동 리로드
- 포트 8000, 8003 직접 노출
- 디버그 모드 활성화
- 볼륨 마운트로 실시간 코드 반영

### 운영 환경

```bash
# .env 파일 설정
cp .env.example .env
# DOMAIN_NAME과 SUBDOMAIN 설정 필요

# 운영 환경 실행
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 로그 확인
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

운영 환경 특징:
- Traefik 리버스 프록시 통합
- SSL/TLS 자동 설정
- 보안 헤더 적용
- 비root 사용자 실행
- 헬스체크 활성화

## 🏗️ 아키텍처

### 멀티스테이지 빌드

```
Dockerfile
├── builder stage     # 의존성 준비
├── development      # 개발 환경
└── production      # 운영 환경 (최적화)
```

### 파일 구조

```
docker-compose.yml          # 베이스 설정
docker-compose.dev.yml      # 개발 오버라이드
docker-compose.prod.yml     # 운영 오버라이드
Dockerfile                  # 멀티스테이지 빌드
.env.example               # 환경변수 템플릿
```

## 📊 헬스체크

### 엔드포인트

- `/health` - 기본 헬스체크
- `/health/live` - 라이브니스 프로브
- `/health/ready` - 레디니스 프로브
- `/health/detailed` - 상세 상태 정보

### 확인 방법

```bash
# 개발 환경
curl http://localhost:8000/health

# 운영 환경
curl https://game.example.com/health

# 상세 정보
curl http://localhost:8000/health/detailed
```

## 🔧 환경 변수

### 필수 설정

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| LUPIN_ENV | 환경 (development/production) | development |
| PORT | 서버 포트 | 8000 |
| DEBUG | 디버그 모드 | false |
| LOG_LEVEL | 로그 레벨 | INFO |

### 운영 환경 전용

| 변수명 | 설명 | 예시 |
|--------|------|------|
| DOMAIN_NAME | 도메인 이름 | example.com |
| SUBDOMAIN | 서브도메인 | game |

## 🔒 보안 설정

### 개발 환경
- 로컬 접근만 허용
- 디버그 정보 노출

### 운영 환경
- 비root 사용자 (lupin) 실행
- 보안 헤더 자동 적용 (HSTS, XSS Protection 등)
- SSL/TLS 강제 적용
- 최소 권한 원칙

## 📈 모니터링

### 메트릭 확인

```bash
# 성능 메트릭
curl http://localhost:8003/api/monitoring/metrics

# WebSocket 연결 상태
curl http://localhost:8003/api/monitoring/connections

# 게임 세션 통계
curl http://localhost:8003/api/monitoring/games
```

## 🐛 문제 해결

### 컨테이너 재시작

```bash
# 개발
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart

# 운영
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
```

### 로그 확인

```bash
# 실시간 로그
docker logs -f lupin-game

# 최근 100줄
docker logs --tail 100 lupin-game
```

### 컨테이너 접속

```bash
# 개발 환경 (root)
docker exec -it lupin-game bash

# 운영 환경 (lupin 사용자)
docker exec -it lupin-game sh
```

## 🔄 업데이트 절차

### 운영 환경 무중단 업데이트

```bash
# 1. 새 이미지 빌드
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# 2. 롤링 업데이트
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build lupin

# 3. 헬스체크 확인
curl https://game.example.com/health
```

## 📝 체크리스트

### 개발 환경 시작 전
- [ ] Docker, Docker Compose 설치 확인
- [ ] 포트 8000, 8003 사용 가능 확인

### 운영 배포 전
- [ ] .env 파일 설정 완료
- [ ] Traefik 네트워크 (proxy_network) 생성 확인
- [ ] 도메인 DNS 설정 확인
- [ ] 백업 계획 수립

## 🆘 지원

문제가 발생하면:
1. 로그 확인 (`docker logs`)
2. 헬스체크 상태 확인
3. 환경 변수 설정 확인
4. GitHub Issues에 문의
