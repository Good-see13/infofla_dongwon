# 데이터베이스 마이그레이션 가이드

## 방법 1: 자동 테이블 생성 (개발 환경용) ⚡

현재 `app.py`가 시작될 때 **자동으로** 테이블이 생성됩니다.

```python
# app.py의 startup_event에서 자동 실행
await init_db()  # 테이블 자동 생성
```

### 장점

- 간단하고 빠름
- 설정 불필요
- 개발 환경에 적합

### 단점

- 마이그레이션 이력 없음
- 프로덕션 환경에 부적합
- 스키마 변경 추적 불가

---

## 방법 2: Alembic 마이그레이션 (프로덕션 권장) 🚀

**Alembic**을 사용하면 데이터베이스 변경 이력을 관리하고 버전 제어할 수 있습니다.

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 초기 마이그레이션 생성

```bash
# 방법 A: Alembic 직접 사용
alembic revision --autogenerate -m "Initial migration"

# 방법 B: 헬퍼 스크립트 사용 (더 간단!)
python migrate.py create "Initial migration"
```

이 명령은 현재 모델을 기반으로 마이그레이션 파일을 자동 생성합니다.

### 3. 마이그레이션 적용 (테이블 생성)

```bash
# 방법 A: Alembic 직접 사용
alembic upgrade head

# 방법 B: 헬퍼 스크립트 사용
python migrate.py up
```

### 4. 모델 변경 시 마이그레이션 생성

예를 들어, `User` 모델에 `phone` 필드를 추가했다면:

```python
# src/api/web/models.py
class User(Base):
    # ... 기존 필드들
    phone = Column(String(20), nullable=True)  # 새 필드
```

마이그레이션 생성:

```bash
python migrate.py create "Add phone field to users"
```

적용:

```bash
python migrate.py up
```

### 5. 마이그레이션 되돌리기

```bash
python migrate.py down
```

### 6. 현재 마이그레이션 상태 확인

```bash
# 현재 버전
python migrate.py current

# 전체 이력
python migrate.py history
```

---

## Alembic 명령어 치트시트

### 헬퍼 스크립트 사용 (권장)

```bash
# 마이그레이션 생성 (자동 감지)
python migrate.py create "설명"

# 최신 버전으로 업그레이드
python migrate.py up

# 한 단계 되돌리기
python migrate.py down

# 현재 버전 확인
python migrate.py current

# 마이그레이션 이력
python migrate.py history
```

### Alembic 직접 사용

```bash
# 자동 마이그레이션 생성
alembic revision --autogenerate -m "메시지"

# 빈 마이그레이션 생성 (수동 작성)
alembic revision -m "메시지"

# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade [revision_id]

# 한 단계 다운그레이드
alembic downgrade -1

# 특정 버전으로 다운그레이드
alembic downgrade [revision_id]

# 현재 버전 확인
alembic current

# 마이그레이션 이력
alembic history

# 마이그레이션 이력 (상세)
alembic history --verbose
```

---

## 실전 워크플로우

### 1. 처음 프로젝트 시작 시

```bash
# 1. MariaDB 실행
docker run -d --name mariadb-dongwon -p 3307:3306 \
  -e MARIADB_ROOT_PASSWORD=12345 \
  -e MARIADB_DATABASE=dongwon \
  mariadb:latest

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 초기 마이그레이션 생성
python migrate.py create "Initial migration"

# 4. 마이그레이션 적용 (테이블 생성!)
python migrate.py up

# 5. 서버 시작
python app.py
```

### 2. 모델 변경 시

```bash
# 1. models.py 수정
# src/common/mariadb/models/User.py에서 User 모델 수정

# 2. 마이그레이션 생성
python migrate.py create "Add new fields to user"

# 3. 생성된 마이그레이션 파일 확인
# alembic/versions/xxx_add_new_fields_to_user.py

# 4. 마이그레이션 적용
python migrate.py up
```

### 3. 새 모델 추가 시

```python
# src/common/mariadb/models/Product.py 생성
from sqlalchemy import Column, BigInteger, String, Integer
from src.common.mariadb.base import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100))
    price = Column(Integer)
```

```python
# src/common/mariadb/models/__init__.py에 등록
from .User import User
from .Product import Product

__all__ = ["User", "Product"]
```

```bash
# DB에 반영 (Prisma 스타일)
python db_push.py

# 또는 Alembic 마이그레이션 (프로덕션)
python migrate.py create "Add product model"
python migrate.py up
```

---

## app.py 수정 (선택사항)

**방법 1 (현재)**: 서버 시작 시 자동 테이블 생성

```python
@app.on_event("startup")
async def startup_event():
    await init_db()  # 자동 테이블 생성
```

**방법 2 (Alembic 전용)**: 자동 생성 비활성화

```python
@app.on_event("startup")
async def startup_event():
    # await init_db()  # 주석 처리
    # Alembic으로만 테이블 관리
```

---

## 주의사항

1. **개발 환경**: 자동 테이블 생성 사용 OK
2. **프로덕션 환경**: 반드시 Alembic 사용
3. **마이그레이션 파일**: Git에 커밋
4. **데이터베이스 백업**: 프로덕션 마이그레이션 전에 백업 필수
5. **팀 작업**: 마이그레이션 순서 중요 (충돌 주의)

---

## 트러블슈팅

### 마이그레이션이 자동 감지되지 않을 때

`src/common/mariadb/models/__init__.py`에서 모든 모델을 등록했는지 확인:

```python
from .User import User
from .Product import Product
from .Order import Order

__all__ = ["User", "Product", "Order"]
```

### 마이그레이션 충돌

```bash
# 현재 상태 확인
alembic current

# 이력 확인
alembic history

# 특정 버전으로 이동
alembic upgrade [revision_id]
```

### 데이터베이스 초기화 (개발 환경만!)

```bash
# 모든 테이블 삭제 후 재생성
alembic downgrade base
alembic upgrade head
```

---

## 참고 자료

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
