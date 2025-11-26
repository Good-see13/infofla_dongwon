#!/bin/bash

# Alembic 마이그레이션 헬퍼 스크립트
# alembic.ini가 어디 있든 상관없이 사용 가능

# alembic.ini 위치 설정
ALEMBIC_CONFIG="alembic.ini"  # 루트에 있는 경우
# ALEMBIC_CONFIG="alembic/alembic.ini"  # alembic 폴더에 있는 경우

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# .env 파일에서 USE_DATABASE 체크
if [ -f .env ]; then
    source .env
    if [ "$USE_DATABASE" != "true" ]; then
        print_error "Database is disabled (USE_DATABASE=$USE_DATABASE)"
        print_warning "Set USE_DATABASE=true in .env file to use database migrations"
        exit 1
    fi
else
    print_warning ".env file not found. Proceeding without checking USE_DATABASE..."
fi

case "$1" in
    create)
        if [ -z "$2" ]; then
            echo "사용법: ./db_migrate.sh create '마이그레이션 메시지'"
            exit 1
        fi
        print_info "마이그레이션 생성 중..."
        alembic -c $ALEMBIC_CONFIG revision --autogenerate -m "$2"
        print_success "마이그레이션 생성 완료"
        ;;
    
    up)
        print_info "마이그레이션 적용 중..."
        alembic -c $ALEMBIC_CONFIG upgrade head
        print_success "마이그레이션 적용 완료"
        ;;
    
    down)
        print_info "마이그레이션 롤백 중..."
        alembic -c $ALEMBIC_CONFIG downgrade -1
        print_success "마이그레이션 롤백 완료"
        ;;
    
    current)
        print_info "현재 마이그레이션 버전:"
        alembic -c $ALEMBIC_CONFIG current
        ;;
    
    history)
        print_info "마이그레이션 히스토리:"
        alembic -c $ALEMBIC_CONFIG history --verbose
        ;;
    
    *)
        echo "사용법:"
        echo "  ./db_migrate.sh create '메시지'  # 마이그레이션 생성"
        echo "  ./db_migrate.sh up               # 적용"
        echo "  ./db_migrate.sh down             # 롤백"
        echo "  ./db_migrate.sh current          # 현재 버전"
        echo "  ./db_migrate.sh history          # 히스토리"
        exit 1
        ;;
esac

