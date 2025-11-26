#!/usr/bin/env bash
set -Eeuo pipefail

# VLM 모델 서버 실행 스크립트
# 서버에서 실행: ./start_vlm_server.sh

# Basic runtime configuration (override via env vars if needed)
APP_MODULE="vlm_server:app"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-60005}"
MIG_DEVICE_ID="${MIG_DEVICE_ID:-MIG-32384341-6c26-5ba4-8170-c732a09c3b4d}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-dongwon}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
PID_FILE="${PROJECT_ROOT}/vlm-server.pid"

if [[ ! -f "${PROJECT_ROOT}/vlm_server.py" ]]; then
  echo "vlm_server.py not found in ${PROJECT_ROOT}" >&2
  exit 1
fi

activate_conda() {
  if [[ "${CONDA_DEFAULT_ENV:-}" == "${CONDA_ENV_NAME}" ]]; then
    return
  fi

  local conda_bin
  if command -v conda >/dev/null 2>&1; then
    conda_bin="$(command -v conda)"
  elif [[ -n "${CONDA_EXE:-}" && -x "${CONDA_EXE}" ]]; then
    conda_bin="${CONDA_EXE}"
  else
    echo "conda executable not found. Ensure conda is installed and on PATH." >&2
    exit 1
  fi

  local conda_base
  conda_base="$("${conda_bin}" info --base)"
  local conda_script="${conda_base}/etc/profile.d/conda.sh"
  if [[ ! -f "${conda_script}" ]]; then
    echo "Unable to locate conda init script at ${conda_script}" >&2
    exit 1
  fi

  # shellcheck disable=SC1090
  set +u
  source "${conda_script}"
  conda activate "${CONDA_ENV_NAME}"
  set -u
}

is_running() {
  if [[ -f "${PID_FILE}" ]]; then
    local pid
    pid="$(cat "${PID_FILE}")"
    if ps -p "${pid}" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_server() {
  if is_running; then
    echo "VLM server already running with PID $(cat "${PID_FILE}"). Stop it first." >&2
    exit 1
  fi

  activate_conda

  if ! command -v uvicorn >/dev/null 2>&1; then
    echo "uvicorn not found inside conda env '${CONDA_ENV_NAME}'. Install requirements first." >&2
    exit 1
  fi

  # conda 환경의 uvicorn 경로 확인
  local uvicorn_path
  uvicorn_path="$(command -v uvicorn)"
  
  # conda base 경로 확인
  local conda_base
  conda_base="$(conda info --base)"

  mkdir -p "${LOG_DIR}"
  export PYTHONUNBUFFERED=1
  export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
  export USE_VLM=true
  export VLM_DEVICE_MAP=cuda

  # conda 환경 정보를 스크립트로 저장하여 nohup에서 사용
  local conda_activate_script="${PROJECT_ROOT}/.conda_activate.sh"
  {
    echo "#!/bin/bash"
    echo "set -e"
    echo "source \"${conda_base}/etc/profile.d/conda.sh\""
    echo "conda activate \"${CONDA_ENV_NAME}\""
    echo "export PYTHONUNBUFFERED=1"
    echo "export PYTHONPATH=\"${PROJECT_ROOT}:\${PYTHONPATH:-}\""
    echo "export USE_VLM=true"
    echo "export VLM_DEVICE_MAP=cuda"
    echo "cd \"${PROJECT_ROOT}\""
    echo "exec env CUDA_VISIBLE_DEVICES=\"${MIG_DEVICE_ID}\" \\"
    echo "  stdbuf -oL -eL \\"
    echo "  \"${uvicorn_path}\" \"${APP_MODULE}\" \\"
    echo "    --host \"${APP_HOST}\" \\"
    echo "    --port \"${APP_PORT}\" \\"
    echo "    --log-level info"
  } > "${conda_activate_script}"
  chmod +x "${conda_activate_script}"

  (
    cd "${PROJECT_ROOT}"
    nohup bash "${conda_activate_script}" \
      >> "${LOG_DIR}/vlm-server.out" 2>&1 &
    echo $! > "${PID_FILE}"
  )

  # 임시 스크립트 정리 (선택사항)
  # rm -f "${conda_activate_script}"

  echo "VLM server started with PID $(cat "${PID_FILE}")."
  echo "Conda Environment: ${CONDA_ENV_NAME}"
  echo "Server running on ${APP_HOST}:${APP_PORT}"
  echo "Logs: tail -F ${LOG_DIR}/vlm-server.out"
}

start_server "$@"
