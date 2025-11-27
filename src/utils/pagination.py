"""
페이징 공통 유틸리티
"""

from typing import Optional
from pydantic import BaseModel, Field
import math


class PaginationParams(BaseModel):
    """페이징 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호 (1부터 시작)")
    page_size: int = Field(default=10, ge=1, le=100, description="페이지당 항목 수 (최대 100)")


class PaginationMeta(BaseModel):
    """페이징 메타데이터"""
    total: int = Field(..., description="전체 항목 수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지당 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev: bool = Field(..., description="이전 페이지 존재 여부")


def create_pagination_meta(
    total: int,
    page: int,
    page_size: int
) -> PaginationMeta:
    """
    페이징 메타데이터 생성
    
    Args:
        total: 전체 항목 수
        page: 현재 페이지
        page_size: 페이지당 항목 수
        
    Returns:
        페이징 메타데이터
    """
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    return PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


def get_skip_limit(page: int, page_size: int) -> tuple[int, int]:
    """
    페이징 파라미터를 skip/limit으로 변환
    
    Args:
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수
        
    Returns:
        (skip, limit) 튜플
    """
    skip = (page - 1) * page_size
    limit = page_size
    
    return skip, limit

