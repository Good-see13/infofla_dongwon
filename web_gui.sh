#!/usr/bin/env bash
# Windows Git Bash 호환성을 위해 일부 옵션 완화
set -eo pipefail

# 로컬 웹 GUI 실행 스크립트
# 로컬에서 실행: ./web_gui.sh
# - API 서버 (포트 8000) + GUI 자동 실행
# - VLM은 원격 서버 사용 (기본값: http://114.110.133.13:60005)

# Basic runtime configuration
APP_MODULE="app:app"
APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-dongwon}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

activate_conda() {
  # conda가 없으면 스킵 (Windows Git Bash 등에서 시스템 Python 사용)
  local conda_bin
  if command -v conda >/dev/null 2>&1; then
    conda_bin="$(command -v conda)"
  elif [[ -n "${CONDA_EXE:-}" ]]; then
    conda_bin="${CONDA_EXE}"
  else
    # conda가 없으면 그냥 스킵 (에러 없이)
    return 0
  fi

  # 이미 활성화된 환경이면 스킵
  if [[ "${CONDA_DEFAULT_ENV:-}" == "${CONDA_ENV_NAME}" ]]; then
    return 0
  fi

  # conda base 경로 확인 (에러 무시)
  local conda_base
  conda_base="$("${conda_bin}" info --base 2>/dev/null || echo "")"
  if [[ -z "${conda_base}" ]]; then
    return 0
  fi

  # conda 스크립트 경로 확인 (Linux/Mac과 Windows 모두 지원)
  local conda_script="${conda_base}/etc/profile.d/conda.sh"
  if [[ ! -f "${conda_script}" ]]; then
    # Windows Git Bash 경로
    conda_script="${conda_base}/Scripts/conda.sh"
    if [[ ! -f "${conda_script}" ]]; then
      return 0
    fi
  fi

  # conda 활성화 시도 (실패해도 계속 진행)
  set +u
  source "${conda_script}" 2>/dev/null || return 0
  conda activate "${CONDA_ENV_NAME}" 2>/dev/null || return 0
  set -u
}

# 환경 변수 설정
export ENABLE_GUI=true  # GUI 자동 실행
# USE_VLM은 기본값이 true이므로 명시적 설정 불필요

# VLM_SERVER_URL이 설정되지 않았으면 기본값 사용 (원격 서버)
if [ -z "${VLM_SERVER_URL:-}" ]; then
    export VLM_SERVER_URL="http://114.110.133.13:60005"
    echo "Using default VLM server: ${VLM_SERVER_URL}"
else
    echo "Using VLM server from environment: ${VLM_SERVER_URL}"
fi

# Conda 환경 활성화 (선택적 - 없어도 계속 진행)
activate_conda

# uvicorn 확인 (conda 환경 또는 시스템 Python)
if ! command -v uvicorn >/dev/null 2>&1; then
    echo "uvicorn not found. Please install requirements: pip install -r requirements.txt" >&2
    exit 1
fi

echo "=========================================="
echo "Starting Local Web GUI"
echo "=========================================="
if [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    echo "Conda Environment: ${CONDA_DEFAULT_ENV}"
else
    # Python 경로 표시
    python_cmd=""
    if command -v python >/dev/null 2>&1; then
        python_cmd="$(command -v python)"
    elif command -v python3 >/dev/null 2>&1; then
        python_cmd="$(command -v python3)"
    else
        python_cmd="Not found"
    fi
    echo "Python: ${python_cmd}"
fi
echo "API Server: http://${APP_HOST}:${APP_PORT}"
echo "GUI: Enabled (auto-start)"
echo "VLM Server: ${VLM_SERVER_URL}"
echo "=========================================="
echo ""

# uvicorn 실행 (GUI 자동 실행됨)
cd "${PROJECT_ROOT}"
exec uvicorn \
    "${APP_MODULE}" \
    --host "${APP_HOST}" \
    --port "${APP_PORT}" \
    --reload \
    --log-level info

