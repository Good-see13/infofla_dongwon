#!/usr/bin/env python3
"""
Prisma 스타일 DB Push 스크립트

사용법:
    python db_push.py              # 모든 테이블 생성/업데이트
    python db_push.py --force      # 모든 테이블 DROP 후 재생성 (주의!)
    python db_push.py --show       # 실행할 SQL만 출력 (실제 적용 X)

워크플로우:
    1. src/common/mariadb/models/에서 모델 정의/수정
    2. python db_push.py 실행
    3. DB에 자동 반영!
"""

import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.schema import CreateTable
from dotenv import load_dotenv

# .env 로드
load_dotenv()

from src.common.mariadb.database import engine, USE_DATABASE
from src.common.mariadb.base import Base
# 모든 모델 import (Base.metadata에 등록하기 위함)
from src.common.mariadb.models import User, Item, ItemImage, DetectionResult


async def show_schema():
    """생성될 스키마 출력"""
    print("\n=== 생성될 테이블 스키마 ===\n")
    for table in Base.metadata.sorted_tables:
        create_sql = str(CreateTable(table).compile(engine.sync_engine))
        print(f"-- {table.name} 테이블")
        print(f"{create_sql};\n")


async def drop_all_tables(skip_confirm: bool = False):
    """모든 테이블 삭제 (위험!)"""
    print("\n⚠️  경고: 모든 테이블을 삭제합니다! 데이터가 모두 사라집니다!")
    
    if not skip_confirm:
        confirm = input("정말 계속하시겠습니까? (yes 입력): ")
        
        if confirm.lower() != "yes":
            print("취소되었습니다.")
            return False
    else:
        print("자동 확인 모드: 테이블 삭제를 진행합니다...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("✅ 모든 테이블이 삭제되었습니다.")
    return True


async def push_to_db(force: bool = False, skip_confirm: bool = False):
    """
    모델을 DB에 Push (Prisma db push 스타일)
    
    Args:
        force: True면 기존 테이블 삭제 후 재생성
        skip_confirm: True면 확인 없이 자동 진행
    """
    print("\n🚀 DB Push 시작...\n")
    
    # 모든 모델 로드 확인
    print("📋 등록된 모델:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")
    
    if not Base.metadata.sorted_tables:
        print("❌ 등록된 모델이 없습니다!")
        return
    
    try:
        if force:
            dropped = await drop_all_tables(skip_confirm=skip_confirm)
            if not dropped:
                return
        
        # 테이블 생성/업데이트
        print("\n📦 테이블 생성 중...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 생성된 테이블 확인
        print("\n✅ DB Push 완료!\n")
        print("생성된 테이블:")
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            for table in tables:
                table_name = table[0]
                
                # 테이블 정보 조회
                result = await conn.execute(text(f"DESCRIBE {table_name}"))
                columns = result.fetchall()
                
                print(f"\n  📄 {table_name}:")
                for col in columns:
                    field, type_, null, key, default, extra = col
                    nullable = "NULL" if null == "YES" else "NOT NULL"
                    key_str = f" [{key}]" if key else ""
                    print(f"     - {field}: {type_} {nullable}{key_str}")
        
        print("\n🎉 완료!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise


async def main():
    """메인 실행 함수"""
    # 데이터베이스 사용 여부 확인
    if not USE_DATABASE:
        print("\n❌ Database is disabled (USE_DATABASE=false)")
        print("Set USE_DATABASE=true in .env file to use database features")
        return
    
    if not engine:
        print("\n❌ Database engine is not configured")
        print("Please check your DATABASE_URL in .env file")
        return
    
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    if "--show" in args:
        await show_schema()
        return
    
    force = "--force" in args
    skip_confirm = "--yes" in args or "-y" in args
    
    if force:
        print("\n⚠️  --force 모드: 기존 테이블을 모두 삭제하고 재생성합니다!")
    
    await push_to_db(force=force, skip_confirm=skip_confirm)


if __name__ == "__main__":
    asyncio.run(main())

