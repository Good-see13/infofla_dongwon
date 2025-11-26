# 로깅 시스템 가이드

## 📁 로그 구조

```
dongwon/
└── logs/
    ├── info/
    │   ├── 2025-01-15.log
    │   ├── 2025-01-16.log
    │   └── ...
    └── error/
        ├── 2025-01-15.log
        ├── 2025-01-16.log
        └── ...
```

## 🎯 로그 레벨별 저장 위치

| 레벨     | 저장 위치                   | 설명             |
| -------- | --------------------------- | ---------------- |
| INFO     | `logs/info/YYYY-MM-DD.log`  | 정보성 로그      |
| WARNING  | `logs/info/YYYY-MM-DD.log`  | 경고 로그        |
| ERROR    | `logs/error/YYYY-MM-DD.log` | 에러 로그        |
| CRITICAL | `logs/error/YYYY-MM-DD.log` | 치명적 에러 로그 |

## ⚙️ 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# 로그 보관 기간 (일)
LOG_RETENTION_DAYS=30  # 기본값: 30일
```

### 보관 기간 옵션

- `LOG_RETENTION_DAYS=7` - 7일 보관
- `LOG_RETENTION_DAYS=30` - 30일 보관 (권장)
- `LOG_RETENTION_DAYS=90` - 90일 보관

## 🔄 로그 자동 관리

### 1. 일별 로그 파일 생성

- 매일 자정(00:00)에 새로운 로그 파일이 생성됩니다
- 파일명: `YYYY-MM-DD.log` 형식

### 2. 자동 삭제

- 서버 시작 시 `LOG_RETENTION_DAYS`보다 오래된 로그 파일을 자동으로 삭제합니다
- 예: `LOG_RETENTION_DAYS=30`인 경우, 30일 이전 로그는 자동 삭제

## 📝 로그 포맷

```
YYYY-MM-DD HH:MM:SS - module_name - LEVEL - filename:line - message
```

**예시:**

```
2025-01-15 14:30:25 - app - INFO - app.py:45 - Server started successfully
2025-01-15 14:30:26 - auth_service - ERROR - auth_service.py:67 - Login failed for user: testuser
```

## 💻 코드에서 로그 사용하기

### 기본 사용법

```python
import logging

logger = logging.getLogger(__name__)

# INFO 레벨 (logs/info/에 저장)
logger.info("User logged in successfully")
logger.warning("Password will expire in 3 days")

# ERROR 레벨 (logs/error/에 저장)
logger.error("Database connection failed")
logger.critical("System is shutting down")
```

### 예외 로깅

```python
try:
    result = some_function()
except Exception as e:
    logger.error(f"Error occurred: {e}", exc_info=True)
    # exc_info=True를 사용하면 스택 트레이스도 로그에 포함됩니다
```

### FastAPI에서 사용

```python
from fastapi import APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/login")
async def login(user_data: dict):
    logger.info(f"Login attempt: {user_data.get('username')}")

    try:
        # 로그인 로직
        result = authenticate_user(user_data)
        logger.info(f"Login successful: {user_data.get('username')}")
        return result
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise
```

## 🔍 로그 조회

### 실시간 로그 확인 (터미널)

```bash
# INFO 로그 실시간 확인
tail -f logs/info/$(date +%Y-%m-%d).log

# ERROR 로그 실시간 확인
tail -f logs/error/$(date +%Y-%m-%d).log

# 모든 로그 실시간 확인
tail -f logs/info/$(date +%Y-%m-%d).log logs/error/$(date +%Y-%m-%d).log
```

### 특정 키워드 검색

```bash
# ERROR 로그에서 "database" 키워드 검색
grep -i "database" logs/error/2025-01-15.log

# 최근 7일간의 ERROR 로그에서 검색
grep -i "database" logs/error/*.log
```

### 날짜별 로그 확인

```bash
# 특정 날짜의 INFO 로그
cat logs/info/2025-01-15.log

# 특정 날짜의 ERROR 로그
cat logs/error/2025-01-15.log
```

## 📊 로그 분석 예시

### 오류 발생 빈도 확인

```bash
# ERROR 로그에서 발생 빈도 상위 10개 확인
grep "ERROR" logs/error/$(date +%Y-%m-%d).log | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
```

### 특정 사용자의 활동 로그 추출

```bash
# 특정 사용자(testuser)의 로그만 추출
grep "testuser" logs/info/$(date +%Y-%m-%d).log
```

## 🚨 주의사항

### 1. 로그에 민감한 정보 기록 금지

```python
# ❌ 나쁜 예
logger.info(f"Login: {username}, Password: {password}")

# ✅ 좋은 예
logger.info(f"Login attempt: {username}")
```

### 2. 적절한 로그 레벨 사용

```python
# ❌ 모든 것을 ERROR로 로깅
logger.error("User clicked button")

# ✅ 적절한 레벨 사용
logger.info("User clicked button")
logger.warning("API rate limit approaching")
logger.error("Database connection failed")
```

### 3. 로그 볼륨 관리

- 너무 많은 DEBUG 로그는 성능 저하 및 디스크 공간 낭비
- 프로덕션에서는 INFO 레벨 이상만 사용 권장

## 🔧 개발/프로덕션 환경별 설정

### 개발 환경

```python
# .env
LOG_RETENTION_DAYS=7  # 짧은 보관 기간
```

### 프로덕션 환경

```python
# .env
LOG_RETENTION_DAYS=90  # 긴 보관 기간
```

## 📦 디스크 공간 관리

예상 로그 크기 (일일):

- 일반 트래픽: 10-50 MB/day
- 높은 트래픽: 100-500 MB/day

30일 보관 시:

- 일반: 300 MB - 1.5 GB
- 높음: 3 GB - 15 GB

## 🛠️ 트러블슈팅

### 로그 파일이 생성되지 않음

1. `logs/` 디렉토리 권한 확인
2. 서버 재시작 후 확인
3. `.env`에 `LOG_RETENTION_DAYS` 설정 확인

### 로그가 삭제되지 않음

- 서버를 재시작하면 시작 시 자동으로 오래된 로그가 삭제됩니다

### 로그가 너무 많이 쌓임

- `LOG_RETENTION_DAYS` 값을 줄이고 서버 재시작

## 📚 참고 자료

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler)
