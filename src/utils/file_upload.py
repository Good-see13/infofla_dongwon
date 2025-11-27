"""
파일 업로드 공통 유틸리티
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 허용된 이미지 MIME 타입
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg", 
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp"
}

# 허용된 이미지 확장자
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# 이미지 매직 넘버 (파일 시그니처) - 바이트 코드로 이미지 검증
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "jpg",  # JPEG
    b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a": "png",  # PNG
    b"\x47\x49\x46\x38\x37\x61": "gif",  # GIF87a
    b"\x47\x49\x46\x38\x39\x61": "gif",  # GIF89a
    b"\x52\x49\x46\x46": "webp",  # WEBP (RIFF 헤더)
    b"\x42\x4d": "bmp",  # BMP
}

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# 스트림 청크 크기 (1MB)
CHUNK_SIZE = 1 * 1024 * 1024  # 1MB

# 시그니처 검증용 바이트 크기
SIGNATURE_SIZE = 32  # 처음 32 바이트만 읽어서 검증


def get_upload_path() -> str:
    """
    업로드 경로 반환 (.env에서 읽거나 기본값 사용)
    
    Returns:
        업로드 기본 경로
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    upload_path = os.getenv("UPLOAD_PATH", "./uploads")
    return upload_path


def validate_item_id(item_id: int) -> int:
    """
    item_id 검증 (경로 탐색 공격 방지)
    
    Args:
        item_id: 아이템 ID
        
    Returns:
        검증된 item_id
        
    Raises:
        HTTPException: item_id가 유효하지 않은 경우
    """
    if not isinstance(item_id, int) or item_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 품목 ID입니다."
        )
    return item_id


def validate_upload_path(item_folder: Path, base_path: Path) -> Path:
    """
    업로드 경로 검증 (경로 탐색 공격 방지)
    
    Args:
        item_folder: 아이템 폴더 경로
        base_path: 기본 업로드 경로
        
    Returns:
        검증된 경로
        
    Raises:
        HTTPException: 경로가 유효하지 않은 경우
    """
    # 경로 정규화
    resolved_item_folder = item_folder.resolve()
    resolved_base_path = base_path.resolve()
    
    # 경로가 base_path 하위에 있는지 확인
    try:
        resolved_item_folder.relative_to(resolved_base_path)
    except ValueError:
        logger.error(f"경로 탐색 공격 시도 감지: item_folder={item_folder}, base_path={base_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 경로입니다."
        )
    
    return resolved_item_folder


def validate_image_by_bytes(file_bytes: bytes) -> Optional[str]:
    """
    파일의 바이트 코드로 이미지 타입 검증
    
    Args:
        file_bytes: 파일 바이트 데이터
        
    Returns:
        이미지 타입 (jpg, png, gif 등) 또는 None
    """
    for signature, image_type in IMAGE_SIGNATURES.items():
        if file_bytes.startswith(signature):
            return image_type
    
    return None


def validate_image_extension(filename: str) -> bool:
    """
    파일 확장자로 이미지 검증
    
    Args:
        filename: 파일 이름
        
    Returns:
        유효한 이미지 확장자 여부
    """
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    파일명 정제 - 위험한 문자 제거 (보안)
    
    Args:
        filename: 원본 파일명
        
    Returns:
        정제된 파일명
    """
    import re
    
    # 경로 구분자 제거
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # 영문, 숫자, 점, 하이픈, 언더스코어, 한글만 허용
    safe_name = re.sub(r'[^a-zA-Z0-9._\-가-힣]', '_', filename)
    
    # 연속된 점 제거 (../ 공격 방지)
    safe_name = re.sub(r'\.+', '.', safe_name)
    
    # 앞뒤 공백 및 점 제거
    safe_name = safe_name.strip('. ')
    
    # 빈 파일명 처리
    if not safe_name or safe_name == '.':
        safe_name = "unnamed_file"
    
    # 최대 길이 제한 (255자)
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:250] + ext
    
    return safe_name


def generate_unique_filename(original_filename: str) -> str:
    """
    중복되지 않는 고유한 파일명 생성 (UUID 사용)
    
    Args:
        original_filename: 원본 파일명
        
    Returns:
        UUID 기반의 새 파일명 (확장자 포함)
    """
    # 파일명 정제
    safe_filename = sanitize_filename(original_filename)
    ext = Path(safe_filename).suffix.lower()
    
    # 확장자가 없으면 원본에서 추출 시도
    if not ext:
        ext = Path(original_filename).suffix.lower()
    
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


async def validate_image_file_header(file: UploadFile) -> Tuple[str, Optional[str]]:
    """
    업로드된 파일의 헤더 검증 (스트림 방식)
    
    Args:
        file: 업로드 파일
        
    Returns:
        (원본 파일명, 감지된 이미지 타입)
        
    Raises:
        HTTPException: 검증 실패 시
    """
    # 파일명 검증
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일명이 없습니다."
        )
    
    # 확장자 검증
    if not validate_image_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"허용되지 않은 파일 확장자입니다. 허용 확장자: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # 파일 시그니처 읽기 (처음 32 바이트만)
    signature_bytes = await file.read(SIGNATURE_SIZE)
    
    # 빈 파일 체크
    if len(signature_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일입니다."
        )
    
    # 바이트 코드로 이미지 타입 검증
    detected_type = validate_image_by_bytes(signature_bytes)
    if not detected_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효한 이미지 파일이 아닙니다. (바이트 코드 검증 실패)"
        )
    
    # Content-Type 검증 (추가 검증)
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.warning(
            f"Content-Type 불일치: filename={file.filename}, "
            f"content_type={file.content_type}, detected_type={detected_type}"
        )
    
    # 파일 포인터를 처음으로 되돌림
    await file.seek(0)
    
    logger.info(f"이미지 헤더 검증 완료: filename={file.filename}, type={detected_type}")
    
    return file.filename, detected_type


async def save_image_file_stream(
    item_id: int,
    original_filename: str,
    file: UploadFile
) -> Tuple[str, str, int]:
    """
    이미지 파일을 스트림으로 저장 (메모리 효율적)
    
    Args:
        item_id: 아이템 ID
        original_filename: 원본 파일명
        file: UploadFile 객체
        
    Returns:
        (새 파일명, 이미지 경로, 파일 크기)
        
    Raises:
        HTTPException: 저장 실패 시
    """
    try:
        # item_id 검증
        validated_item_id = validate_item_id(item_id)
        
        # 업로드 기본 경로
        base_upload_path = get_upload_path()
        base_path = Path(base_upload_path)
        
        # 아이템 ID별 폴더 경로 생성
        item_folder = base_path / str(validated_item_id)
        
        # 경로 검증 (경로 탐색 공격 방지)
        validated_folder = validate_upload_path(item_folder, base_path)
        
        # 폴더 생성
        await asyncio.to_thread(validated_folder.mkdir, parents=True, exist_ok=True)
        
        # 고유한 파일명 생성
        new_filename = generate_unique_filename(original_filename)
        
        # 전체 파일 경로
        file_path = validated_folder / new_filename
        
        # 스트림 방식으로 파일 저장
        total_size = 0
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        
        # 파일을 열고 청크 단위로 쓰기
        with open(file_path, "wb") as f:
            while True:
                # 청크 단위로 읽기 (1MB씩)
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                # 파일 크기 체크
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    # 파일 닫고 삭제
                    f.close()
                    if file_path.exists():
                        file_path.unlink()
                    file_size_mb = total_size / (1024 * 1024)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"파일 크기가 10MB를 초과했습니다. (업로드 파일: {file_size_mb:.2f}MB, 최대: {max_size_mb:.0f}MB)"
                    )
                
                # 청크 쓰기 (블로킹 I/O이지만 짧은 시간)
                await asyncio.to_thread(f.write, chunk)
        
        # DB에 저장할 상대 경로 (base_upload_path 포함)
        relative_path = f"{base_upload_path}/{item_id}/{new_filename}"
        
        logger.info(
            f"이미지 저장 완료 (스트림): item_id={item_id}, "
            f"original={original_filename}, new={new_filename}, "
            f"size={total_size / (1024*1024):.2f}MB, path={relative_path}"
        )
        
        return new_filename, relative_path, total_size
        
    except HTTPException:
        raise
    except Exception as e:
        # 실패 시 파일 삭제
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        logger.error(f"이미지 저장 실패: item_id={item_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 저장 중 오류가 발생했습니다: {str(e)}"
        )


async def upload_images(
    item_id: int,
    files: List[UploadFile]
) -> List[Tuple[str, str, str]]:
    """
    다중 이미지 업로드 및 저장 (스트림 방식)
    
    Args:
        item_id: 아이템 ID
        files: 업로드 파일 목록
        
    Returns:
        [(원본 파일명, 새 파일명, 이미지 경로), ...] 리스트
        
    Raises:
        HTTPException: 검증 또는 저장 실패 시
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="업로드할 파일이 없습니다."
        )
    
    if len(files) > 10:  # 최대 10개 제한
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="한 번에 최대 10개의 이미지만 업로드할 수 있습니다."
        )
    
    result = []
    total_uploaded_size = 0
    
    for idx, file in enumerate(files, 1):
        logger.info(f"이미지 업로드 시작 ({idx}/{len(files)}): filename={file.filename}")
        
        # 1. 이미지 헤더 검증 (스트림 시작 전)
        original_filename, detected_type = await validate_image_file_header(file)
        
        # 2. 스트림 방식으로 파일 저장
        new_filename, image_path, file_size = await save_image_file_stream(
            item_id, original_filename, file
        )
        
        total_uploaded_size += file_size
        result.append((original_filename, new_filename, image_path))
        
        logger.info(
            f"이미지 업로드 완료 ({idx}/{len(files)}): "
            f"original={original_filename}, size={file_size / (1024*1024):.2f}MB"
        )
    
    logger.info(
        f"✅ 다중 이미지 업로드 완료: item_id={item_id}, count={len(result)}, "
        f"total_size={total_uploaded_size / (1024*1024):.2f}MB"
    )
    
    return result


def delete_image_file(image_path: str) -> bool:
    """
    이미지 파일 삭제
    
    Args:
        image_path: 이미지 경로
        
    Returns:
        삭제 성공 여부
    """
    try:
        file_path = Path(image_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"이미지 삭제 완료: path={image_path}")
            return True
        else:
            logger.warning(f"이미지 파일이 존재하지 않음: path={image_path}")
            return False
    except Exception as e:
        logger.error(f"이미지 삭제 실패: path={image_path}, error={str(e)}")
        return False


def _delete_folder_sync(item_folder: Path) -> int:
    """동기 폴더 삭제 (스레드 풀에서 실행)"""
    deleted_count = 0
    for file_path in item_folder.iterdir():
        if file_path.is_file():
            file_path.unlink()
            deleted_count += 1
    item_folder.rmdir()
    return deleted_count


async def delete_item_images_folder(item_id: int) -> bool:
    """
    아이템 ID 폴더 내의 모든 이미지 파일 삭제 (비동기)
    
    Args:
        item_id: 아이템 ID
        
    Returns:
        삭제 성공 여부
    """
    try:
        base_upload_path = get_upload_path()
        item_folder = Path(base_upload_path) / str(item_id)
        
        # 폴더 존재 확인 (동기이지만 빠름)
        if not item_folder.exists():
            logger.info(f"삭제할 폴더가 없음: item_id={item_id}")
            return True
        
        # 폴더 삭제 (스레드 풀에서 실행)
        deleted_count = await asyncio.to_thread(_delete_folder_sync, item_folder)
        
        logger.info(f"아이템 폴더 삭제 완료: item_id={item_id}, deleted_files={deleted_count}")
        return True
        
    except Exception as e:
        logger.error(f"아이템 폴더 삭제 실패: item_id={item_id}, error={str(e)}")
        return False

