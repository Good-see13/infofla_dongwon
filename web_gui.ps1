# 로컬 웹 GUI 실행 스크립트 (Windows PowerShell)
# 로컬에서 실행: .\web_gui.ps1
# - API 서버 (포트 8000) + GUI 자동 실행
# - VLM은 원격 서버 사용 (기본값: http://114.110.133.13:60005)

# Basic runtime configuration
$APP_MODULE = "app:app"
$APP_HOST = if ($env:APP_HOST) { $env:APP_HOST } else { "127.0.0.1" }
$APP_PORT = if ($env:APP_PORT) { $env:APP_PORT } else { "8000" }

# 프로젝트 루트 경로
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_ROOT

# 로그 디렉토리 생성
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# 환경 변수 설정
$env:ENABLE_GUI = "true"
$env:USE_VLM = "true"

# VLM_SERVER_URL이 설정되지 않았으면 기본값 사용
if (-not $env:VLM_SERVER_URL) {
    $env:VLM_SERVER_URL = "http://114.110.133.13:60005"
    Write-Host "Using default VLM server: $env:VLM_SERVER_URL"
} else {
    Write-Host "Using VLM server from environment: $env:VLM_SERVER_URL"
}

# venv 활성화 (있는 경우)
$venvActivated = $false
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..."
    & ".venv\Scripts\Activate.ps1"
    $venvActivated = $true
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..."
    & "venv\Scripts\Activate.ps1"
    $venvActivated = $true
} else {
    Write-Host "No virtual environment found. Using system Python."
}

# uvicorn 확인
$uvicornPath = Get-Command uvicorn -ErrorAction SilentlyContinue
if (-not $uvicornPath) {
    Write-Host "uvicorn not found. Please install requirements: pip install -r requirements.txt" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "=========================================="
Write-Host "Starting Local Web GUI"
Write-Host "=========================================="
if ($venvActivated -and $env:VIRTUAL_ENV) {
    Write-Host "Virtual Environment: $env:VIRTUAL_ENV"
} else {
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonPath) {
        $pythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
    }
    if ($pythonPath) {
        Write-Host "Python: $pythonPath"
    }
}
Write-Host "API Server: http://${APP_HOST}:${APP_PORT}"
Write-Host "GUI: Enabled (auto-start)"
Write-Host "VLM Server: $env:VLM_SERVER_URL"
Write-Host "=========================================="
Write-Host ""

# uvicorn 실행 (GUI 자동 실행됨)
& uvicorn $APP_MODULE --host $APP_HOST --port $APP_PORT --reload --log-level info

