# 🔒 보안 가이드

프로젝트의 보안 설정 및 모범 사례 가이드입니다.

---

## 📋 목차

1. [보안 개선 사항](#보안-개선-사항)
2. [환경 변수 설정](#환경-변수-설정)
3. [JWT 토큰 관리](#jwt-토큰-관리)
4. [파일 업로드 보안](#파일-업로드-보안)
5. [데이터베이스 보안](#데이터베이스-보안)
6. [프로덕션 체크리스트](#프로덕션-체크리스트)

---

## 🛡️ 보안 개선 사항

### ✅ 적용된 보안 조치

#### 1. **SECRET_KEY 강화**

- 최소 32자 이상 필수
- 자동 랜덤 키 생성 (개발 환경)
- 프로덕션에서는 환경 변수 필수 설정

```python
# 안전한 SECRET_KEY 생성
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

#### 2. **Refresh Token 구현**

- Access Token: 15분 (짧은 유효 기간)
- Refresh Token: 7일
- **HttpOnly Cookie 저장** (XSS 공격 방지) ⭐
- Token Rotation (갱신 시 새 Refresh Token 발급)
- 토큰 타입 검증 ("access" vs "refresh")
- SameSite=Lax (CSRF 방지)

#### 3. **파일 업로드 보안**

- **경로 탐색 공격 방지**: item_id 검증 및 경로 정규화
- **파일명 정제**: 위험한 문자 제거, 연속된 점(`.`) 제거
- **파일 검증**: 확장자 + 매직 넘버 (바이트 코드) 이중 검증
- **파일 크기 제한**: 10MB
- **스트림 처리**: 메모리 효율적 업로드

#### 4. **데이터베이스 연결 풀**

- 개발 환경: NullPool (연결 풀 미사용)
- 프로덕션: 연결 풀 활성화 (pool_size=20, max_overflow=10)

#### 5. **비밀번호 보안**

- bcrypt 해싱
- 최소 6자 이상 (권장: 8자 이상)
- 로그인 실패 5회 시 계정 잠금

---

## ⚙️ 환경 변수 설정

### `.env` 파일 (필수)

```env
# ==========================================
# 보안 설정
# ==========================================

# 환경 타입 (development / production)
ENVIRONMENT=development

# JWT Secret Key (32자 이상, 프로덕션에서 필수!)
SECRET_KEY=your-secret-key-here-change-in-production

# JWT 설정
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ==========================================
# 데이터베이스 설정
# ==========================================

USE_DATABASE=true
DATABASE_URL="mysql+aiomysql://root:12345@localhost:3307/dongwon"

# MariaDB 환경 변수
MARIADB_ROOT_PASSWORD=12345
MARIADB_DATABASE=dongwon
MARIADB_USER=test
MARIADB_PASSWORD=12345
MARIADB_PORT=3307

# ==========================================
# 파일 업로드 설정
# ==========================================

UPLOAD_PATH=./uploads

# ==========================================
# 로그 설정
# ==========================================

LOG_RETENTION_DAYS=30
```

### 프로덕션 환경 설정

```env
# 프로덕션 환경
ENVIRONMENT=production

# 강력한 SECRET_KEY 생성 (예시)
SECRET_KEY=AbCdEfGh1234567890IjKlMnOpQrStUvWxYz_-AbCdEfGh

# 짧은 Access Token
ACCESS_TOKEN_EXPIRE_MINUTES=15

# 강력한 데이터베이스 비밀번호
MARIADB_ROOT_PASSWORD=your-strong-password-here
MARIADB_PASSWORD=your-strong-password-here
```

---

## 🔑 JWT 토큰 관리

### Access Token vs Refresh Token

| 항목          | Access Token      | Refresh Token                   |
| ------------- | ----------------- | ------------------------------- |
| **유효 기간** | 15분              | 7일                             |
| **용도**      | API 인증          | Access Token 갱신               |
| **저장 위치** | 메모리 (권장)     | **HttpOnly Cookie (적용됨)** ✅ |
| **갱신**      | Refresh Token으로 | 로그인 시 발급                  |

### 토큰 사용 흐름

```
1. 로그인
   POST /api/web/auth/login
   → Access Token (JSON 응답)
   → Refresh Token (HttpOnly Cookie 자동 저장) ✅

2. API 호출
   Header: Authorization: Bearer <access_token>

3. Access Token 만료 (15분 후)
   POST /api/web/auth/refresh
   → Cookie에서 자동으로 Refresh Token 읽음 ✅
   → 새 Access Token (JSON 응답)
   → 새 Refresh Token (HttpOnly Cookie 자동 갱신) ✅

4. 로그아웃
   POST /api/web/auth/logout
   → Cookie에서 Refresh Token 삭제 ✅

5. Refresh Token 만료 (7일 후)
   → 재로그인 필요
```

### 프론트엔드 구현 예시 (HttpOnly Cookie 사용)

```javascript
// Access Token 저장 (메모리)
let accessToken = null;

// 로그인
const loginResponse = await fetch("/api/web/auth/login", {
  method: "POST",
  credentials: "include", // ⭐ Cookie 자동 전송/저장
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ loginId: "test", password: "123123" }),
});

const { access_token, user } = await loginResponse.json();
accessToken = access_token;
// Refresh Token은 자동으로 Cookie에 저장됨 ✅

// API 호출 시
const response = await fetch("/api/web/item/", {
  credentials: "include", // ⭐ Cookie 자동 전송
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});

// 401 에러 시 토큰 갱신
if (response.status === 401) {
  const refreshResponse = await fetch("/api/web/auth/refresh", {
    method: "POST",
    credentials: "include", // ⭐ Cookie에서 자동으로 Refresh Token 읽음
  });

  const { access_token } = await refreshResponse.json();
  accessToken = access_token;
  // 새 Refresh Token도 자동으로 Cookie에 저장됨 ✅

  // 원래 요청 재시도
  return fetch("/api/web/item/", {
    credentials: "include",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

// 로그아웃
await fetch("/api/web/auth/logout", {
  method: "POST",
  credentials: "include", // ⭐ Cookie 자동 삭제
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
});
accessToken = null;
```

**핵심 변경 사항:**

- `credentials: "include"` 추가 (Cookie 자동 전송/저장)
- Refresh Token을 수동으로 관리할 필요 없음 ✅
- XSS 공격으로부터 Refresh Token 보호 ✅

---

## 📁 파일 업로드 보안

### 적용된 보안 조치

#### 1. **파일 검증**

```python
# 확장자 검증
allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

# 매직 넘버 검증 (바이트 코드)
image_signatures = {
    b"\xff\xd8\xff": "jpg",  # JPEG
    b"\x89\x50\x4e\x47": "png",  # PNG
    ...
}
```

#### 2. **파일명 정제**

```python
# 위험한 문자 제거
safe_name = re.sub(r'[^a-zA-Z0-9._\-가-힣]', '_', filename)

# 연속된 점 제거 (../ 공격 방지)
safe_name = re.sub(r'\.+', '.', safe_name)

# 경로 구분자 제거
filename = filename.replace("/", "_").replace("\\", "_")
```

#### 3. **경로 검증**

```python
# 경로 정규화
resolved_folder = item_folder.resolve()
resolved_base = base_path.resolve()

# base_path 하위에 있는지 확인
resolved_folder.relative_to(resolved_base)
```

#### 4. **파일 크기 제한**

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

---

## 🗄️ 데이터베이스 보안

### SQL Injection 방지

```python
# ✅ 안전 (SQLAlchemy ORM 사용)
result = await db.execute(
    select(User).where(User.loginId == login_id)
)

# ❌ 위험 (절대 사용 금지)
# query = f"SELECT * FROM users WHERE loginId = '{login_id}'"
```

### 연결 풀 설정

```python
# 개발 환경
ENVIRONMENT=development
→ NullPool (연결 풀 미사용)

# 프로덕션 환경
ENVIRONMENT=production
→ pool_size=20, max_overflow=10
```

### 비밀번호 관리

```python
# bcrypt 해싱
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 해싱
hashed = pwd_context.hash(plain_password)

# 검증
is_valid = pwd_context.verify(plain_password, hashed_password)
```

---

## ✅ 프로덕션 체크리스트

### 🔴 필수 (Critical)

- [ ] **SECRET_KEY 설정**: 32자 이상, 랜덤 생성
- [ ] **CORS 설정**: 특정 도메인만 허용 (`allow_origins=["*"]` 제거)
- [ ] **HTTPS 강제**: 프로덕션에서는 HTTPS만 사용
- [ ] **데이터베이스 비밀번호**: 강력한 비밀번호 사용
- [ ] **환경 변수 확인**: `ENVIRONMENT=production` 설정

### 🟠 권장 (Recommended)

- [ ] **Rate Limiting**: API 호출 횟수 제한 (slowapi)
- [ ] **비밀번호 정책**: 최소 8자, 대소문자+숫자+특수문자
- [ ] **로그 모니터링**: 에러 로그 실시간 모니터링
- [ ] **백업**: 데이터베이스 정기 백업
- [ ] **방화벽**: 불필요한 포트 차단

### 🟡 추가 보안 (Optional)

- [ ] **2FA**: 2단계 인증
- [ ] **IP 화이트리스트**: 관리자 API는 특정 IP만 허용
- [ ] **보안 헤더**: X-Frame-Options, CSP 등
- [ ] **세션 관리**: 동시 로그인 제한
- [ ] **감사 로그**: 중요 작업 로그 기록

---

## 🚨 보안 사고 대응

### 1. SECRET_KEY 유출 시

```bash
# 1. 즉시 SECRET_KEY 변경
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# 2. .env 파일 업데이트
SECRET_KEY=<new-secret-key>

# 3. 서버 재시작
# 모든 기존 토큰 무효화됨

# 4. 사용자에게 재로그인 요청
```

### 2. 데이터베이스 비밀번호 유출 시

```bash
# 1. 데이터베이스 비밀번호 변경
mysql -u root -p
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new-password';

# 2. .env 파일 업데이트
MARIADB_ROOT_PASSWORD=new-password

# 3. 서버 재시작
```

### 3. 파일 업로드 공격 감지 시

```bash
# 1. 로그 확인
tail -f logs/error/$(date +%Y-%m-%d).log | grep "경로 탐색 공격"

# 2. 업로드 폴더 확인
find uploads/ -type f -name "*.php" -o -name "*.sh"

# 3. 의심 파일 삭제
rm -f uploads/suspicious-file.php
```

---

## 📚 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

---

## 🔧 보안 테스트

### JWT 토큰 테스트

```bash
# 로그인
TOKEN=$(curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' | \
  jq -r '.access_token')

# API 호출
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/web/auth/me

# 토큰 갱신
REFRESH_TOKEN=$(curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' | \
  jq -r '.refresh_token')

curl -X POST 'http://localhost:8000/api/web/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
```

### 파일 업로드 테스트

```bash
# 정상 이미지 업로드
curl -X POST "http://localhost:8000/api/web/item/1/upload-images" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.jpg"

# 악의적 파일명 테스트 (자동 정제됨)
curl -X POST "http://localhost:8000/api/web/item/1/upload-images" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@../../../etc/passwd.jpg"
```

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24  
**버전**: 1.0.0
