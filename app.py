from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.errors import register_exception_handlers
from src.api.lifecycle import register_lifecycle
from src.api.ai import health_router, model_router
from src.api.web import web_router
from src.utils.logger import setup_logging
from src.utils.request_logger import RequestLoggingMiddleware


logger = setup_logging()

app = FastAPI(title="동원 산업 POC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 로깅 미들웨어
app.add_middleware(RequestLoggingMiddleware)

# 공통 예외 핸들러 등록
register_exception_handlers(app)

# 라이프사이클 훅 등록
register_lifecycle(app, logger)

app.include_router(health_router)
app.include_router(model_router)
app.include_router(web_router)

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        access_log=False,  # uvicorn의 기본 액세스 로그 비활성화 (커스텀 미들웨어 사용)
        timeout_keep_alive=120,  # Keep-alive 타임아웃 증가
        limit_concurrency=1000,  # 동시 연결 제한 증가
        limit_max_requests=10000,  # 최대 요청 수 증가
        http="h11"  # HTTP 프로토콜 명시
    )
