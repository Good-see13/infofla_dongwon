# 🗄️ 데이터베이스 설정 가이드

새로운 환경에서 데이터베이스를 설정하는 방법입니다.

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [데이터베이스 생성](#데이터베이스-생성)
3. [테이블 생성 (자동)](#테이블-생성-자동)
4. [테이블 수정/추가](#테이블-수정추가)
5. [문제 해결](#문제-해결)

---

## 🔧 사전 요구사항

### 1. MariaDB 설치 확인

```bash
# Docker로 설치된 경우
docker ps | grep mariadb

# 직접 설치된 경우
mysql --version
```

### 2. `.env` 파일 설정

**방법 1: 템플릿 복사 (권장)**

```bash
# env.template을 복사하여 .env 파일 생성
cp env.template .env

# .env 파일을 편집하여 환경에 맞게 수정
vi .env  # 또는 원하는 에디터 사용
```

**방법 2: 직접 생성**

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력:

```env
# 데이터베이스 사용 여부
USE_DATABASE=true

# MariaDB 연결 정보
DATABASE_URL="mysql+aiomysql://root:12345@localhost:3307/dongwon"

# MariaDB 환경 변수
MARIADB_ROOT_PASSWORD=12345
MARIADB_DATABASE=dongwon
MARIADB_USER=test
MARIADB_PASSWORD=12345
MARIADB_PORT=3307

# JWT 설정
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# 파일 업로드 경로
UPLOAD_PATH=./uploads

# 로그 보관 기간 (일)
LOG_RETENTION_DAYS=30
```

**중요**: `.env` 파일은 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다.

---

## 🗃️ 데이터베이스 생성

### Docker 사용 시

```bash
# MariaDB 컨테이너 실행 (docker-compose.yml 사용)
docker-compose up -d db_dev

# 데이터베이스 생성 확인
docker exec -i db_dev mysql -u root -p12345 -e "SHOW DATABASES;"
```

### 직접 설치 시

```bash
# MariaDB 접속
mysql -u root -p

# 데이터베이스 생성
CREATE DATABASE dongwon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 사용자 생성 및 권한 부여
CREATE USER 'test'@'localhost' IDENTIFIED BY '12345';
GRANT ALL PRIVILEGES ON dongwon.* TO 'test'@'localhost';
FLUSH PRIVILEGES;
```

---

## 🚀 테이블 생성 (자동)

### 방법 1: `db_push.py` 사용 (권장)

**Prisma 스타일의 자동 테이블 생성/업데이트**

#### 1. 생성될 스키마 미리보기

```bash
uv run python db_push.py --show
```

#### 2. 테이블 생성/업데이트 (안전)

```bash
uv run python db_push.py
```

**동작 방식:**

- 존재하지 않는 테이블은 새로 생성
- 이미 존재하는 테이블은 건너뜀 (데이터 보존)
- 컬럼 추가는 자동으로 처리되지 않음 (수동 마이그레이션 필요)

#### 3. 테이블 전체 재생성 (위험! 데이터 삭제됨)

```bash
uv run python db_push.py --force
```

**경고**: `--force` 옵션은 모든 테이블을 삭제하고 재생성합니다. 프로덕션 환경에서는 절대 사용하지 마세요!

#### 4. 확인 없이 자동 실행

```bash
uv run python db_push.py --force --yes
```

---

## 🔄 테이블 수정/추가

### 워크플로우

1. **모델 파일 수정**

   ```bash
   # 예: 새 컬럼 추가
   src/common/mariadb/models/User.py
   ```

2. **변경사항 확인**

   ```bash
   uv run python db_push.py --show
   ```

3. **DB에 반영**
   ```bash
   uv run python db_push.py
   ```

### 예시: 새 모델 추가

#### 1. 모델 파일 생성

`src/common/mariadb/models/NewModel.py`:

```python
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from src.common.mariadb.base import Base

class NewModel(Base):
    __tablename__ = "new_table"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    createDate = Column(DateTime, server_default=func.now())
```

#### 2. `__init__.py`에 추가

`src/common/mariadb/models/__init__.py`:

```python
from .NewModel import NewModel

__all__ = [
    "User",
    "Item",
    "ItemImage",
    "InferResult",
    "NewModel",  # 추가
]
```

#### 3. `db_push.py`에 import 추가

```python
from src.common.mariadb.models import User, Item, ItemImage, InferResult, NewModel
```

#### 4. 테이블 생성

```bash
uv run python db_push.py
```

---

## 📊 현재 테이블 구조

### 1. `users` - 사용자 정보

```sql
- id: BIGINT (PK, AUTO_INCREMENT)
- loginId: VARCHAR(30) UNIQUE
- password: VARCHAR(128)
- name: VARCHAR(30)
- email: VARCHAR(255) UNIQUE
- description: TEXT
- createAt: DATETIME
- updatedAt: DATETIME
- lastLogout: DATETIME (nullable)
- pwCreatedAt: DATETIME (nullable)
- pwFailCount: INT
- isDeleteUser: BOOLEAN
- deleteAt: DATETIME (nullable)
```

### 2. `items` - 품목 정보

```sql
- id: BIGINT (PK, AUTO_INCREMENT)
- itemName: VARCHAR(200)
- createDate: DATETIME
- updatedDate: DATETIME
```

### 3. `itemImages` - 품목 이미지

```sql
- id: BIGINT (PK)
- itemId: BIGINT (PK, FK → items.id, CASCADE DELETE)
- originalImageName: VARCHAR(100)
- newImageName: VARCHAR(100)
- imagePath: VARCHAR(200)
- createDate: DATETIME
```

### 4. `detectionResults` - 탐지 결과

```sql
- id: BIGINT (PK, AUTO_INCREMENT)
- itemId: BIGINT (FK → items.id, CASCADE DELETE)
- imageName: VARCHAR(100)
- imagePath: VARCHAR(200)
- status: ENUM('TRUE', 'FALSE')
- createDate: DATETIME
```

---

## 🛠️ 문제 해결

### 1. "Database is disabled" 오류

```bash
# .env 파일에서 확인
USE_DATABASE=true
```

### 2. "Database engine is not configured" 오류

```bash
# DATABASE_URL 형식 확인
DATABASE_URL="mysql+aiomysql://사용자:비밀번호@호스트:포트/데이터베이스명"
```

### 3. 연결 오류 (2003, "Can't connect to MySQL server")

```bash
# MariaDB 실행 확인
docker ps | grep mariadb

# 포트 확인
docker port db_dev

# 재시작
docker-compose restart db_dev
```

### 4. 테이블이 생성되지 않음

```bash
# 모델이 제대로 import 되었는지 확인
uv run python db_push.py --show

# db_push.py에 모델 import 추가
from src.common.mariadb.models import User, Item, ItemImage, InferResult
```

### 5. 컬럼 추가가 반영되지 않음

**SQLAlchemy의 `create_all()`은 기존 테이블을 수정하지 않습니다.**

**해결 방법:**

1. **수동 ALTER TABLE** (권장 - 데이터 보존)

   ```sql
   ALTER TABLE users ADD COLUMN new_column VARCHAR(100);
   ```

2. **테이블 재생성** (데이터 삭제됨!)

   ```bash
   uv run python db_push.py --force
   ```

3. **Alembic 마이그레이션 사용** (프로덕션 권장)
   ```bash
   ./db_migrate.sh
   ```

---

## 📝 주의사항

### ⚠️ 프로덕션 환경

- `--force` 옵션 절대 사용 금지
- 백업 후 작업
- Alembic 마이그레이션 사용 권장

### ✅ 개발 환경

- `--force` 옵션으로 빠른 재생성 가능
- 더미 데이터는 `create_dummy_users.py` 등으로 재생성

### 🔐 보안

- `.env` 파일은 절대 Git에 커밋하지 않기
- 프로덕션 환경에서는 강력한 비밀번호 사용
- 데이터베이스 사용자는 최소 권한 원칙 적용

---

## 🎯 빠른 시작 (새 환경)

```bash
# 1. 저장소 클론
git clone <repository-url>
cd dongwon

# 2. .env 파일 생성
cp env.template .env
# .env 파일을 편집하여 환경에 맞게 수정

# 3. MariaDB 시작 (Docker)
docker-compose up -d db_dev

# 4. 데이터베이스 생성 확인
docker exec -i db_dev mysql -u root -p12345 -e "SHOW DATABASES;"

# 5. 테이블 생성 (자동)
uv run python db_push.py

# 6. 더미 데이터 생성 (선택)
uv run python create_dummy_users.py

# 7. 서버 실행
uv run python app.py
```

---

## 📚 관련 문서

- [Alembic 마이그레이션 가이드](./guide/DB_MIGRATION_GUIDE.md)
- [환경 변수 설정 가이드](./guide/ENV_SETUP_GUIDE.md)
- [API 문서](./src/api/web/README.md)

---

**작성일**: 2025-10-24  
**최종 수정**: 2025-10-24
