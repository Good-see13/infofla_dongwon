"""
Analysis Response Schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class VLMResult(BaseModel):
    """VLM Analysis Result"""
    type: str
    count: int = 0
    description: str = ""
    text_content: Optional[str] = None
    raw_output: Optional[str] = None


class YOLOResult(BaseModel):
    """YOLO Detection Result"""
    success: bool
    detections: List[Dict[str, Any]]
    total_detections: int
    model: str
    model_type: str


class BaseAnalysisResponse(BaseModel):
    """Base Analysis Response"""
    success: bool
    analysis_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        arbitrary_types_allowed = True


class SimilarItem(BaseModel):
    """Similar item from DB 2nd verification"""
    itemName: str
    itemId: int
    score: float = Field(..., description="유사도 점수 (0.0 ~ 1.0)")
    description: Optional[str] = Field(None, description="DB description")


class ObjectAnalysisResponse(BaseAnalysisResponse):
    """Object Detection Analysis Response"""
    type: str = "object"
    analysis_type: str = "object"
    vlm_result: VLMResult
    yolo_result: YOLOResult
    count: int
    vlm_count: int
    message: str
    next_action: str = "confirm_required"
    confirmation_prompt: str
    similar_items: List[SimilarItem] = Field(default_factory=list, description="DB 2차 검증 유사 품목 목록")


class PaperAnalysisResponse(BaseAnalysisResponse):
    """Paper/Document Analysis Response"""
    type: str = "paper"
    analysis_type: str = "paper"
    vlm_result: VLMResult
    yolo_result: Optional[YOLOResult] = None
    count: Optional[int] = None
    message: str
    extracted_text: str
    next_action: str = "input_required"
    input_prompt: str
    confirmation_prompt: str


class DetectionCandidate(BaseModel):
    """Detection candidate for similarity search"""
    class_name: str
    confidence: float
    bbox: List[float]


class NewObjectAnalysisResponse(BaseAnalysisResponse):
    """New Object Analysis Response (unknown type treated as new object)"""
    analysis_type: str = "new_object"
    vlm_result: VLMResult
    yolo_result: Optional[YOLOResult] = None
    detection_candidates: List[DetectionCandidate] = []  # Top 3 detection results for DB similarity search
    next_action: str = "manual_review"
    message: str
    description: str = ""  # Detailed description from VLM for new object registration


class ErrorAnalysisResponse(BaseAnalysisResponse):
    """Error Response"""
    success: bool = False
    analysis_type: str = "error"
    error: str

