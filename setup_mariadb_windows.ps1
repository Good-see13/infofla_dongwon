# MariaDB 자동 설치 및 설정 스크립트 (Windows용)
# PowerShell 스크립트
# Docker 또는 로컬 설치 지원

# 관리자 권한 확인
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARNING] 관리자 권한으로 실행하는 것을 권장합니다." -ForegroundColor Yellow
    Write-Host "일부 기능이 제한될 수 있습니다." -ForegroundColor Yellow
    Write-Host ""
}

# 함수: 메시지 출력
function Print-Info {
    param([string]$message)
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Print-Success {
    param([string]$message)
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$message)
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$message)
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# 함수: .env 파일에서 값 읽기
function Get-EnvValue {
    param([string]$key)
    
    if (Test-Path ".env") {
        $content = Get-Content ".env" | Where-Object { $_ -match "^$key=" }
        if ($content) {
            $value = $content -replace "^$key=", "" -replace '"', '' -replace "'", ''
            return $value.Trim()
        }
    }
    return $null
}

# .env 파일 확인
if (-not (Test-Path ".env")) {
    Print-Error ".env 파일이 없습니다!"
    Print-Info ".env 파일을 먼저 생성해주세요."
    Print-Info ""
    Print-Info "예시 .env 파일 내용:"
    Print-Info "MARIADB_ROOT_PASSWORD=12345"
    Print-Info "MARIADB_DATABASE=dongwon"
    Print-Info "MARIADB_USER=test"
    Print-Info "MARIADB_PASSWORD=12345"
    Print-Info "MARIADB_PORT=3307"
    exit 1
}

# .env에서 환경변수 로드
Print-Info ".env 파일에서 설정 로드 중..."
$MARIADB_ROOT_PASSWORD = Get-EnvValue "MARIADB_ROOT_PASSWORD"
$MARIADB_DATABASE = Get-EnvValue "MARIADB_DATABASE"
$MARIADB_USER = Get-EnvValue "MARIADB_USER"
$MARIADB_PASSWORD = Get-EnvValue "MARIADB_PASSWORD"
$MARIADB_PORT = Get-EnvValue "MARIADB_PORT"

# 기본값 설정
if ([string]::IsNullOrEmpty($MARIADB_PORT)) {
    $MARIADB_PORT = "3307"
}

# 환경변수 검증
if ([string]::IsNullOrEmpty($MARIADB_ROOT_PASSWORD) -or [string]::IsNullOrEmpty($MARIADB_DATABASE)) {
    Print-Error ".env 파일에 필수 값이 없습니다!"
    Print-Info "MARIADB_ROOT_PASSWORD, MARIADB_DATABASE 등을 확인해주세요."
    exit 1
}

Print-Success "설정 로드 완료"
Write-Host "  - Database: $MARIADB_DATABASE"
Write-Host "  - User: $MARIADB_USER"
Write-Host "  - Port: $MARIADB_PORT"
Write-Host ""

# 변수 초기화
$MARIADB_INSTALLED = $false
$MARIADB_TYPE = ""  # "docker", "local", "none"
$CONTAINER_NAME = "mariadb-dongwon"

# 1. Docker 컨테이너 확인
Print-Info "Docker MariaDB 컨테이너 확인 중..."
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue

if ($dockerInstalled) {
    try {
        $dockerRunning = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            # MariaDB 컨테이너가 실행 중인지 확인
            $containers = docker ps --format "{{.Names}}" | Select-String "mariadb"
            
            if ($containers) {
                $existingContainer = $containers[0].ToString()
                Print-Success "Docker MariaDB 컨테이너 발견: $existingContainer"
                
                # 컨테이너 포트 확인
                $portInfo = docker port $existingContainer 2>&1 | Select-String "3306"
                if ($portInfo) {
                    $containerPort = ($portInfo -split ":")[1]
                    Print-Info "Docker MariaDB 포트: $containerPort"
                }
                
                # 연결 테스트
                $testResult = docker exec $existingContainer mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Print-Success "Docker MariaDB 연결 성공!"
                    $MARIADB_INSTALLED = $true
                    $MARIADB_TYPE = "docker"
                    $CONTAINER_NAME = $existingContainer
                } else {
                    Print-Warning "Docker MariaDB가 있지만 비밀번호가 다릅니다."
                }
            } else {
                Print-Info "Docker는 있지만 MariaDB 컨테이너는 없습니다."
            }
        } else {
            Print-Info "Docker는 설치되어 있지만 실행 중이 아닙니다."
        }
    } catch {
        Print-Info "Docker 상태 확인 중 오류 발생"
    }
} else {
    Print-Info "Docker가 설치되어 있지 않습니다."
}

# 2. 로컬 MariaDB 확인 (Docker가 없거나 컨테이너가 없는 경우)
if (-not $MARIADB_INSTALLED) {
    Print-Info "로컬 MariaDB 설치 확인 중..."
    
    # MySQL 클라이언트 확인
    $mysqlCmd = Get-Command mysql -ErrorAction SilentlyContinue
    
    if ($mysqlCmd) {
        Print-Success "MySQL/MariaDB 클라이언트 발견"
        
        # 연결 테스트
        try {
            $testResult = mysql -h localhost -P $MARIADB_PORT -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Print-Success "로컬 MariaDB 연결 성공!"
                $MARIADB_INSTALLED = $true
                $MARIADB_TYPE = "local"
            } else {
                Print-Info "로컬 MariaDB가 있지만 연결할 수 없습니다."
            }
        } catch {
            Print-Info "로컬 MariaDB 연결 실패"
        }
    } else {
        Print-Info "로컬에 MySQL/MariaDB가 설치되어 있지 않습니다."
    }
}

# 3. MariaDB 설치 필요 여부 확인
if (-not $MARIADB_INSTALLED) {
    Write-Host ""
    Print-Warning "MariaDB가 설치되어 있지 않습니다!"
    Write-Host ""
    Write-Host "설치 옵션을 선택하세요:"
    Write-Host "  1) Docker로 MariaDB 설치 (권장)"
    Write-Host "  2) 로컬에 MariaDB 설치 (수동)"
    Write-Host "  3) 기존 MariaDB 사용 (설정만 진행)"
    Write-Host "  4) 종료"
    Write-Host ""
    
    $choice = Read-Host "선택 (1-4)"
    
    switch ($choice) {
        "1" {
            # Docker 설치
            if (-not $dockerInstalled) {
                Print-Error "Docker가 설치되어 있지 않습니다!"
                Print-Info "Docker Desktop을 먼저 설치해주세요:"
                Print-Info "https://www.docker.com/products/docker-desktop/"
                exit 1
            }
            
            Print-Info "Docker로 MariaDB 설치 중..."
            
            # 기존 컨테이너 확인
            $existingContainer = docker ps -a --format "{{.Names}}" | Select-String "^mariadb-dongwon$"
            
            if ($existingContainer) {
                Print-Warning "이미 'mariadb-dongwon' 컨테이너가 존재합니다."
                $deleteChoice = Read-Host "삭제하고 새로 만드시겠습니까? (y/n)"
                
                if ($deleteChoice -eq "y" -or $deleteChoice -eq "Y") {
                    Print-Info "기존 컨테이너 삭제 중..."
                    docker rm -f mariadb-dongwon 2>&1 | Out-Null
                    Print-Success "기존 컨테이너 삭제 완료"
                } else {
                    # 컨테이너 시작
                    Print-Info "기존 컨테이너 시작 중..."
                    docker start mariadb-dongwon 2>&1 | Out-Null
                    Start-Sleep -Seconds 5
                    
                    $testResult = docker exec mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Print-Success "기존 컨테이너 시작 완료!"
                        $MARIADB_INSTALLED = $true
                        $MARIADB_TYPE = "docker"
                    } else {
                        Print-Error "컨테이너는 시작되었지만 연결할 수 없습니다."
                        Print-Info "비밀번호를 확인하거나 컨테이너를 삭제하고 다시 실행해주세요."
                        exit 1
                    }
                }
            }
            
            if (-not $MARIADB_INSTALLED) {
                # 새 컨테이너 생성
                Print-Info "새 MariaDB 컨테이너 생성 중..."
                
                $dockerCmd = "docker run -d --name mariadb-dongwon " +
                            "-p ${MARIADB_PORT}:3306 " +
                            "-e MARIADB_ROOT_PASSWORD=$MARIADB_ROOT_PASSWORD " +
                            "-e MARIADB_DATABASE=$MARIADB_DATABASE "
                
                if (-not [string]::IsNullOrEmpty($MARIADB_USER)) {
                    $dockerCmd += "-e MARIADB_USER=$MARIADB_USER " +
                                 "-e MARIADB_PASSWORD=$MARIADB_PASSWORD "
                }
                
                $dockerCmd += "mariadb:latest"
                
                Invoke-Expression $dockerCmd
                
                if ($LASTEXITCODE -eq 0) {
                    Print-Success "Docker 컨테이너 생성 완료"
                    Print-Info "MariaDB 초기화 대기 중 (10초)..."
                    Start-Sleep -Seconds 10
                    
                    # 연결 테스트 (최대 3번 재시도)
                    $connected = $false
                    for ($i = 1; $i -le 3; $i++) {
                        Print-Info "연결 테스트 중... ($i/3)"
                        $testResult = docker exec mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "SELECT 1;" 2>&1
                        if ($LASTEXITCODE -eq 0) {
                            Print-Success "Docker MariaDB 연결 성공!"
                            $MARIADB_INSTALLED = $true
                            $MARIADB_TYPE = "docker"
                            $connected = $true
                            break
                        }
                        Start-Sleep -Seconds 5
                    }
                    
                    if (-not $connected) {
                        Print-Error "MariaDB 컨테이너는 생성되었지만 연결할 수 없습니다."
                        Print-Info "잠시 후 다시 시도해주세요."
                        exit 1
                    }
                } else {
                    Print-Error "Docker 컨테이너 생성 실패"
                    exit 1
                }
            }
        }
        "2" {
            Print-Info "로컬 MariaDB 설치 가이드:"
            Write-Host ""
            Write-Host "1. MariaDB 다운로드:"
            Write-Host "   https://mariadb.org/download/"
            Write-Host ""
            Write-Host "2. 설치 시 다음 정보 입력:"
            Write-Host "   - Root Password: $MARIADB_ROOT_PASSWORD"
            Write-Host "   - Port: $MARIADB_PORT"
            Write-Host ""
            Write-Host "3. 설치 후 이 스크립트를 다시 실행하세요."
            Write-Host ""
            exit 0
        }
        "3" {
            Print-Info "기존 MariaDB 사용 모드"
            $MARIADB_INSTALLED = $true
            $MARIADB_TYPE = "existing"
        }
        default {
            Print-Info "종료합니다."
            exit 0
        }
    }
}

# 4. 데이터베이스 및 사용자 설정
if ($MARIADB_INSTALLED) {
    Write-Host ""
    Print-Info "데이터베이스 및 사용자 설정 중..."
    
    if ($MARIADB_TYPE -eq "docker") {
        # Docker 환경
        Print-Info "데이터베이스 '$MARIADB_DATABASE' 생성 중..."
        
        $createDbCmd = "CREATE DATABASE IF NOT EXISTS ``$MARIADB_DATABASE`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        docker exec mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e $createDbCmd 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Print-Success "데이터베이스 생성 완료"
        } else {
            Print-Error "데이터베이스 생성 실패"
        }
        
        # 사용자 생성 (root가 아닌 경우)
        if (-not [string]::IsNullOrEmpty($MARIADB_USER) -and $MARIADB_USER -ne "root") {
            Print-Info "사용자 '$MARIADB_USER' 생성 중..."
            
            $createUserSql = @"
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';
GRANT ALL PRIVILEGES ON ``$MARIADB_DATABASE``.* TO '$MARIADB_USER'@'%';
FLUSH PRIVILEGES;
"@
            
            $createUserSql | docker exec -i mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" 2>&1 | Out-Null
            Print-Success "사용자 생성 완료"
        }
        
        # 연결 테스트
        $testResult = docker exec mariadb-dongwon mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "USE $MARIADB_DATABASE; SELECT 1;" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Print-Success "Docker MariaDB 설정 완료!"
        } else {
            Print-Warning "데이터베이스는 생성되었지만 연결 테스트에 실패했습니다."
        }
        
    } else {
        # 로컬 설치의 경우
        Print-Info "데이터베이스 '$MARIADB_DATABASE' 생성 중..."
        
        $createDbCmd = "CREATE DATABASE IF NOT EXISTS ``$MARIADB_DATABASE`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        mysql -h localhost -P $MARIADB_PORT -u root -p"$MARIADB_ROOT_PASSWORD" -e $createDbCmd 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Print-Success "데이터베이스 생성 완료"
            
            # 사용자 생성 (root가 아닌 경우)
            if (-not [string]::IsNullOrEmpty($MARIADB_USER) -and $MARIADB_USER -ne "root") {
                Print-Info "사용자 '$MARIADB_USER' 생성 중..."
                
                $createUserSql = @"
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'localhost' IDENTIFIED BY '$MARIADB_PASSWORD';
CREATE USER IF NOT EXISTS '$MARIADB_USER'@'%' IDENTIFIED BY '$MARIADB_PASSWORD';
GRANT ALL PRIVILEGES ON ``$MARIADB_DATABASE``.* TO '$MARIADB_USER'@'localhost';
GRANT ALL PRIVILEGES ON ``$MARIADB_DATABASE``.* TO '$MARIADB_USER'@'%';
FLUSH PRIVILEGES;
"@
                
                $createUserSql | mysql -h localhost -P $MARIADB_PORT -u root -p"$MARIADB_ROOT_PASSWORD" 2>&1 | Out-Null
                Print-Success "사용자 생성 완료"
            }
            
            # 연결 테스트
            $testResult = mysql -h localhost -P $MARIADB_PORT -u root -p"$MARIADB_ROOT_PASSWORD" -e "USE $MARIADB_DATABASE; SELECT 1;" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Print-Success "로컬 MariaDB 설정 완료!"
            } else {
                Print-Warning "데이터베이스는 생성되었지만 연결 테스트에 실패했습니다."
            }
        } else {
            Print-Error "데이터베이스 생성 실패"
            Print-Info "수동으로 다음 명령어를 실행해주세요:"
            Print-Info "  mysql -u root -p"
            Print-Info "  CREATE DATABASE ``$MARIADB_DATABASE`` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        }
    }
}

# 완료 메시지
Write-Host ""
Print-Success "========================================="
Print-Success "  MariaDB 설정 완료!"
Print-Success "========================================="
Write-Host ""
Write-Host "📋 연결 정보:"
Write-Host "  - Type: $MARIADB_TYPE"
Write-Host "  - Host: localhost"
Write-Host "  - Port: $MARIADB_PORT"
Write-Host "  - Database: $MARIADB_DATABASE"
if (-not [string]::IsNullOrEmpty($MARIADB_USER) -and $MARIADB_USER -ne "root") {
    Write-Host "  - User: root 또는 $MARIADB_USER"
} else {
    Write-Host "  - User: root"
}
Write-Host ""
Write-Host "🚀 다음 단계:"
Write-Host "  1. uv run python db_push.py    # 테이블 생성"
Write-Host "  2. uv run python app.py        # 서버 시작"
Write-Host ""

if ($MARIADB_TYPE -eq "docker") {
    Write-Host "🐳 Docker 명령어:"
    Write-Host "  - 시작:    docker start mariadb-dongwon"
    Write-Host "  - 중지:    docker stop mariadb-dongwon"
    Write-Host "  - 재시작:  docker restart mariadb-dongwon"
    Write-Host "  - 접속:    docker exec -it mariadb-dongwon mysql -u root -p"
    Write-Host "  - 로그:    docker logs mariadb-dongwon"
    Write-Host "  - 삭제:    docker rm -f mariadb-dongwon"
    Write-Host ""
    Write-Host "💡 연결 테스트:"
    Write-Host "  docker exec mariadb-dongwon mysql -u root -p$MARIADB_ROOT_PASSWORD -e 'SHOW DATABASES;'"
} else {
    Write-Host "🔧 MySQL 명령어:"
    Write-Host "  - 접속:    mysql -u root -p -P $MARIADB_PORT"
    Write-Host "  - 서비스:  services.msc 에서 MySQL/MariaDB 확인"
    Write-Host ""
    Write-Host "💡 연결 테스트:"
    Write-Host "  mysql -h localhost -P $MARIADB_PORT -u root -p$MARIADB_ROOT_PASSWORD -e 'SHOW DATABASES;'"
}
Write-Host ""
Write-Host "📝 .env 파일 확인:"
Write-Host "  DATABASE_URL이 올바르게 설정되어 있는지 확인하세요."
Write-Host ""

