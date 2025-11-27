"""
요청/응답 로깅 미들웨어
"""

import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logger = logging.getLogger(__name__)

# 로깅에서 제외할 민감한 필드
SENSITIVE_FIELDS = {"password", "token", "access_token", "refresh_token", "secret", "authorization"}


def mask_sensitive_data(data: dict) -> dict:
    """민감한 데이터 마스킹 유틸 (예: password, token 등)"""
    masked = {}
    for k, v in data.items():
        if any(word in k.lower() for word in ["password", "token", "secret"]):
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    요청/응답 상세 로깅 미들웨어 (파일 업로드 안전 버전)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url)
        path = request.url.path
        query_params = dict(request.query_params)
        request_body = None
        response_body = None
        status_code = None

        content_type = request.headers.get("content-type", "").lower()

        # ⚠️ 파일 업로드 요청(multipart/form-data)은 body 로깅 건너뛰기
        if "multipart/form-data" in content_type:
            logger.debug(f"[UPLOAD] Multipart 요청 - body 로깅 생략: {method} {path}")
        elif method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                # 일반 요청(body 읽기)
                body = await request.body()
                if body:
                    try:
                        parsed = json.loads(body.decode("utf-8"))
                        request_body = mask_sensitive_data(parsed)
                    except json.JSONDecodeError:
                        request_body = {"raw": body.decode("utf-8", errors="ignore")[:200]}
                
                # Request body를 다시 복구
                async def receive() -> Message:
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception as e:
                logger.debug(f"요청 본문 읽기 실패: {e}")

        # 응답 처리
        try:
            response = await call_next(request)
            status_code = response.status_code

            # 응답 본문 로깅 (400 이상만)
            if status_code >= 400:
                response_body_bytes = b""
                async for chunk in response.body_iterator:
                    response_body_bytes += chunk

                try:
                    response_body = json.loads(response_body_bytes.decode("utf-8"))
                except json.JSONDecodeError:
                    response_body = response_body_bytes.decode("utf-8", errors="ignore")[:200]

                # 응답을 재생성하여 body iterator 복원
                from starlette.responses import Response as StarletteResponse
                response = StarletteResponse(
                    content=response_body_bytes,
                    status_code=status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

        except Exception as e:
            status_code = 500
            response_body = {"detail": str(e)}
            logger.error(f"요청 처리 중 예외 발생: {e}", exc_info=True)
            raise

        finally:
            process_time = (time.time() - start_time) * 1000  # ms

            # 로그 메시지 구성
            log_parts = [
                f"{client_ip}",
                f'"{method} {path}"',
                f"{status_code}",
                f"{process_time:.2f}ms",
            ]

            if query_params:
                log_parts.append(f"query={json.dumps(query_params, ensure_ascii=False)}")

            if request_body:
                body_str = json.dumps(request_body, ensure_ascii=False)
                if len(body_str) > 500:
                    body_str = body_str[:500] + "..."
                log_parts.append(f"body={body_str}")

            if response_body:
                resp_str = json.dumps(response_body, ensure_ascii=False)
                if len(resp_str) > 500:
                    resp_str = resp_str[:500] + "..."
                log_parts.append(f"response={resp_str}")

            if status_code >= 500:
                logger.error(" | ".join(log_parts))
            elif status_code >= 400:
                logger.warning(" | ".join(log_parts))
            else:
                logger.info(" | ".join(log_parts))

        return response

