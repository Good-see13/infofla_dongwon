# Windows 환경 설정 가이드

Windows 환경에서 프로젝트를 설정하는 방법을 안내합니다.

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [MariaDB 설치](#mariadb-설치)
3. [Python 환경 설정](#python-환경-설정)
4. [프로젝트 설정](#프로젝트-설정)
5. [서버 실행](#서버-실행)
6. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 1. PowerShell 실행 정책 확인

PowerShell을 **관리자 권한**으로 실행 후:

```powershell
Get-ExecutionPolicy
```

만약 `Restricted`로 되어 있다면:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 필수 소프트웨어

- **Python 3.10.19** 이상
- **Git** (선택사항)
- **Docker Desktop** (Docker 설치 방식 선택 시)

---

## MariaDB 설치

### 방법 1: 자동 설치 스크립트 (권장) ⭐

#### 1단계: .env 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```bash
# MariaDB environment variables
MARIADB_ROOT_PASSWORD=12345
MARIADB_DATABASE=dongwon
MARIADB_USER=test
MARIADB_PASSWORD=12345
MARIADB_PORT=3307

# Database URL for SQLAlchemy
DATABASE_URL=mysql+aiomysql://root:12345@localhost:3307/dongwon

# Application settings
USE_DATABASE=true
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
UPLOAD_PATH=./uploads
LOG_RETENTION_DAYS=7
```

#### 2단계: 스크립트 실행

PowerShell에서 실행:

```powershell
powershell -ExecutionPolicy Bypass -File setup_mariadb_windows.ps1
```

**스크립트가 자동으로 수행하는 작업:**

- Docker 또는 로컬 MariaDB 확인
- MariaDB 설치 (선택한 방법에 따라)
- 데이터베이스 생성 (`dongwon`)
- 사용자 생성 및 권한 부여
- 연결 테스트

#### 3단계: 설치 옵션 선택

스크립트 실행 시 다음 옵션 중 선택:

1. **Docker로 MariaDB 설치 (권장)**

   - Docker Desktop이 설치되어 있어야 함
   - 가장 간편하고 깔끔한 방법
   - 포트 충돌 없음

2. **로컬에 MariaDB 설치**

   - 수동 설치 가이드 제공
   - Windows 서비스로 실행

3. **기존 MariaDB 사용**
   - 이미 설치된 MariaDB 사용
   - 데이터베이스만 생성

---

### 방법 2: Docker Desktop 사용

#### 1단계: Docker Desktop 설치

1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) 다운로드
2. 설치 후 재부팅
3. Docker Desktop 실행 확인

#### 2단계: MariaDB 컨테이너 실행

PowerShell에서:

```powershell
docker run -d `
  --name mariadb-dongwon `
  -p 3307:3306 `
  -e MARIADB_ROOT_PASSWORD=12345 `
  -e MARIADB_DATABASE=dongwon `
  -e MARIADB_USER=test `
  -e MARIADB_PASSWORD=12345 `
  mariadb:latest
```

#### 3단계: 연결 확인

```powershell
docker exec mariadb-dongwon mysql -u root -p12345 -e "SHOW DATABASES;"
```

#### Docker 관리 명령어

```powershell
# 시작
docker start mariadb-dongwon

# 중지
docker stop mariadb-dongwon

# 재시작
docker restart mariadb-dongwon

# 로그 확인
docker logs mariadb-dongwon

# 컨테이너 접속
docker exec -it mariadb-dongwon mysql -u root -p

# 삭제
docker rm -f mariadb-dongwon
```

---

### 방법 3: 로컬 설치

#### 1단계: MariaDB 다운로드

1. [MariaDB 공식 사이트](https://mariadb.org/download/)에서 다운로드
2. Windows용 MSI 설치 파일 선택
3. 설치 진행

#### 2단계: 설치 시 설정

- **Root Password**: `.env` 파일의 `MARIADB_ROOT_PASSWORD` 값 입력
- **Port**: `.env` 파일의 `MARIADB_PORT` 값 입력 (기본: 3307)
- **Character Set**: `utf8mb4` 선택

#### 3단계: 데이터베이스 생성

MySQL 클라이언트 실행:

```powershell
mysql -u root -p -P 3307
```

SQL 실행:

```sql
CREATE DATABASE dongwon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EXIT;
```

---

## Python 환경 설정

### 1. Python 설치 확인

```powershell
python --version
```

Python 3.10.19 이상이 필요합니다.

### 2. uv 설치 (권장)

```powershell
pip install uv
```

### 3. 가상환경 생성 및 활성화

#### uv 사용 (권장)

```powershell
# 1. 가상환경 생성
uv venv

# 2. 가상환경 활성화
.venv\Scripts\Activate.ps1

# 또는 한 줄로 (PowerShell 7+)
uv venv; .venv\Scripts\Activate.ps1
```

#### 기본 venv 사용

```powershell
# 1. 가상환경 생성
python -m venv .venv

# 2. 가상환경 활성화
.venv\Scripts\Activate.ps1
```

**가상환경 활성화 확인:**

```powershell
# 프롬프트 앞에 (.venv)가 표시되어야 함
(.venv) PS C:\Users\...\dongwon>
```

**가상환경 비활성화:**

```powershell
deactivate
```

### 4. 패키지 설치

**가상환경이 활성화된 상태에서:**

```powershell
# uv 사용 (권장)
uv pip install -r requirements.txt

# 또는 pip
pip install -r requirements.txt
```

**설치 확인:**

```powershell
# 설치된 패키지 목록 확인
pip list

# 주요 패키지 확인
python -c "import fastapi; print(fastapi.__version__)"
```

---

## 프로젝트 설정

### 1. 데이터베이스 테이블 생성

```powershell
uv run python db_push.py
```

**출력 예시:**

```
🚀 DB Push 시작...

📋 등록된 모델:
  - users
  - items
  - itemImages
  - detectionResults

📦 테이블 생성 중...

✅ DB Push 완료!
```

### 2. 더미 데이터 생성 (선택사항)

```powershell
uv run python create_dummy_users.py
```

### 3. 업로드 폴더 생성

```powershell
New-Item -ItemType Directory -Force -Path uploads
```

---

## 서버 실행

### 개발 서버

```powershell
uv run python app.py
```

또는

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 프로덕션 서버

```powershell
$env:ENVIRONMENT="production"
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 서버 접속

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 문제 해결

### 1. PowerShell 스크립트 실행 오류

#### 오류 1: 스크립트 실행 정책

**오류:**

```
setup_mariadb_windows.ps1 cannot be loaded because running scripts is disabled
```

**해결:**

```powershell
# 현재 사용자에 대해 스크립트 실행 허용
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

또는 일회성 실행:

```powershell
powershell -ExecutionPolicy Bypass -File setup_mariadb_windows.ps1
```

#### 오류 2: 가상환경 활성화 오류

**오류:**

```
.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system
```

**해결:**

```powershell
# 방법 1: 실행 정책 변경 (권장)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# 방법 2: cmd.exe 사용
.venv\Scripts\activate.bat

# 방법 3: 일회성 우회
PowerShell -ExecutionPolicy Bypass -Command ".venv\Scripts\Activate.ps1"
```

**실행 정책 확인:**

```powershell
Get-ExecutionPolicy -List
```

**출력 예시:**

```
Scope          ExecutionPolicy
-----          ---------------
MachinePolicy  Undefined
UserPolicy     Undefined
Process        Undefined
CurrentUser    RemoteSigned    ← 이렇게 되어야 함
LocalMachine   Undefined
```

---

### 2. Docker Desktop이 실행되지 않음

**증상:**

```
error during connect: This error may indicate that the docker daemon is not running
```

**해결:**

1. Docker Desktop 실행
2. 시스템 트레이에서 Docker 아이콘 확인
3. Docker가 완전히 시작될 때까지 대기 (1-2분)

---

### 3. 포트 충돌

**오류:**

```
Bind for 0.0.0.0:3307 failed: port is already allocated
```

**해결:**

포트 사용 확인:

```powershell
netstat -ano | findstr :3307
```

프로세스 종료:

```powershell
taskkill /PID <PID번호> /F
```

또는 `.env` 파일에서 다른 포트로 변경:

```bash
MARIADB_PORT=3308
DATABASE_URL=mysql+aiomysql://root:12345@localhost:3308/dongwon
```

---

### 4. MySQL 클라이언트를 찾을 수 없음

**오류:**

```
'mysql' is not recognized as an internal or external command
```

**해결:**

#### 옵션 1: Docker 사용

```powershell
docker exec -it mariadb-dongwon mysql -u root -p
```

#### 옵션 2: PATH 추가

1. MariaDB 설치 경로 확인 (예: `C:\Program Files\MariaDB 10.11\bin`)
2. 시스템 환경 변수에 추가:
   - `제어판` → `시스템` → `고급 시스템 설정` → `환경 변수`
   - `Path` 편집 → `새로 만들기` → MariaDB bin 경로 추가
3. PowerShell 재시작

---

### 5. 데이터베이스 연결 오류

**오류:**

```
RuntimeError: Database is not configured
```

**확인 사항:**

1. `.env` 파일 존재 확인
2. `USE_DATABASE=true` 설정 확인
3. `DATABASE_URL` 형식 확인:
   ```
   mysql+aiomysql://사용자:비밀번호@호스트:포트/데이터베이스명
   ```
4. MariaDB 실행 확인:

   ```powershell
   # Docker
   docker ps | findstr mariadb

   # 로컬
   Get-Service | findstr -i maria
   ```

---

### 6. 한글 깨짐 문제

**증상:** 데이터베이스에 한글이 깨져서 저장됨

**해결:**

데이터베이스 문자셋 확인:

```sql
SHOW VARIABLES LIKE 'character_set%';
```

문자셋 변경:

```sql
ALTER DATABASE dongwon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

### 7. 관리자 권한 필요

일부 작업은 관리자 권한이 필요할 수 있습니다.

**PowerShell을 관리자 권한으로 실행:**

1. 시작 메뉴에서 `PowerShell` 검색
2. 우클릭 → `관리자 권한으로 실행`

---

## 추가 리소스

### 관련 문서

- [ENV_SETUP_GUIDE.md](ENV_SETUP_GUIDE.md) - 환경 변수 설정
- [DB_SETUP_GUIDE.md](DB_SETUP_GUIDE.md) - 데이터베이스 상세 가이드
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) - 보안 설정
- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - 프로젝트 구조

### Docker Desktop 설정

**WSL 2 Backend 활성화 (권장):**

1. Docker Desktop 설정 열기
2. `General` → `Use the WSL 2 based engine` 체크
3. Docker Desktop 재시작

**리소스 제한 설정:**

1. `Settings` → `Resources`
2. CPU, Memory 할당량 조정
3. `Apply & Restart`

### Windows Terminal 사용 (권장)

PowerShell보다 더 나은 터미널 환경:

1. [Microsoft Store](https://aka.ms/terminal)에서 설치
2. 기본 프로필을 PowerShell로 설정
3. 색상 테마 및 폰트 커스터마이징

### 유용한 PowerShell 명령어

#### 경로 구분자 차이

```powershell
# Windows: 백슬래시 (\)
.venv\Scripts\Activate.ps1
cd C:\Users\username\project

# macOS/Linux: 슬래시 (/)
source .venv/bin/activate
cd /home/username/project
```

#### 환경 변수 설정

```powershell
# 임시 설정 (현재 세션만)
$env:ENVIRONMENT="production"
$env:DATABASE_URL="mysql+aiomysql://root:12345@localhost:3307/dongwon"

# 영구 설정 (사용자 레벨)
[System.Environment]::SetEnvironmentVariable("ENVIRONMENT", "production", "User")

# 확인
$env:ENVIRONMENT
Get-ChildItem Env:
```

#### 파일 및 폴더 관리

```powershell
# 폴더 생성
New-Item -ItemType Directory -Force -Path uploads

# 파일 내용 확인
Get-Content .env
cat .env  # 별칭

# 파일 찾기
Get-ChildItem -Recurse -Filter "*.py"

# 프로세스 확인
Get-Process python
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

#### 포트 및 네트워크

```powershell
# 포트 사용 확인
netstat -ano | findstr :8000
netstat -ano | findstr :3307

# 프로세스 종료
taskkill /PID <PID번호> /F

# 방화벽 규칙 추가 (관리자 권한 필요)
New-NetFirewallRule -DisplayName "FastAPI" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## 🎉 완료!

이제 Windows 환경에서 프로젝트를 실행할 준비가 완료되었습니다!

```powershell
# 서버 시작
uv run python app.py

# 브라우저에서 접속
start http://localhost:8000/docs
```

문제가 발생하면 [문제 해결](#문제-해결) 섹션을 참고하거나 이슈를 등록해주세요.
