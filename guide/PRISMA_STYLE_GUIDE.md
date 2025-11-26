# Prisma 스타일 워크플로우 가이드

이 프로젝트는 Prisma와 유사한 워크플로우로 데이터베이스를 관리합니다.

> **📚 자세한 내용은 [DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)를 참고하세요.**

---

## 🚀 빠른 시작

### 1. 모델 정의

`src/common/mariadb/models/` 폴더에서 모델을 정의하세요:

```python
# src/common/mariadb/models/User.py
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean
from src.common.mariadb.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    loginId = Column(String(30), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    name = Column(String(30), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
```

```python
# src/common/mariadb/models/__init__.py에 등록
from .User import User

__all__ = ["User"]
```

### 2. DB에 Push

```bash
uv run python db_push.py
```

**끝!** 테이블이 자동으로 생성됩니다! 🎉

---

## 📋 Prisma vs SQLAlchemy 비교

| Prisma               | SQLAlchemy (이 프로젝트)         |
| -------------------- | -------------------------------- |
| `schema.prisma`      | `src/common/mariadb/models/*.py` |
| `prisma db push`     | `uv run python db_push.py`       |
| `@id`                | `primary_key=True`               |
| `@unique`            | `unique=True`                    |
| `@default(now())`    | `default=datetime.utcnow`        |
| `@updatedAt`         | `onupdate=datetime.utcnow`       |
| `String?` (optional) | `nullable=True`                  |
| `BigInt`             | `BigInteger`                     |
| `Boolean`            | `Boolean`                        |

---

## 🛠️ db_push.py 명령어

```bash
# 테이블 생성/업데이트
uv run python db_push.py

# 스키마만 확인 (실제 적용 X)
uv run python db_push.py --show

# 모든 테이블 삭제 후 재생성 (주의!)
uv run python db_push.py --force

# 도움말
uv run python db_push.py --help
```

---

## 📝 모델 정의 가이드

### 기본 타입

```python
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Boolean, Float

class Example(Base):
    __tablename__ = "examples"

    # 숫자
    id = Column(BigInteger, primary_key=True)  # Prisma: BigInt @id
    count = Column(Integer, default=0)         # Prisma: Int @default(0)
    price = Column(Float)                      # Prisma: Float

    # 문자열
    name = Column(String(100))                 # Prisma: String @db.VarChar(100)
    description = Column(Text)                 # Prisma: String (긴 텍스트)

    # 불리언
    is_active = Column(Boolean, default=True)  # Prisma: Boolean @default(true)

    # 날짜/시간
    created = Column(DateTime, default=datetime.utcnow)  # Prisma: DateTime @default(now())
    updated = Column(DateTime, onupdate=datetime.utcnow) # Prisma: DateTime @updatedAt
```

### 제약 조건

```python
class User(Base):
    __tablename__ = "users"

    # Primary Key
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Unique
    email = Column(String(255), unique=True)

    # Not Null
    name = Column(String(30), nullable=False)

    # Nullable (Optional)
    phone = Column(String(20), nullable=True)

    # Index
    loginId = Column(String(30), index=True, unique=True)

    # Default
    is_active = Column(Boolean, default=True)

    # Comment (문서화)
    name = Column(String(30), comment="사용자 이름")
```

### 관계 설정 (Foreign Key)

```python
from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

class Order(Base):
    __tablename__ = "orders"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'))

    # Relationship
    user = relationship("User", back_populates="orders")
```

---

## 🚨 주의사항

### ✅ 개발 환경

- `uv run python db_push.py` 사용 OK
- `--force` 사용 OK (데이터 삭제 감수)

### ⚠️ 프로덕션 환경

- **절대** `--force` 사용 금지!
- Alembic 마이그레이션 사용 권장
- 데이터 백업 필수

### 📌 모델 변경 시 주의

- **필드 삭제**: 데이터 손실 위험
- **NOT NULL 추가**: 기존 NULL 데이터 있으면 오류
- **타입 변경**: 데이터 호환성 확인 필요

---

## 📚 관련 문서

- **[DB_SETUP_GUIDE.md](./DB_SETUP_GUIDE.md)** - 완전한 데이터베이스 설정 가이드
- **[MARIADB_SETUP_GUIDE.md](./MARIADB_SETUP_GUIDE.md)** - MariaDB 설치 가이드
- **[DB_MIGRATION_GUIDE.md](./DB_MIGRATION_GUIDE.md)** - Alembic 마이그레이션 가이드
- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

---

Happy Coding! 🚀
