"""
Image Processing Module
"""

import json
import logging
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
import torch
from PIL import Image

from src.models.exceptions import ModelLoadError, build_error_message
from src.core.config import VLM_MAX_NEW_TOKENS
from .prompts import VLM_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image Processing Class"""
    
    @staticmethod
    def process_image(image_bytes: bytes) -> np.ndarray:
        """Convert image bytes to OpenCV image"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Invalid image format")
        
        return image
    
    @staticmethod
    def parse_detections(results) -> List[Dict[str, Any]]:
        """Parse YOLO results to extract detection information"""
        detections = []
        
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = results[0].names[class_id]
                
                detections.append({
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "class_id": class_id
                })
        
        return detections


class VLMProcessor:
    """VLM Image Analysis Processor"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self._minimum_torch_version = (2, 1, 0)
    
    def analyze_image(self, image: np.ndarray, hint: str = "") -> Dict[str, Any]:
        if not self.model_manager.is_ready():
            try:
                self.model_manager.ensure_loaded()
            except ModelLoadError as exc:
                return {"type": "error", "message": str(exc)}
        
        try:
            if not self._is_supported_torch_version():
                required = ".".join(map(str, self._minimum_torch_version))
                return {
                    "type": "error",
                    "message": f"PyTorch>={required} is required for VLM inference",
                }
            
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
            pil_image = Image.fromarray(image_rgb)
            
            prompt_text = VLM_ANALYSIS_PROMPT
            if hint:
                prompt_text = prompt_text + "\nHint: " + hint

            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": prompt_text}
                ]
            }]
            
            inputs = self.model_manager.processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, 
                return_dict=True, return_tensors="pt"
            )
            inputs = inputs.to(self.model_manager.model.device)
            
            with torch.no_grad():
                generated_ids = self.model_manager.model.generate(**inputs, max_new_tokens=VLM_MAX_NEW_TOKENS)
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] 
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.model_manager.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, 
                clean_up_tokenization_spaces=False
            )
            
            # JSON 파싱 시도 (마크다운 코드 블록 제거 포함)
            raw_output = output_text[0] if output_text else ""
            
            # 마크다운 코드 블록 제거 시도
            cleaned_output = raw_output.strip()
            if cleaned_output.startswith("```"):
                # ```json 또는 ```로 시작하는 경우 제거
                lines = cleaned_output.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_output = "\n".join(lines).strip()
            
            try:
                parsed = json.loads(cleaned_output)
                
                # 스키마 검증 및 기본값 설정
                result = {
                    "type": parsed.get("type", "unknown"),
                    "count": int(parsed.get("count", 0)) if isinstance(parsed.get("count"), (int, float)) else 0,
                    "description": str(parsed.get("description", "")),
                    "text_content": parsed.get("text_content") if parsed.get("text_content") is not None else None
                }
                
                # 타입 검증
                if result["type"] not in ["object", "paper", "unknown"]:
                    logger.warning("Invalid type '%s' from VLM, defaulting to 'unknown'", result["type"])
                    result["type"] = "unknown"
                
                # 타입에 따른 기본값 설정
                if result["type"] == "paper":
                    # 문서인 경우 count는 0
                    result["count"] = 0
                    if result["text_content"] is None:
                        result["text_content"] = ""
                elif result["type"] == "object":
                    # 객체인 경우 text_content는 None
                    result["text_content"] = None
                elif result["type"] == "unknown":
                    # unknown 타입 (new object로 처리됨)
                    result["count"] = 0
                    result["text_content"] = None
                
                return result
                
            except json.JSONDecodeError as e:
                logger.warning("VLM output is not valid JSON: %s. Raw output: %s", e, raw_output[:200])
                # 파싱 실패 시 structured output 기본 구조 반환
                # raw_output에서 유용한 정보 추출 시도
                description = "Failed to parse VLM response"
                if raw_output:
                    # raw_output의 앞부분에서 설명 추출 시도
                    raw_clean = raw_output[:200].strip()
                    if raw_clean:
                        description = f"VLM response parsing failed. Raw output: {raw_clean}"
                
                return {
                    "type": "unknown",
                    "count": 0,
                    "description": description,
                    "text_content": None,
                    "raw_output": raw_output[:500] if raw_output else None,  # 최대 500자만 저장
                    "parse_error": str(e)
                }
        
        except Exception as e:
            message = build_error_message("VLM analysis failed", str(e))
            logger.error(message)
            return {"type": "error", "message": message}

    def _is_supported_torch_version(self) -> bool:
        """Check whether the installed torch version satisfies minimum requirements."""
        return _parse_version(torch.__version__) >= self._minimum_torch_version


def _parse_version(version: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into a comparable tuple."""
    parts: List[int] = []
    for token in version.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])
