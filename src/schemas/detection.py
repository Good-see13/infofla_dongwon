"""
Detection Response Schemas
"""

from typing import List
from pydantic import BaseModel


class DetectionItem(BaseModel):
    """Single detection item"""
    class_name: str
    confidence: float
    bbox: List[float]
    class_id: int


class DetectionResponse(BaseModel):
    """YOLO Detection Response"""
    success: bool
    detections: List[DetectionItem]
    total_detections: int
    model: str
    model_type: str
    timestamp: str

