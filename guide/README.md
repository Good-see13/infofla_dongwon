# 📚 프로젝트 가이드

이 폴더는 프로젝트의 모든 가이드 문서를 포함하고 있습니다.

## 📋 가이드 목록

### 🚀 시작하기

- **[ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md)** - 환경 설정 및 시작 가이드

  - .env 파일 설정
  - 패키지 설치
  - 서버 실행 방법
  - API 테스트

- **[WINDOWS_SETUP_GUIDE.md](./WINDOWS_SETUP_GUIDE.md)** - Windows 환경 설정 가이드
  - PowerShell 설정
  - MariaDB 자동 설치 (Docker/로컬)
  - Python 환경 구성
  - 문제 해결

### 🗄️ 데이터베이스

- **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** ⭐ **새 환경 설정 완벽 가이드**

  - 새 환경에서 DB 설정 전체 과정
  - 테이블 자동 생성 (`db_push.py`)
  - 테이블 수정/추가 방법
  - 문제 해결
  - **가장 먼저 읽어야 할 문서!**

- **[MARIADB_SETUP_GUIDE.md](./MARIADB_SETUP_GUIDE.md)** - MariaDB 설치 가이드 (macOS)

  - Docker 설치 방법 (권장)
  - Homebrew 설치 방법
  - 유용한 명령어
  - 트러블슈팅

- **[PRISMA_STYLE_GUIDE.md](./PRISMA_STYLE_GUIDE.md)** - Prisma 스타일 DB 개발 가이드

  - 모델 정의 방법
  - `uv run python db_push.py` 사용법
  - Prisma vs SQLAlchemy 비교
  - 관계 설정 (Foreign Key)

- **[DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md)** - Alembic 마이그레이션 가이드
  - 프로덕션 배포용
  - 마이그레이션 생성 및 적용
  - 버전 관리
  - 롤백 방법

### 🔒 보안

- **[SECURITY_GUIDE.md](./SECURITY_GUIDE.md)** ⭐ **보안 가이드 (필수)**

  - SECRET_KEY 설정 (32자 이상)
  - JWT 토큰 관리 (Access + Refresh)
  - 파일 업로드 보안 (경로 탐색 공격 방지)
  - 데이터베이스 연결 풀
  - 프로덕션 체크리스트

- **[HTTPONLY_COOKIE_GUIDE.md](./HTTPONLY_COOKIE_GUIDE.md)** - HttpOnly Cookie 가이드

  - Refresh Token을 HttpOnly Cookie에 저장
  - XSS 공격 방지
  - CORS 설정
  - 프론트엔드 구현

- **[FRONTEND_TOKEN_GUIDE.md](./FRONTEND_TOKEN_GUIDE.md)** - 프론트엔드 토큰 자동 갱신
  - Axios Interceptor 구현
  - React/Vue.js 예시
  - 401 에러 자동 처리

### 📝 기타

- **[LOGGING_GUIDE.md](./LOGGING_GUIDE.md)** - 로깅 설정 가이드
  - 로그 레벨 설정
  - 로그 파일 관리
  - 로그 보관 기간

---

## 🎯 빠른 시작 (새 환경)

### 1단계: 환경 설정

```bash
# .env 파일 생성
cp env.template .env

# .env 파일 편집
vi .env
```

### 2단계: 데이터베이스 설정

```bash
# MariaDB 시작 (Docker)
docker-compose up -d db_dev

# 테이블 자동 생성 ⭐
uv run python db_push.py
```

**자세한 내용**: [DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)

### 3단계: 서버 시작

```bash
uv run python app.py
```

### 4단계: API 문서 확인

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📖 용도별 가이드

### 🆕 새 환경 설정

1. **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** ⭐ - 전체 설정 가이드
2. [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) - 환경 변수 설정

### 💻 로컬 개발

1. [PRISMA_STYLE_GUIDE.md](./PRISMA_STYLE_GUIDE.md) - 모델 정의 및 빠른 개발
2. [MARIADB_SETUP_GUIDE.md](./MARIADB_SETUP_GUIDE.md) - DB 관리 명령어

### 🚀 프로덕션 배포

1. [DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md) - 안전한 마이그레이션
2. [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) - 프로덕션 환경 설정

### ➕ 새 모델 추가

1. [PRISMA_STYLE_GUIDE.md](./PRISMA_STYLE_GUIDE.md) - 모델 작성 방법
2. `uv run python db_push.py` - 테이블 생성

---

## 🔧 추가 문서

프로젝트 루트의 다른 문서들:

- **[README.md](../README.md)** - 프로젝트 개요 및 빠른 시작
- **[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md)** - 전체 구조 설명
- **[src/api/web/README.md](../src/api/web/README.md)** - Web API 개발 가이드
- **[src/common/mariadb/models/README.md](../src/common/mariadb/models/README.md)** - 모델 작성 가이드

---

## 💡 가이드 선택 플로우차트

```
시작
 ↓
새 환경 설정? → Yes → DB_SETUP_GUIDE.md ⭐
 ↓ No
 ↓
DB 설치만? → Yes → MARIADB_SETUP_GUIDE.md
 ↓ No
 ↓
새 모델 추가? → Yes → PRISMA_STYLE_GUIDE.md
 ↓ No
 ↓
프로덕션 배포? → Yes → DB_MIGRATION_GUIDE.md
 ↓ No
 ↓
환경 변수 설정? → Yes → ENV_SETUP_GUIDE.md
 ↓ No
 ↓
완료!
```

---

## 📞 문제 해결

문제가 발생하면:

1. **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** 의 "문제 해결" 섹션 확인
2. 해당 가이드의 "트러블슈팅" 섹션 확인
3. 로그 확인 (`logs/` 폴더)
4. GitHub Issues 검색

---

## 🎓 학습 경로

### 초급 (처음 시작)

1. **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** - 전체 설정 이해 ⭐
2. [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) - 환경 설정 이해
3. [PRISMA_STYLE_GUIDE.md](./PRISMA_STYLE_GUIDE.md) - 모델 작성 기초

### 중급 (개발)

1. [MARIADB_SETUP_GUIDE.md](./MARIADB_SETUP_GUIDE.md) - DB 관리
2. [src/api/web/README.md](../src/api/web/README.md) - API 개발
3. [LOGGING_GUIDE.md](./LOGGING_GUIDE.md) - 로깅 설정

### 고급 (배포)

1. [DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md) - 마이그레이션 관리
2. [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - 아키텍처 이해

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24
