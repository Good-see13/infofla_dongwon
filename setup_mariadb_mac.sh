#!/bin/bash

# MariaDB 자동 설치 및 설정 스크립트 (macOS용)
# MariaDB 10.11 버전
# Docker 또는 로컬 설치 지원

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 메시지 출력
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 함수: .env 파일에서 값 읽기
get_env_value() {
    local key=$1
    local value=$(grep "^${key}=" .env 2>/dev/null | cut -d '=' -f 2- | tr -d '"' | tr -d "'")
    echo "$value"
}

# .env 파일 확인
if [ ! -f ".env" ]; then
    print_error ".env 파일이 없습니다!"
    print_info ".env 파일을 먼저 생성해주세요."
    exit 1
fi

# .env에서 환경변수 로드
print_info ".env 파일에서 설정 로드 중..."
MARIADB_ROOT_PASSWORD=$(get_env_value "MARIADB_ROOT_PASSWORD")
MARIADB_DATABASE=$(get_env_value "MARIADB_DATABASE")
MARIADB_USER=$(get_env_value "MARIADB_USER")
MARIADB_PASSWORD=$(get_env_value "MARIADB_PASSWORD")
MARIADB_PORT=$(get_env_value "MARIADB_PORT")

# 환경변수 검증
if [ -z "$MARIADB_ROOT_PASSWORD" ] || [ -z "$MARIADB_DATABASE" ]; then
    print_error ".env 파일에 필수 값이 없습니다!"
    print_info "MARIADB_ROOT_PASSWORD, MARIADB_DATABASE 등을 확인해주세요."
    exit 1
fi

print_success "설정 로드 완료"
echo "  - Database: $MARIADB_DATABASE"
echo "  - User: $MARIADB_USER"
echo "  - Port: $MARIADB_PORT"

# 변수 초기화
MARIADB_INSTALLED=false
MARIADB_TYPE=""  # "docker", "local", "none"

# 1. Docker 컨테이너 확인
print_info "Docker MariaDB 컨테이너 확인 중..."
if command -v docker &> /dev/null; then
    # Docker가 설치되어 있는지 확인
    if docker ps &> /dev/null 2>&1; then
        # MariaDB 컨테이너가 실행 중인지 확인
        if docker ps --format '{{.Names}}' | grep -q mariadb; then
            CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep mariadb | head -1)
            print_success "Docker MariaDB 컨테이너 발견: $CONTAINER_NAME"
            
            # 컨테이너 포트 확인
            CONTAINER_PORT=$(docker port $CONTAINER_NAME | grep 3306 | cut -d ':' -f 2)
            print_info "Docker MariaDB 포트: $CONTAINER_PORT"
            
            # 연결 테스트
            if docker exec $CONTAINER_NAME mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null; then
                print_success "Docker MariaDB 연결 성공!"
                MARIADB_INSTALLED=true
                MARIADB_TYPE="docker"
            else
                print_warning "Docker MariaDB가 있지만 비밀번호가 다릅니다."
            fi
        else
            print_info "Docker는 있지만 MariaDB 컨테이너는 없습니다."
        fi
    else
        print_info "Docker는 설치되어 있지만 실행 중이 아닙니다."
    fi
else
    print_info "Docker가 설치되어 있지 않습니다."
fi

# 2. 로컬 MariaDB/MySQL 확인 (통신으로 확인)
if [ "$MARIADB_INSTALLED" = false ]; then
    print_info "로컬 MariaDB/MySQL 연결 확인 중..."
    
    # mysql 명령어가 있는지 확인
    if command -v mysql &> /dev/null; then
        # 포트로 연결 시도
        if mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
            print_success "로컬 MariaDB 연결 성공! (포트: $MARIADB_PORT)"
            MARIADB_INSTALLED=true
            MARIADB_TYPE="local"
            
            # 버전 확인
            VERSION=$(mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT VERSION();" -sN 2>/dev/null)
            print_info "MariaDB 버전: $VERSION"
        # 기본 포트(3306)로도 시도
        elif mysql -h localhost -P 3306 -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
            print_success "로컬 MariaDB 연결 성공! (포트: 3306)"
            print_warning "하지만 .env의 포트($MARIADB_PORT)와 다릅니다."
            MARIADB_INSTALLED=true
            MARIADB_TYPE="local"
        # 비밀번호 없이 시도
        elif mysql -h localhost -P "$MARIADB_PORT" -u root -e "SELECT 1;" &> /dev/null 2>&1; then
            print_success "로컬 MariaDB 발견 (비밀번호 미설정)"
            MARIADB_INSTALLED=true
            MARIADB_TYPE="local"
        else
            print_info "로컬 MariaDB에 연결할 수 없습니다."
        fi
    else
        print_info "mysql 명령어가 없습니다."
    fi
fi

# 3. MariaDB가 없으면 설치 선택
if [ "$MARIADB_INSTALLED" = false ]; then
    print_warning "MariaDB가 설치되어 있지 않거나 연결할 수 없습니다."
    echo ""
    echo "설치 방법을 선택하세요:"
    echo "  1) Docker로 설치 (권장)"
    echo "  2) Homebrew로 로컬 설치"
    echo "  3) 설치 건너뛰기"
    echo ""
    read -p "선택 (1-3): " INSTALL_CHOICE
    
    case $INSTALL_CHOICE in
        1)
            # Docker 설치
            print_info "Docker로 MariaDB 설치 중..."
            
            if ! command -v docker &> /dev/null; then
                print_error "Docker가 설치되어 있지 않습니다!"
                print_info "Docker Desktop을 먼저 설치해주세요: https://www.docker.com/products/docker-desktop"
                exit 1
            fi
            
            # 기존 컨테이너가 있는지 확인 (중지된 상태)
            if docker ps -a --format '{{.Names}}' | grep -q "^mariadb-dongwon$"; then
                print_warning "mariadb-dongwon 컨테이너가 이미 존재합니다."
                read -p "기존 컨테이너를 삭제하고 새로 생성하시겠습니까? (y/n): " DELETE_CHOICE
                if [ "$DELETE_CHOICE" = "y" ] || [ "$DELETE_CHOICE" = "Y" ]; then
                    print_info "기존 컨테이너 삭제 중..."
                    docker rm -f mariadb-dongwon &> /dev/null || true
                else
                    print_info "기존 컨테이너를 시작합니다..."
                    docker start mariadb-dongwon
                    sleep 5
                    MARIADB_INSTALLED=true
                    MARIADB_TYPE="docker"
                    # 다음 설정 단계로 진행
                fi
            fi
            
            # 새 컨테이너 생성 (기존 컨테이너가 없거나 삭제한 경우)
            if [ "$MARIADB_INSTALLED" = false ]; then
                print_info "MariaDB Docker 컨테이너 생성 중..."
                
                # 사용자 설정이 있는 경우와 없는 경우 분리
                if [ -n "$MARIADB_USER" ] && [ "$MARIADB_USER" != "root" ]; then
                    docker run -d \
                        --name mariadb-dongwon \
                        -p $MARIADB_PORT:3306 \
                        -e MARIADB_ROOT_PASSWORD=$MARIADB_ROOT_PASSWORD \
                        -e MARIADB_DATABASE=$MARIADB_DATABASE \
                        -e MARIADB_USER=$MARIADB_USER \
                        -e MARIADB_PASSWORD=$MARIADB_PASSWORD \
                        -v mariadb-dongwon-data:/var/lib/mysql \
                        mariadb:10.11
                else
                    docker run -d \
                        --name mariadb-dongwon \
                        -p $MARIADB_PORT:3306 \
                        -e MARIADB_ROOT_PASSWORD=$MARIADB_ROOT_PASSWORD \
                        -e MARIADB_DATABASE=$MARIADB_DATABASE \
                        -v mariadb-dongwon-data:/var/lib/mysql \
                        mariadb:10.11
                fi
                
                print_info "컨테이너 시작 대기 중... (15초)"
                sleep 15
                
                # 연결 확인 (재시도 로직 추가)
                MAX_RETRIES=3
                RETRY_COUNT=0
                while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
                    if docker exec mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
                        print_success "Docker MariaDB 설치 및 시작 완료!"
                        MARIADB_INSTALLED=true
                        MARIADB_TYPE="docker"
                        break
                    else
                        RETRY_COUNT=$((RETRY_COUNT + 1))
                        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                            print_info "연결 재시도 중... ($RETRY_COUNT/$MAX_RETRIES)"
                            sleep 5
                        fi
                    fi
                done
                
                if [ "$MARIADB_INSTALLED" = false ]; then
                    print_error "Docker MariaDB 시작 실패"
                    print_info "로그 확인: docker logs mariadb-dongwon"
                    exit 1
                fi
            fi
            ;;
            
        2)
            # Homebrew 설치
            print_info "Homebrew로 MariaDB 설치 중..."
            
            # Homebrew 확인
            if ! command -v brew &> /dev/null; then
                print_warning "Homebrew가 설치되어 있지 않습니다."
                print_info "Homebrew 설치 중... (시간이 걸릴 수 있습니다)"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                
                # Apple Silicon Mac의 경우 PATH 추가
                if [[ $(uname -m) == 'arm64' ]]; then
                    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                fi
            fi
            
            # MariaDB 설치
            print_info "MariaDB 10.11 설치 중... (시간이 걸릴 수 있습니다)"
            brew install mariadb@10.11
            
            # PATH에 추가
            if [[ $(uname -m) == 'arm64' ]]; then
                echo 'export PATH="/opt/homebrew/opt/mariadb@10.11/bin:$PATH"' >> ~/.zshrc
                export PATH="/opt/homebrew/opt/mariadb@10.11/bin:$PATH"
            else
                echo 'export PATH="/usr/local/opt/mariadb@10.11/bin:$PATH"' >> ~/.zshrc
                export PATH="/usr/local/opt/mariadb@10.11/bin:$PATH"
            fi
            
            # 서비스 시작
            brew services start mariadb@10.11
            print_info "MariaDB 서비스 시작 대기 중... (5초)"
            sleep 5
            
            # MariaDB 보안 설정 (unix_socket 플러그인 비활성화)
            print_info "MariaDB 초기 보안 설정 중..."
            if mysql -u root -e "SELECT 1;" &> /dev/null 2>&1; then
                mysql -u root <<EOF
USE mysql;
UPDATE user SET plugin='' WHERE User='root';
FLUSH PRIVILEGES;
EOF
                print_success "보안 설정 완료"
            fi
            
            print_success "MariaDB 설치 완료"
            MARIADB_INSTALLED=true
            MARIADB_TYPE="local"
            ;;
            
        3)
            print_info "설치를 건너뜁니다."
            exit 0
            ;;
            
        *)
            print_error "잘못된 선택입니다."
            exit 1
            ;;
    esac
fi

# 4. 데이터베이스 설정
if [ "$MARIADB_INSTALLED" = true ]; then
    print_info "데이터베이스 설정 중..."
    
    if [ "$MARIADB_TYPE" = "docker" ]; then
        # Docker의 경우
        CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep mariadb | head -1)
        
        # Root 비밀번호 확인
        print_info "Root 비밀번호 확인 중..."
        if docker exec $CONTAINER_NAME mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
            print_success "Root 비밀번호 확인 완료"
        else
            print_warning "Root 비밀번호가 일치하지 않습니다. 설정 시도 중..."
            # 비밀번호 없이 시도 (초기 상태)
            if docker exec $CONTAINER_NAME mysql -u root -e "SELECT 1;" &> /dev/null 2>&1; then
                docker exec $CONTAINER_NAME mysql -u root -e "ALTER USER 'root'@'%' IDENTIFIED BY '$MARIADB_ROOT_PASSWORD'; ALTER USER 'root'@'localhost' IDENTIFIED BY '$MARIADB_ROOT_PASSWORD'; FLUSH PRIVILEGES;" 2>/dev/null || true
                print_success "Root 비밀번호 설정 완료"
            else
                print_error "Root 계정에 접근할 수 없습니다."
                print_info "컨테이너를 재생성하거나 수동으로 비밀번호를 설정해주세요."
            fi
        fi
        
        # 데이터베이스 생성
        print_info "데이터베이스 '$MARIADB_DATABASE' 생성 중..."
        if docker exec $CONTAINER_NAME mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$MARIADB_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" &> /dev/null 2>&1; then
            print_success "데이터베이스 생성 완료"
        else
            print_error "데이터베이스 생성 실패"
        fi
        
        # 사용자 생성 (root가 아닌 경우)
        if [ "$MARIADB_USER" != "root" ] && [ -n "$MARIADB_USER" ]; then
            print_info "사용자 '$MARIADB_USER' 생성 중..."
            docker exec $CONTAINER_NAME mysql -u root -p"$MARIADB_ROOT_PASSWORD" <<EOF
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$MARIADB_DATABASE\`.* TO '$MARIADB_USER'@'%';
FLUSH PRIVILEGES;
EOF
            print_success "사용자 생성 완료"
        fi
        
        # 연결 테스트
        if docker exec $CONTAINER_NAME mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "USE $MARIADB_DATABASE; SELECT 1;" &> /dev/null 2>&1; then
            print_success "Docker MariaDB 설정 완료!"
        else
            print_warning "데이터베이스는 생성되었지만 연결 테스트에 실패했습니다."
        fi
        
    else
        # 로컬 설치의 경우
        
        # Root 비밀번호 설정
        print_info "Root 비밀번호 설정 중..."
        
        # 먼저 비밀번호 없이 접속 시도
        if mysql -h localhost -P "$MARIADB_PORT" -u root -e "SELECT 1;" &> /dev/null 2>&1; then
            print_info "비밀번호 없는 root 계정 발견, 비밀번호 설정 중..."
            mysql -h localhost -P "$MARIADB_PORT" -u root <<EOF
SET PASSWORD FOR 'root'@'localhost' = PASSWORD('$MARIADB_ROOT_PASSWORD');
FLUSH PRIVILEGES;
EOF
            print_success "Root 비밀번호 설정 완료"
        # 이미 비밀번호가 설정되어 있는지 확인
        elif mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
            print_info "Root 비밀번호가 이미 설정되어 있습니다."
        else
            print_warning "Root 계정에 접근할 수 없습니다. 수동으로 비밀번호를 설정해주세요."
            print_info "명령어: mysql -u root"
            print_info "그 다음: ALTER USER 'root'@'localhost' IDENTIFIED BY '$MARIADB_ROOT_PASSWORD';"
        fi
        
        # 포트 변경 (필요한 경우)
        if [ "$MARIADB_PORT" != "3306" ]; then
            print_info "포트를 $MARIADB_PORT 로 변경 중..."
            
            if [[ $(uname -m) == 'arm64' ]]; then
                MARIADB_CONFIG="/opt/homebrew/etc/my.cnf"
            else
                MARIADB_CONFIG="/usr/local/etc/my.cnf"
            fi
            
            if [ ! -f "$MARIADB_CONFIG" ]; then
                sudo touch "$MARIADB_CONFIG"
            fi
            
            if grep -q "^port" "$MARIADB_CONFIG"; then
                sudo sed -i.bak "s/^port.*/port = $MARIADB_PORT/" "$MARIADB_CONFIG"
            else
                echo "[mysqld]" | sudo tee -a "$MARIADB_CONFIG" > /dev/null
                echo "port = $MARIADB_PORT" | sudo tee -a "$MARIADB_CONFIG" > /dev/null
            fi
            
            brew services restart mariadb@10.11
            sleep 3
        fi
        
        # 데이터베이스 생성
        print_info "데이터베이스 '$MARIADB_DATABASE' 생성 중..."
        
        # 비밀번호로 연결 시도
        if mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" &> /dev/null 2>&1; then
            mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS \`$MARIADB_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF
            print_success "데이터베이스 생성 완료"
            
            # 사용자 생성 (root가 아닌 경우)
            if [ "$MARIADB_USER" != "root" ] && [ -n "$MARIADB_USER" ]; then
                print_info "사용자 '$MARIADB_USER' 생성 중..."
                mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" <<EOF
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'localhost' IDENTIFIED BY '$MARIADB_PASSWORD';
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$MARIADB_DATABASE\`.* TO '$MARIADB_USER'@'localhost';
GRANT ALL PRIVILEGES ON \`$MARIADB_DATABASE\`.* TO '$MARIADB_USER'@'%';
FLUSH PRIVILEGES;
EOF
                print_success "사용자 생성 완료"
            fi
            
            # 연결 테스트
            if mysql -h localhost -P "$MARIADB_PORT" -u root -p"$MARIADB_ROOT_PASSWORD" -e "USE $MARIADB_DATABASE; SELECT 1;" &> /dev/null 2>&1; then
                print_success "로컬 MariaDB 설정 완료!"
            else
                print_warning "데이터베이스는 생성되었지만 연결 테스트에 실패했습니다."
            fi
        else
            print_error "Root 계정으로 연결할 수 없습니다."
            print_info "다음 명령어로 수동 설정이 필요합니다:"
            print_info "  mysql -u root"
            print_info "  SET PASSWORD FOR 'root'@'localhost' = PASSWORD('$MARIADB_ROOT_PASSWORD');"
            print_info "  CREATE DATABASE \`$MARIADB_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        fi
    fi
fi

# 완료 메시지
echo ""
print_success "========================================="
print_success "  MariaDB 설정 완료!"
print_success "========================================="
echo ""
echo "📋 연결 정보:"
echo "  - Type: $MARIADB_TYPE"
echo "  - Host: localhost"
echo "  - Port: $MARIADB_PORT"
echo "  - Database: $MARIADB_DATABASE"
if [ -n "$MARIADB_USER" ] && [ "$MARIADB_USER" != "root" ]; then
    echo "  - User: root 또는 $MARIADB_USER"
else
    echo "  - User: root"
fi
echo ""
echo "🚀 다음 단계:"
echo "  1. uv run python db_push.py    # 테이블 생성"
echo "  2. uv run python app.py        # 서버 시작"
echo ""

if [ "$MARIADB_TYPE" = "docker" ]; then
    echo "🐳 Docker 명령어:"
    echo "  - 시작:    docker start mariadb-dongwon"
    echo "  - 중지:    docker stop mariadb-dongwon"
    echo "  - 재시작:  docker restart mariadb-dongwon"
    echo "  - 접속:    docker exec -it mariadb-dongwon mysql -u root -p"
    echo "  - 로그:    docker logs mariadb-dongwon"
    echo "  - 삭제:    docker rm -f mariadb-dongwon"
    echo ""
    echo "💡 연결 테스트:"
    echo "  docker exec mariadb-dongwon mysql -u root -p$MARIADB_ROOT_PASSWORD -e 'SHOW DATABASES;'"
else
    echo "🔧 Homebrew 명령어:"
    echo "  - 시작:    brew services start mariadb@10.11"
    echo "  - 중지:    brew services stop mariadb@10.11"
    echo "  - 재시작:  brew services restart mariadb@10.11"
    echo "  - 상태:    brew services list | grep mariadb"
    echo "  - 접속:    mysql -u root -p -P $MARIADB_PORT"
    echo ""
    echo "💡 연결 테스트:"
    echo "  mysql -h localhost -P $MARIADB_PORT -u root -p$MARIADB_ROOT_PASSWORD -e 'SHOW DATABASES;'"
fi
echo ""
echo "📝 .env 파일 확인:"
echo "  DATABASE_URL이 올바르게 설정되어 있는지 확인하세요."
echo ""
