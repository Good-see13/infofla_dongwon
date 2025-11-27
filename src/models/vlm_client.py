"""
VLM 서버 HTTP 클라이언트
에이전트(로컬)에서 모델 서버(원격)로 요청을 보내는 클라이언트
VLMProcessor와 동일한 인터페이스를 유지하여 기존 코드 변경 최소화
"""
import logging
import requests
import cv2
import numpy as np
from typing import Dict, Any
from src.core.config import VLM_SERVER_URL, VLM_SERVER_TIMEOUT

logger = logging.getLogger(__name__)

class VLMHTTPClient:
    """VLM 서버 HTTP 클라이언트 (VLMProcessor와 동일한 인터페이스)"""
    
    def __init__(self, server_url: str = None, timeout: int = None):
        self.server_url = (server_url or VLM_SERVER_URL).rstrip("/")
        self.timeout = timeout or VLM_SERVER_TIMEOUT
        logger.info("VLM HTTP Client initialized: %s", self.server_url)
    
    def check_health(self) -> bool:
        """
        VLM 서버 연결 상태 확인
        
        Returns:
            True if server is available, False otherwise
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=10  # 헬스체크는 짧은 타임아웃 사용
            )
            if response.status_code == 200:
                health_data = response.json()
                vlm_ready = health_data.get("vlm_ready", False)
                if vlm_ready:
                    logger.info("VLM server health check passed: %s", health_data)
                    return True
                else:
                    logger.warning("VLM server is not ready: %s", health_data)
                    return False
            else:
                logger.warning("VLM server health check failed: status=%s", response.status_code)
                return False
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to VLM server at %s (health check failed)", self.server_url)
            return False
        except requests.exceptions.Timeout:
            logger.error("VLM server health check timeout (10s)")
            return False
        except Exception as e:
            logger.error("VLM server health check error: %s", str(e))
            return False
    
    def analyze_image(self, image: np.ndarray, hint: str = "") -> Dict[str, Any]:
        """
        VLM 서버에 이미지 분석 요청
        기존 VLMProcessor.analyze_image()와 동일한 인터페이스 유지
        
        Args:
            image: numpy array 이미지
            hint: YOLO 탐지 결과 힌트
            
        Returns:
            VLM 분석 결과 (기존과 동일한 형식)
        """
        try:
            # 이미지를 JPEG로 인코딩
            _, buffer = cv2.imencode(".jpg", image)
            image_bytes = buffer.tobytes()
            
            # VLM 서버에 요청 (hint는 서버에서 사용하지 않음)
            files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
            
            logger.debug("Sending request to VLM server: %s", self.server_url)
            response = requests.post(
                f"{self.server_url}/analyze",
                files=files,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_msg = f"VLM server error ({response.status_code}): {response.text}"
                logger.error(error_msg)
                return {"type": "error", "message": error_msg}
            
            result = response.json()
            
            # 응답 형식 검증 (기존 VLMProcessor와 동일)
            if "type" not in result:
                logger.warning("Invalid VLM server response: missing 'type' field")
                return {"type": "error", "message": "Invalid VLM server response"}
            
            logger.debug("VLM server response: type=%s", result.get("type"))
            return result
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to VLM server at {self.server_url}"
            logger.error(error_msg)
            return {"type": "error", "message": error_msg}
        except requests.exceptions.Timeout:
            error_msg = f"VLM server timeout ({self.timeout}s)"
            logger.error(error_msg)
            return {"type": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"VLM client error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"type": "error", "message": error_msg}

