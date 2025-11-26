# 환경 설정 가이드

## 1. .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

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
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-this-in-production
```

⚠️ **중요**: 프로덕션 환경에서는 반드시 강력한 비밀번호와 SECRET_KEY를 사용하세요!

## 2. 패키지 설치

```bash
pip install -r requirements.txt
```

## 3. MariaDB 설정

MariaDB가 실행 중이고 다음 설정으로 접근 가능한지 확인하세요:

- Host: localhost
- Port: 3307
- Database: dongwon
- User: root
- Password: 12345

### Docker로 MariaDB 실행 (옵션)

```bash
docker run -d \
  --name mariadb-dongwon \
  -p 3307:3306 \
  -e MARIADB_ROOT_PASSWORD=12345 \
  -e MARIADB_DATABASE=dongwon \
  -e MARIADB_USER=test \
  -e MARIADB_PASSWORD=12345 \
  mariadb:latest
```

## 4. 서버 실행

```bash
python app.py
```

서버가 시작되면 데이터베이스 테이블이 자동으로 생성됩니다.

## 5. API 테스트

### Swagger UI 접속

```
http://localhost:8000/docs
```

### 사용 가능한 엔드포인트

#### Web API

- `POST /api/web/auth/register` - 회원가입
- `POST /api/web/auth/login` - 로그인
- `GET /api/web/auth/users/{username}` - 사용자 조회
- `GET /api/web/auth/health` - 헬스 체크

#### YOLO API

- `GET /` - 서비스 상태
- `GET /health` - 헬스 체크
- `POST /detect` - 단일 이미지 객체 탐지
- `POST /yolo/detect-multiple` - 다중 이미지 객체 탐지

### 예시: 회원가입

```bash
curl -X POST "http://localhost:8000/api/web/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "full_name": "테스트 유저"
  }'
```

### 예시: 로그인

```bash
curl -X POST "http://localhost:8000/api/web/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

## 추가 API 추가 방법

### 1. 새 모델 추가

```python
# src/common/mariadb/models/Product.py
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, DateTime
from src.common.mariadb.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    createAt = Column(DateTime, default=datetime.utcnow)
```

```python
# src/common/mariadb/models/__init__.py에 등록
from .User import User
from .Product import Product

__all__ = ["User", "Product"]
```

```bash
# DB에 반영
python db_push.py
```

### 2. 새 API 모듈 추가

기능별로 폴더를 만들어 관리합니다 (예: products):

```
src/api/web/products/
├── __init__.py
├── products.py
├── products_service.py
└── products_schemas.py
```

#### products.py

```python
from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/")
async def get_products():
    return {"products": []}
```

#### **init**.py

```python
from .products import router

__all__ = ["router"]
```

#### src/api/web/**init**.py에 등록

```python
from .auth import router as auth_router
from .products import router as products_router

web_router.include_router(auth_router)
web_router.include_router(products_router)
```

이렇게 하면 `/api/web/products/` 경로로 API가 생성됩니다.
