"""
더미 사용자 데이터 생성 스크립트
"""

import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from passlib.context import CryptContext
from dotenv import load_dotenv
import os

from src.common.mariadb.models import User

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL")

# 비동기 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_dummy_users():
    """더미 사용자 데이터 생성"""
    
    # 더미 사용자 데이터 (비밀번호는 모두 "password123")
    dummy_users = [
              {
            "loginId": "test",
            "password": "123123",
            "name": "슈퍼관리자",
            "email": "test@example.com",
            "description": "슈퍼 시스템 관리자"
        },
        {
            "loginId": "admin",
            "password": "password123",
            "name": "관리자",
            "email": "admin@example.com",
            "description": "시스템 관리자"
        },
        {
            "loginId": "testuser1",
            "password": "password123",
            "name": "홍길동",
            "email": "hong@example.com",
            "description": "테스트 사용자 1"
        },
        {
            "loginId": "testuser2",
            "password": "password123",
            "name": "김철수",
            "email": "kim@example.com",
            "description": "테스트 사용자 2"
        },
        {
            "loginId": "testuser3",
            "password": "password123",
            "name": "이영희",
            "email": "lee@example.com",
            "description": "테스트 사용자 3"
        },
        {
            "loginId": "testuser4",
            "password": "password123",
            "name": "박민수",
            "email": "park@example.com",
            "description": "테스트 사용자 4"
        },
        {
            "loginId": "testuser5",
            "password": "password123",
            "name": "최지원",
            "email": "choi@example.com",
            "description": "테스트 사용자 5"
        },
        {
            "loginId": "testuser6",
            "password": "password123",
            "name": "정수진",
            "email": "jung@example.com",
            "description": "테스트 사용자 6"
        },
        {
            "loginId": "testuser7",
            "password": "password123",
            "name": "강민호",
            "email": "kang@example.com",
            "description": "테스트 사용자 7"
        },
        {
            "loginId": "testuser8",
            "password": "password123",
            "name": "윤서연",
            "email": "yoon@example.com",
            "description": "테스트 사용자 8"
        },
        {
            "loginId": "testuser9",
            "password": "password123",
            "name": "임동현",
            "email": "lim@example.com",
            "description": "테스트 사용자 9"
        },
        {
            "loginId": "testuser10",
            "password": "password123",
            "name": "송하늘",
            "email": "song@example.com",
            "description": "테스트 사용자 10"
        },
        {
            "loginId": "manager1",
            "password": "password123",
            "name": "매니저1",
            "email": "manager1@example.com",
            "description": "부서 매니저"
        },
        {
            "loginId": "manager2",
            "password": "password123",
            "name": "매니저2",
            "email": "manager2@example.com",
            "description": "팀 매니저"
        },
        {
            "loginId": "developer1",
            "password": "password123",
            "name": "개발자1",
            "email": "dev1@example.com",
            "description": "백엔드 개발자"
        },
        {
            "loginId": "developer2",
            "password": "password123",
            "name": "개발자2",
            "email": "dev2@example.com",
            "description": "프론트엔드 개발자"
        },
    ]
    
    async with SessionLocal() as session:
        try:
            now = datetime.utcnow()
            created_count = 0
            skipped_count = 0
            
            for user_data in dummy_users:
                # 중복 체크
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(
                        (User.loginId == user_data["loginId"]) | 
                        (User.email == user_data["email"])
                    )
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    print(f"⏭️  건너뜀: {user_data['loginId']} (이미 존재)")
                    skipped_count += 1
                    continue
                
                # 비밀번호 해시
                hashed_password = pwd_context.hash(user_data["password"])
                
                # User 객체 생성
                user = User(
                    loginId=user_data["loginId"],
                    password=hashed_password,
                    name=user_data["name"],
                    email=user_data["email"],
                    description=user_data["description"],
                    pwCreatedAt=now
                )
                
                session.add(user)
                created_count += 1
                print(f"✅ 생성: {user_data['loginId']} - {user_data['name']} ({user_data['email']})")
            
            # 커밋
            await session.commit()
            
            print(f"\n{'='*60}")
            print(f"✅ 완료: {created_count}명 생성, {skipped_count}명 건너뜀")
            print(f"{'='*60}")
            print(f"\n📝 모든 사용자 비밀번호: password123")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 에러: {e}")
            raise


if __name__ == "__main__":
    print("🚀 더미 사용자 데이터 생성 시작...\n")
    asyncio.run(create_dummy_users())

