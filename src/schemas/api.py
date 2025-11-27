"""
API Response Schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from .detection import DetectionItem


class CameraResult(BaseModel):
    """Single camera detection result"""
    camera_id: int
    model: str
    success: bool
    detections: Optional[List[DetectionItem]] = None
    total_detections: Optional[int] = None
    error: Optional[str] = None


class MultipleDetectionResponse(BaseModel):
    """Multiple camera detection response"""
    success: bool
    results: List[CameraResult]
    description: str
    timestamp: str


class VLMOnlyResponse(BaseModel):
    """VLM-only analysis response"""
    success: bool
    result: Dict[str, Any]
    timestamp: str


class FormattedDetectionResponse(BaseModel):
    """Formatted detection response for API"""
    success: bool
    detections: List[DetectionItem]
    total_detections: int
    model: str
    model_type: str
    timestamp: str

