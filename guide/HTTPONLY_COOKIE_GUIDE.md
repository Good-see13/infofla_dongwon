# 🍪 HttpOnly Cookie로 Refresh Token 보호

Refresh Token을 HttpOnly Cookie에 저장하여 XSS 공격으로부터 보호하는 구현 가이드입니다.

---

## ✅ 구현 완료

### **현재 상태: HttpOnly Cookie 적용됨** 🔒

Refresh Token은 JSON 응답으로 반환되지 않고, **자동으로 HttpOnly Cookie에 저장**됩니다.

---

## 🔒 보안 효과

```json
// 로그인 응답 (JSON)
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { ... }
}
// ✅ refresh_token은 JSON 응답에 포함되지 않음!

// + HttpOnly Cookie (자동 저장)
Set-Cookie: refresh_token=eyJhbGc...; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800
```

**보안 개선:**

- **Refresh Token이 JSON 응답에 노출되지 않음** ✅
- **JavaScript로 접근 불가** ✅
- **XSS 공격 방지** ✅
- **CSRF 방지** (SameSite=Lax) ✅
- 자동으로 Cookie 전송/갱신 ✅

---

## 🔧 Cookie 설정 상세

### 로그인 시 Cookie 설정

```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token_value,
    httponly=True,      # JavaScript 접근 차단 (XSS 방지)
    secure=False,       # 개발: False, 프로덕션: True (HTTPS 필수)
    samesite="lax",     # CSRF 방지 (lax/strict/none)
    max_age=604800,     # 7일 (초 단위)
    path="/"            # 모든 경로에서 사용 가능 (새로고침 시에도 유지)
)
```

### Cookie 속성 설명

| 속성         | 값                                  | 설명                                         |
| ------------ | ----------------------------------- | -------------------------------------------- |
| **httponly** | `True`                              | JavaScript로 접근 불가 (XSS 방지)            |
| **secure**   | `False` (개발)<br>`True` (프로덕션) | HTTPS에서만 전송                             |
| **samesite** | `lax`                               | Cross-Site 요청 제한 (CSRF 방지)             |
| **max_age**  | `604800`                            | 7일 (초 단위)                                |
| **path**     | `/`                                 | 모든 경로에서 Cookie 전송 (새로고침 시 유지) |

---

## ⚠️ Swagger UI 사용 시 주의사항

### **Refresh Token을 Swagger에 직접 입력하면 안 됩니다!**

**문제 상황:**

브라우저 개발자 도구에서 `refresh_token` 쿠키를 복사하여 Swagger UI의 "Authorize" 버튼에 입력하면 **"유효하지 않은 토큰 타입입니다"** 에러가 발생합니다.

**원인:**

```python
# JWT 토큰 생성 시 타입 구분
create_access_token()  → {"type": "access", ...}
create_refresh_token() → {"type": "refresh", ...}

# 토큰 검증 시 타입 확인
verify_token(token, token_type="access")  # Swagger Authorization은 access 타입만 허용
verify_token(token, token_type="refresh") # refresh API만 허용
```

Swagger UI의 "Authorize" 버튼은 **Access Token만** 입력해야 합니다. Refresh Token은 HttpOnly Cookie에 저장되어 자동으로 전송되므로 수동으로 입력할 필요가 없습니다.

**올바른 사용법:**

1. **로그인 API 호출** (`POST /api/web/auth/login`)

   - Swagger UI에서 로그인 실행
   - 응답에서 `access_token` 복사
   - `refresh_token`은 자동으로 Cookie에 저장됨 (복사 불필요)

2. **Authorize 버튼에 Access Token 입력**

   ```
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **토큰 갱신 API 호출** (`POST /api/web/auth/refresh`)
   - Swagger UI에서 실행하면 Cookie에서 자동으로 Refresh Token 읽음
   - 새 `access_token` 받음
   - 새 `refresh_token`도 자동으로 Cookie에 저장됨

**Swagger UI 제한 사항:**

- ⚠️ **Swagger UI는 Cookie를 완벽하게 지원하지 않습니다**
- Swagger UI에서 로그인해도 Cookie가 저장되지 않거나 새로고침 시 사라질 수 있습니다
- `/api/web/auth/refresh` API를 Swagger에서 테스트하면 Cookie를 읽지 못할 수 있습니다
- **실제 테스트는 `curl` 또는 Postman 사용을 권장합니다**

**새로고침 시 쿠키가 사라지는 이유:**

1. **Swagger UI 자체의 제한**: Swagger UI는 브라우저 기반이지만 Cookie 관리가 제한적입니다
2. **이전 설정 (`path="/api/web/auth"`)**: 특정 경로에서만 Cookie가 전송되어 새로고침 시 보이지 않았습니다
3. **현재 설정 (`path="/"`)**: 모든 경로에서 Cookie가 전송되지만, Swagger UI는 여전히 Cookie를 제대로 표시하지 못할 수 있습니다

**해결 방법:**

- 브라우저 개발자 도구(F12 → Application → Cookies)에서 쿠키를 직접 확인하세요
- 실제 프론트엔드 애플리케이션에서는 정상 작동합니다
- 테스트는 `curl` 또는 Postman을 사용하세요

**⚠️ 중복 쿠키 문제:**

이전 버전에서 `path="/api/web/auth"`로 설정된 쿠키가 남아있을 수 있습니다. 이 경우 두 개의 `refresh_token` 쿠키가 동시에 존재합니다:

```
refresh_token (Path: /api/web/auth)  ← 이전 쿠키
refresh_token (Path: /)              ← 새 쿠키
```

**해결 방법:**

1. **자동 삭제**: 다음 로그인/토큰 갱신 시 이전 쿠키가 자동으로 삭제됩니다
2. **수동 삭제**: 브라우저 개발자 도구에서 `path="/api/web/auth"` 쿠키를 직접 삭제
3. **로그아웃**: 로그아웃 시 모든 경로의 쿠키가 삭제됩니다

**curl로 테스트:**

```bash
# 1. 로그인 (Cookie 저장)
curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' \
  -c cookies.txt

# 2. 토큰 갱신 (Cookie에서 자동으로 읽음)
curl -X POST 'http://localhost:8000/api/web/auth/refresh' \
  -b cookies.txt -c cookies.txt

# 3. 인증이 필요한 API 호출
ACCESS_TOKEN="<로그인 응답의 access_token>"
curl -X GET 'http://localhost:8000/api/web/auth/me' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -b cookies.txt
```

---

## 📡 API 사용법

### 1. 로그인 (`POST /api/web/auth/login`)

```bash
curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' \
  -c cookies.txt  # ⭐ Cookie 저장
```

**응답:**

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "loginId": "test",
    "name": "슈퍼관리자",
    "email": "test@example.com",
    "description": "..."
  }
}
// ✅ refresh_token은 JSON 응답에 포함되지 않음 (Cookie에만 저장)
```

**Cookie 저장:**

```
Set-Cookie: refresh_token=eyJhbGc...; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800
```

---

### 2. 토큰 갱신 (`POST /api/web/auth/refresh`)

```bash
curl -X POST 'http://localhost:8000/api/web/auth/refresh' \
  -b cookies.txt  # ⭐ Cookie에서 자동으로 읽음
```

**특징:**

- Request Body 불필요 (Cookie에서 자동으로 읽음)
- 새 Refresh Token도 자동으로 Cookie에 저장 (Rotation)

---

### 3. 로그아웃 (`POST /api/web/auth/logout`)

```bash
curl -X POST 'http://localhost:8000/api/web/auth/logout' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -b cookies.txt  # ⭐ Cookie 자동 삭제
```

**특징:**

- Cookie에서 Refresh Token 자동 삭제

---

## 🌐 프론트엔드 구현

### Fetch API

```javascript
// 로그인
const loginResponse = await fetch("http://localhost:8000/api/web/auth/login", {
  method: "POST",
  credentials: "include", // ⭐ Cookie 자동 전송/저장
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ loginId: "test", password: "123123" }),
});

const { access_token, user } = await loginResponse.json();
// Refresh Token은 자동으로 Cookie에 저장됨 ✅

// 토큰 갱신
const refreshResponse = await fetch(
  "http://localhost:8000/api/web/auth/refresh",
  {
    method: "POST",
    credentials: "include", // ⭐ Cookie에서 자동으로 Refresh Token 읽음
  }
);

const { access_token: newAccessToken } = await refreshResponse.json();
// 새 Refresh Token도 자동으로 Cookie에 저장됨 ✅

// 로그아웃
await fetch("http://localhost:8000/api/web/auth/logout", {
  method: "POST",
  credentials: "include", // ⭐ Cookie 자동 삭제
  headers: { Authorization: `Bearer ${access_token}` },
});
```

### Axios

```javascript
import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true, // ⭐ Cookie 자동 전송/저장
});

// 로그인
const loginResponse = await apiClient.post("/api/web/auth/login", {
  loginId: "test",
  password: "123123",
});

const { access_token } = loginResponse.data;
// Refresh Token은 자동으로 Cookie에 저장됨 ✅

// 토큰 갱신
const refreshResponse = await apiClient.post("/api/web/auth/refresh");
// Cookie에서 자동으로 Refresh Token 읽음 ✅

// 로그아웃
await apiClient.post(
  "/api/web/auth/logout",
  {},
  {
    headers: { Authorization: `Bearer ${access_token}` },
  }
);
```

**핵심 포인트:**

- Fetch API: `credentials: "include"` 추가
- Axios: `withCredentials: true` 설정
- Refresh Token을 수동으로 관리할 필요 없음 ✅

---

## 🔍 Cookie 확인 방법

### 1. 브라우저 개발자 도구

**Chrome/Edge:**

1. F12 → Application 탭
2. Cookies → `http://localhost:8000`
3. `refresh_token` 확인

**확인 항목:**

- ✅ HttpOnly: `true`
- ✅ SameSite: `Lax`
- ✅ Path: `/` (모든 경로)
- ✅ Expires: 7일 후

### 2. curl 명령어

```bash
# 로그인 후 Cookie 저장
curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' \
  -c cookies.txt

# Cookie 내용 확인
cat cookies.txt | grep refresh_token
```

**출력 예시:**

```
#HttpOnly_localhost	FALSE	/	FALSE	1761891750	refresh_token	eyJhbGc...
```

---

## ⚠️ CORS 설정 (필수)

HttpOnly Cookie를 사용하려면 **CORS 설정이 필수**입니다.

### app.py 수정

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React 개발 서버
        "http://localhost:5173",  # Vite 개발 서버
        "https://yourdomain.com",  # 프로덕션 도메인
    ],
    allow_credentials=True,  # ⭐ Cookie 전송 허용 (필수!)
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**주의:**

- `allow_credentials=True` 필수
- `allow_origins=["*"]` 사용 불가 (특정 도메인만 허용)

---

## 🚀 프로덕션 배포 시 설정

### 1. HTTPS 강제 (`secure=True`)

```python
# src/api/web/auth/auth.py
import os

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

response.set_cookie(
    key="refresh_token",
    value=refresh_token_value,
    httponly=True,
    secure=IS_PRODUCTION,  # ⭐ 프로덕션에서는 True
    samesite="lax",
    max_age=7 * 24 * 60 * 60,
    path="/"  # 모든 경로에서 사용 가능
)
```

### 2. 환경 변수 설정

```env
# .env (프로덕션)
ENVIRONMENT=production
```

### 3. SameSite 설정 강화 (선택)

```python
samesite="strict"  # 더 강력한 CSRF 방지 (일부 시나리오에서 제한적)
```

---

## 🧪 테스트 시나리오

### 1. 로그인 → Cookie 저장 확인

```bash
curl -X POST 'http://localhost:8000/api/web/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"loginId":"test","password":"123123"}' \
  -c cookies.txt -v 2>&1 | grep "Set-Cookie"
```

**기대 결과:**

```
< Set-Cookie: refresh_token=eyJhbGc...; HttpOnly; Path=/; SameSite=Lax; Max-Age=604800
```

### 2. 토큰 갱신 → Cookie에서 자동 읽기

```bash
curl -X POST 'http://localhost:8000/api/web/auth/refresh' \
  -b cookies.txt -s | jq '.access_token'
```

**기대 결과:**

```json
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. 로그아웃 → Cookie 삭제 확인

```bash
curl -X POST 'http://localhost:8000/api/web/auth/logout' \
  -H 'Authorization: Bearer <access_token>' \
  -b cookies.txt -c cookies.txt -v 2>&1 | grep "Set-Cookie"
```

**기대 결과:**

```
< Set-Cookie: refresh_token=; Path=/; Max-Age=0
```

---

## 📊 보안 비교

| 항목                  | localStorage | HttpOnly Cookie    |
| --------------------- | ------------ | ------------------ |
| **JavaScript 접근**   | ✅ 가능      | ❌ 불가능          |
| **XSS 공격**          | ❌ 취약      | ✅ 안전            |
| **CSRF 공격**         | ✅ 안전      | ⚠️ SameSite로 방지 |
| **자동 전송**         | ❌ 수동      | ✅ 자동            |
| **CORS 설정**         | 불필요       | 필수               |
| **프론트엔드 복잡도** | 높음         | 낮음               |

---

## 💡 핵심 요약

### **프론트엔드 개발자가 알아야 할 것**

1. **`credentials: "include"` 추가** (Fetch API)
2. **`withCredentials: true` 설정** (Axios)
3. **Refresh Token을 직접 관리하지 않음** (자동 처리)
4. **Swagger UI에서는 Access Token만 사용** (Refresh Token은 Cookie로 자동 전송)

### **백엔드 개발자가 알아야 할 것**

1. **HttpOnly Cookie로 Refresh Token 저장**
2. **CORS 설정 필수** (`allow_credentials=True`)
3. **프로덕션에서 `secure=True` 설정**

### **Swagger UI 테스트 시 주의사항**

| 토큰 타입         | Swagger "Authorize" | 용도                   |
| ----------------- | ------------------- | ---------------------- |
| **Access Token**  | ✅ 입력 가능        | 인증이 필요한 API 호출 |
| **Refresh Token** | ❌ 입력 불가        | Cookie로 자동 전송     |

**Refresh Token을 Swagger에 입력하면:**

```json
{
  "detail": "유효하지 않은 토큰 타입입니다."
}
```

**이유:** Access Token은 `type: "access"`, Refresh Token은 `type: "refresh"`로 구분되며, Swagger Authorization은 Access Token만 허용합니다.

---

## 🔗 관련 문서

- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - 전체 보안 가이드
- [FRONTEND_TOKEN_GUIDE.md](./FRONTEND_TOKEN_GUIDE.md) - 프론트엔드 토큰 자동 갱신

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24  
**버전**: 1.0.0
