import logging
import re
import asyncio
from typing import Any, Dict, Optional, List

from src.core.config import BACKBONE_CONFIDENCE, TRAINED_CONFIDENCE, VLM_TOP_DETECTION_CANDIDATES, API_SERVER_URL
from src.models.exceptions import (
    DetectionError,
    ModelLoadError,
    ModelNotAvailableError,
    VLMProcessingError,
    build_error_message,
)
from src.models.models import ModelType, YOLOModelManager
from src.models.processors import ImageProcessor, VLMProcessor
from src.schemas import (
    DetectionItem,
    DetectionResponse,
    DetectionCandidate,
    SimilarItem,
    ErrorAnalysisResponse,
    ObjectAnalysisResponse,
    PaperAnalysisResponse,
    NewObjectAnalysisResponse,
)
from src.utils.common import get_timestamp

logger = logging.getLogger(__name__)


class DetectionService:
    """Object Detection Service"""
    
    def __init__(self, model_manager: YOLOModelManager):
        self.model_manager = model_manager
        self._confidence_by_model = {
            ModelType.BACKBONE: BACKBONE_CONFIDENCE,
            ModelType.TRAINED: TRAINED_CONFIDENCE,
        }
    
    def detect_objects(
        self,
        image_bytes: bytes,
        model_type: str = ModelType.BACKBONE.value,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Perform object detection"""
        requested_type = ModelType.from_value(model_type)
        try:
            image = ImageProcessor.process_image(image_bytes)
        except ValueError as exc:
            message = build_error_message("Image decoding failed", str(exc))
            logger.error(message)
            raise DetectionError(message, retryable=False) from exc

        try:

            try:
                self.model_manager.ensure_loaded(requested_type)
                model, model_name = self.model_manager.get_model(requested_type)
                effective_type = requested_type
            except (ModelLoadError, ModelNotAvailableError) as exc:
                if requested_type is ModelType.TRAINED:
                    logger.warning(
                        "Trained model unavailable, falling back to backbone: %s", exc
                    )
                    self.model_manager.ensure_loaded(ModelType.BACKBONE)
                    model, model_name = self.model_manager.get_model(ModelType.BACKBONE)
                    effective_type = ModelType.BACKBONE
                else:
                    raise DetectionError(
                        build_error_message("Model not available", str(exc)),
                        retryable=False,
                    ) from exc

            conf_threshold = confidence
            if conf_threshold is None:
                conf_threshold = self._confidence_by_model.get(
                    effective_type, TRAINED_CONFIDENCE
                )

            try:
                results = model.predict(image, verbose=False, conf=conf_threshold)
            except Exception as exc:
                raise DetectionError(
                    build_error_message("YOLO prediction failed", str(exc))
                ) from exc

            detections = ImageProcessor.parse_detections(results)
            
            return DetectionResponse(
                success=True,
                detections=[DetectionItem(**det) for det in detections],
                total_detections=len(detections),
                model=model_name,
                model_type=effective_type.value,
                timestamp=get_timestamp()
            ).dict()
            
        except DetectionError:
            raise
        except Exception as exc:
            message = build_error_message("Detection failed", str(exc))
            logger.error(message)
            raise DetectionError(message) from exc


class IntegratedAnalysisService:
    """VLM + YOLO Integrated Analysis Service"""
    
    def __init__(self, vlm_processor: VLMProcessor, detection_service: DetectionService, api_url: Optional[str] = None):
        self.vlm_processor = vlm_processor
        self.detection_service = detection_service
        self.api_url = (api_url or API_SERVER_URL).rstrip("/")
    
    @staticmethod
    def _build_detection_message(detections: list, vlm_count: int, yolo_count: int) -> str:
        """Build detection message from results"""
        if not detections:
            return "No objects detected"
        
        message_parts = [f"{det['class_name']} (confidence: {det['confidence']:.1%})" 
                        for det in detections]
        message = f"Detected objects: {', '.join(message_parts)}"
        return f"{message} | VLM predicted: {vlm_count}, YOLO detected: {yolo_count}"
    
    @staticmethod
    def _build_document_message(description: str, text_content: str) -> str:
        """Build document message from OCR results"""
        if text_content:
            truncated = text_content[:100] + ('...' if len(text_content) > 100 else '')
            return f"Document: {description} | OCR text: {truncated}"
        return f"Document detected: {description} | Text extraction failed"
    
    @staticmethod
    def _extract_keywords(text: str, min_length_en: int = 3, min_length_ko: int = 2) -> tuple[list[str], list[str]]:
        """
        텍스트에서 영어/한국어 키워드 추출
        
        Args:
            text: 추출할 텍스트
            min_length_en: 영어 키워드 최소 길이
            min_length_ko: 한국어 키워드 최소 길이
            
        Returns:
            (영어 키워드 리스트, 한국어 키워드 리스트)
        """
        if not text:
            return [], []
        
        text_lower = text.lower()
        # 영어 불용어 제거
        stopwords = {'the', 'and', 'with', 'from', 'that', 'this', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had'}
        # 영어 키워드 추출 (최소 길이 이상만)
        keywords_en = [w for w in re.findall(rf'\b[a-zA-Z]{{{min_length_en},}}\b', text_lower) 
                       if w not in stopwords]
        # 한국어 키워드 추출 (최소 길이 이상만)
        keywords_ko = re.findall(rf'[가-힣]{{{min_length_ko},}}', text)
        
        return keywords_en, keywords_ko
    
    def _find_similar_items(self, vlm_description: str, detected_item_name: str, top_k: int = 5, vlm_description_ko: str = "") -> List[SimilarItem]:
        """
        DB 2차 검증: VLM 특징과 DB description 비교하여 유사 품목 찾기
        
        Args:
            vlm_description: VLM이 생성한 특징 설명
            detected_item_name: YOLO가 탐지한 물품명 (예: "sprocket")
            top_k: 반환할 유사 품목 개수
            
        Returns:
            유사 품목 목록 (SimilarItem 리스트)
        """
        try:
            # VLM description 키워드 추출 (영어 + 한국어)
            vlm_keywords_en, vlm_keywords_ko = self._extract_keywords(vlm_description)
            # 한국어 번역본이 있으면 추가
            if vlm_description_ko:
                ko_en, ko_ko = self._extract_keywords(vlm_description_ko)
                vlm_keywords_ko.extend(ko_ko)
            
            # 검색에 사용할 키워드 (상위 5-10개만, 가장 중요한 키워드만)
            search_keywords = (vlm_keywords_en[:5] + vlm_keywords_ko[:5])[:10]
            
            logger.info("VLM keywords extracted: EN=%d (%s), KO=%d (%s), search_keywords=%s", 
                       len(vlm_keywords_en), vlm_keywords_en[:5], 
                       len(vlm_keywords_ko), vlm_keywords_ko[:5],
                       search_keywords[:10])
            
            if not search_keywords:
                logger.warning("No keywords extracted from VLM description! vlm_description='%s', vlm_description_ko='%s'", 
                             vlm_description[:100] if vlm_description else "empty",
                             vlm_description_ko[:100] if vlm_description_ko else "empty")
                return []
            
            # 키워드로 DB에서 직접 유사한 Item만 조회 (HTTP API 대신 직접 DB 접근)
            items = []
            try:
                from src.common.mariadb.database import SessionLocal, engine
                from src.common.mariadb.models import Item
                from sqlalchemy import select, or_
                
                if not SessionLocal or not engine:
                    logger.warning("Database not available, skipping similarity search")
                    return []
                
                # 비동기 함수를 동기적으로 실행
                async def fetch_items_async():
                    async with SessionLocal() as session:
                        # description에 키워드가 포함된 Item만 조회
                        keyword_filters = []
                        for keyword in search_keywords:
                            if keyword:
                                keyword_filters.append(Item.description.like(f"%{keyword}%"))
                        
                        if not keyword_filters:
                            return []
                        
                        query = select(Item).where(or_(*keyword_filters)).limit(100)
                        result = await session.execute(query)
                        db_items = result.scalars().all()
                        
                        # dict로 변환
                        items_list = []
                        for item in db_items:
                            items_list.append({
                                "id": item.id,
                                "itemName": item.itemName,
                                "description": item.description or ""
                            })
                        return items_list
                
                # 비동기 함수 실행 (이벤트 루프가 이미 실행 중일 수 있으므로 새 루프 생성)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 이미 실행 중인 이벤트 루프가 있으면 새 스레드에서 새 루프로 실행
                        import concurrent.futures
                        def run_in_new_loop():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(fetch_items_async())
                            finally:
                                new_loop.close()
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_in_new_loop)
                            items = future.result(timeout=5)
                    else:
                        items = loop.run_until_complete(fetch_items_async())
                except RuntimeError:
                    # 이벤트 루프가 없으면 새로 생성
                    items = asyncio.run(fetch_items_async())
                
                logger.info("Fetched %d items matching keywords from database (direct DB access)", len(items))
                
            except Exception as e:
                logger.warning("Failed to fetch items from database: %s", e, exc_info=True)
                return []
            
            if not items:
                logger.debug("No items found matching keywords")
                return []
            
            # 유사도 계산
            similar_items = []
            
            # 전체 키워드 집합 (유사도 계산용)
            vlm_keywords = set(vlm_keywords_en) | set(vlm_keywords_ko)
            
            if not vlm_keywords:
                logger.warning("No VLM keywords extracted for similarity comparison")
                return []
            
            items_with_description = 0
            items_processed = 0
            
            for item in items:
                item_name = (item.get("itemName") or "").strip()
                item_id = item.get("id")
                db_description = (item.get("description") or "").strip()
                
                if not item_id:
                    continue
                
                # DB description이 없으면 스킵 (하지만 로그는 남김)
                if not db_description:
                    logger.debug("Item '%s' (id=%d) has no description, skipping", item_name, item_id)
                    continue
                
                items_with_description += 1
                logger.debug("Processing item '%s' (id=%d) with description: '%s'", item_name, item_id, db_description[:50])
                
                # DB description 키워드 추출 (영어 + 한국어)
                db_keywords_en, db_keywords_ko = self._extract_keywords(db_description, min_length_en=1, min_length_ko=1)
                # 전체 키워드 집합
                db_keywords = set(db_keywords_en) | set(db_keywords_ko)
                
                # 키워드 교집합 계산 (Jaccard 유사도)
                similarity = 0.0
                if vlm_keywords and db_keywords:
                    intersection = vlm_keywords & db_keywords
                    union = vlm_keywords | db_keywords
                    if union:
                        similarity = len(intersection) / len(union)
                    logger.debug("Item '%s': keyword similarity=%.3f (intersection=%d, union=%d)", 
                               item_name, similarity, len(intersection), len(union))
                
                # 추가: 부분 문자열 매칭 (한국어 설명과 DB description 간)
                # VLM description의 주요 단어가 DB description에 포함되는지 확인
                if vlm_description_ko and db_description:
                    # 주요 단어 추출 (2글자 이상)
                    vlm_words = [w for w in re.findall(r'[가-힣]{2,}', vlm_description_ko)]
                    db_words = [w for w in re.findall(r'[가-힣]{2,}', db_description)]
                    if vlm_words and db_words:
                        # 공통 단어가 있으면 보너스 점수
                        common_words = set(vlm_words) & set(db_words)
                        if common_words:
                            bonus = len(common_words) * 0.1
                            similarity += bonus
                            similarity = min(similarity, 1.0)
                            logger.debug("Item '%s': Korean word match bonus=%.3f (common_words=%s)", 
                                       item_name, bonus, list(common_words)[:3])
                
                # 추가: 영어 description과 영어 description 직접 비교
                # VLM 원본 영어 description과 DB 영어 description 비교
                if vlm_description and db_description:
                    # 영어 단어 추출
                    vlm_en_words = set(re.findall(r'\b[a-zA-Z]+\b', vlm_description.lower()))
                    db_en_words = set(re.findall(r'\b[a-zA-Z]+\b', db_description.lower()))
                    if vlm_en_words and db_en_words:
                        en_intersection = vlm_en_words & db_en_words
                        en_union = vlm_en_words | db_en_words
                        if en_union:
                            en_similarity = len(en_intersection) / len(en_union)
                            # 영어 매칭이 있으면 더 높은 가중치
                            if en_similarity > similarity:
                                similarity = en_similarity
                            logger.debug("Item '%s': English word similarity=%.3f (intersection=%s)", 
                                       item_name, en_similarity, list(en_intersection)[:5])
                
                # 추가: 부분 문자열 포함 여부 확인 (더 관대한 매칭)
                # VLM description에 DB description의 주요 단어가 포함되는지
                if vlm_description and db_description:
                    db_main_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', db_description.lower())]
                    for word in db_main_words:
                        if word in vlm_description.lower():
                            similarity += 0.15
                            logger.debug("Item '%s': Found DB word '%s' in VLM description", item_name, word)
                            break
                
                # 한국어도 동일하게
                if vlm_description_ko and db_description:
                    db_ko_words = [w for w in re.findall(r'[가-힣]{2,}', db_description)]
                    for word in db_ko_words:
                        if word in vlm_description_ko:
                            similarity += 0.15
                            logger.debug("Item '%s': Found DB Korean word '%s' in VLM description", item_name, word)
                            break
                
                similarity = min(similarity, 1.0)  # 최대 1.0으로 제한
                
                # 탐지된 물품명과 DB itemName 부분 일치 확인 (보너스 점수)
                if detected_item_name.lower() in item_name.lower() or item_name.lower() in detected_item_name.lower():
                    similarity += 0.2  # 보너스 점수
                    similarity = min(similarity, 1.0)  # 최대 1.0으로 제한
                
                items_processed += 1
                
                # 유사도가 0.05 이상인 경우만 추가 (임계값 완화)
                if similarity >= 0.05:
                    similar_items.append({
                        "itemName": item_name,
                        "itemId": item_id,
                        "score": similarity,
                        "description": db_description
                    })
                    logger.info("Similar item found: '%s' (score=%.3f, item_id=%d)", item_name, similarity, item_id)
                else:
                    logger.debug("Item '%s' similarity too low: %.3f < 0.05", item_name, similarity)
            
            # 유사도 순으로 정렬 (내림차순)
            similar_items.sort(key=lambda x: x["score"], reverse=True)
            
            # 상위 top_k개만 반환
            top_items = similar_items[:top_k]
            
            # SimilarItem 객체로 변환
            result = [
                SimilarItem(
                    itemName=item["itemName"],
                    itemId=item["itemId"],
                    score=item["score"],
                    description=item.get("description")
                )
                for item in top_items
            ]
            
            logger.info("DB 2차 검증 완료: detected='%s', found %d similar items (from %d total items, %d with description, %d processed)", 
                       detected_item_name, len(result), len(items), items_with_description, items_processed)
            if result:
                logger.info("Top similar items: %s", 
                           ", ".join([f"{item.itemName}({item.score:.2f})" for item in result[:3]]))
            else:
                logger.warning("No similar items found! Check if DB descriptions exist and match VLM description keywords.")
            return result
            
        except Exception as e:
            logger.error("Error in similarity search: %s", e, exc_info=True)
            return []
    
    def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            image = ImageProcessor.process_image(image_bytes)
            yolo_result = self._run_detection_with_fallback(image_bytes)

            hint = ""
            detections = yolo_result.get("detections") or []
            has_sprocket = False
            if detections:
                counts = {}
                for detection in detections:
                    # DetectionItem 객체 또는 dict 모두 처리
                    if isinstance(detection, dict):
                        label = detection.get("class_name", "unknown")
                    else:
                        label = getattr(detection, "class_name", "unknown")
                    counts[label] = counts.get(label, 0) + 1
                    # YOLO가 이제 sprocket, sprocket_3, sprocket_db30, sprocket_z36 등 여러 클래스를 반환할 수 있음
                    if "sprocket" in label.lower():
                        has_sprocket = True
                parts = ["{0} {1}".format(label, count) for label, count in counts.items()]
                total = yolo_result.get("total_detections", len(detections))
                hint = "YOLO detected {0} objects: {1}.".format(total, ", ".join(parts))
                # sprocket 탐지 시 세부 타입 구분 및 상세 설명 강조
                if has_sprocket:
                    # YOLO가 이미 구체적인 타입(sprocket_3, sprocket_db30, sprocket_z36 등)을 반환했음
                    # VLM은 타입 구분이 아닌 추가 상세 정보(물리적 특성, 마킹, 재질 등)에 집중
                    hint += " YOLO has already identified the sprocket types. Please provide additional details: (1) Physical dimensions (diameter, thickness, size), (2) Material and surface finish, (3) Any visible markings, part numbers, or labels, (4) Distinguishing features, (5) Condition assessment."
                else:
                    # YOLO가 다른 객체는 탐지했지만 sprocket은 탐지하지 못한 경우
                    # VLM에게 sprocket이 있는지 확인하고, 있다면 타입까지 구분하도록 요청
                    hint += " IMPORTANT: YOLO may have missed some objects. If you see sprockets (gear-like objects with teeth) in the image, identify the specific type (e.g., sprocket_z36 for 36 teeth, sprocket_z40 for 40 teeth) and include them in your count and description with detailed characteristics (tooth count, diameter, material, markings, condition)."
            else:
                # detections가 비어있을 때: 문서인지 먼저 확인하고, 아니면 객체 분석
                # YOLO가 탐지 실패한 경우에도 sprocket이 있을 수 있으므로 VLM에게 확인 요청
                hint = "YOLO detected no objects. First check if this is a document/paper (contains text, labels, forms). If it's a document, extract text. If it's a physical object, carefully analyze the image. IMPORTANT: If you see sprockets (gear-like objects with teeth), identify the specific type (e.g., sprocket_z36 for 36 teeth, sprocket_z40 for 40 teeth) and provide detailed characteristics (tooth count, diameter, material, markings, condition). Count and describe all visible objects with their characteristics (shape, color, size, material, purpose, distinguishing features) in detail."

            vlm_result = self.vlm_processor.analyze_image(image, hint=hint)
            
            if vlm_result.get("type") == "error":
                detail = vlm_result.get("message", "Unknown error")
                raise VLMProcessingError(detail)
            
            # VLM description 한국어 번역 추가 (서버 측에서도 수행)
            vlm_description = vlm_result.get("description", "")
            if vlm_description and not vlm_result.get("description_ko"):
                try:
                    import requests as req
                    params = {"client": "gtx", "sl": "auto", "tl": "ko", "dt": "t", "q": vlm_description}
                    translate_response = req.get(
                        "https://translate.googleapis.com/translate_a/single",
                        params=params,
                        timeout=5,
                    )
                    if translate_response.status_code == 200:
                        translated = "".join(segment[0] for segment in translate_response.json()[0])
                        vlm_result["description_ko"] = translated.strip() or vlm_description
                        logger.debug("VLM description translated to Korean: %s", vlm_result["description_ko"][:50])
                except Exception as e:
                    logger.warning("Failed to translate VLM description to Korean: %s", e)
                    # 번역 실패해도 계속 진행
            
            analysis_type = vlm_result.get("type", "unknown")
            
            logger.info("Analysis type: %s", analysis_type)
            
            if analysis_type == "object":
                vlm_count = int(vlm_result.get("count", 0))
                yolo_count = yolo_result.get("total_detections", len(detections))
                logger.info("Object analysis: VLM=%s, YOLO=%s", vlm_count, yolo_count)
                message = self._build_detection_message(
                    yolo_result["detections"], vlm_count, yolo_count
                )

                # YOLO와 VLM 수량 차이 보완: 둘 중 더 큰 값을 사용
                # 둘 다 0이면 0, 하나만 0이면 0이 아닌 값, 둘 다 0이 아니면 더 큰 값
                if vlm_count == 0 and yolo_count == 0:
                    effective_count = 0
                elif vlm_count == 0:
                    effective_count = yolo_count
                elif yolo_count == 0:
                    effective_count = vlm_count
                else:
                    # 둘 다 0이 아니면 더 큰 값 사용
                    effective_count = max(vlm_count, yolo_count)

                # DB 2차 검증: 유사 품목 찾기
                # VLM description 원본(영어) 우선 사용, 없으면 한국어 번역본 사용
                vlm_description = vlm_result.get("description", "")  # 원본 영어
                vlm_description_ko = vlm_result.get("description_ko", "")  # 한국어 번역
                detected_item_name = ""
                if detections:
                    # 가장 많이 탐지된 항목 사용
                    counts = {}
                    for detection in detections:
                        if isinstance(detection, dict):
                            label = detection.get("class_name", "unknown")
                        else:
                            label = getattr(detection, "class_name", "unknown")
                        counts[label] = counts.get(label, 0) + 1
                    if counts:
                        detected_item_name = next(iter(counts.keys()))
                
                # detected_item_name이 없으면 "new item"으로 설정 (YOLO 탐지 실패 시)
                if not detected_item_name:
                    detected_item_name = "new item"
                
                logger.info("DB 2차 검증 시작: detected_item_name='%s', vlm_description='%s', vlm_description_ko='%s'", 
                           detected_item_name, 
                           vlm_description[:100] if vlm_description else "empty",
                           vlm_description_ko[:100] if vlm_description_ko else "empty")
                
                similar_items = []
                # 영어 또는 한국어 description이 있으면 검증 수행
                if vlm_description or vlm_description_ko:
                    # 영어와 한국어 모두 전달하여 양쪽 모두 비교
                    similar_items = self._find_similar_items(
                        vlm_description or vlm_description_ko, 
                        detected_item_name, 
                        top_k=5,
                        vlm_description_ko=vlm_description_ko
                    )
                    logger.info("Found %d similar items for '%s'", len(similar_items), detected_item_name)
                else:
                    logger.warning("DB 2차 검증 스킵: vlm_description=%s, vlm_description_ko=%s", 
                                 bool(vlm_description), bool(vlm_description_ko))

                return ObjectAnalysisResponse(
                    success=True,
                    vlm_result=vlm_result,
                    yolo_result=yolo_result,
                    count=effective_count,
                    vlm_count=vlm_count,
                    message=message,
                    confirmation_prompt=f"Are {yolo_count} detected objects correct? (YES/NO)",
                    similar_items=similar_items
                ).dict()
                
            elif analysis_type == "paper":
                text_content = vlm_result.get("text_content", "")
                description = vlm_result.get("description", "Document")
                logger.info("Paper analysis: %s chars extracted", len(text_content))
                
                return PaperAnalysisResponse(
                    success=True,
                    vlm_result=vlm_result,
                    message=self._build_document_message(description, text_content),
                    extracted_text=text_content,
                    input_prompt="Please input item name and quantity from document",
                    confirmation_prompt="Is the information correct? (YES/NO)"
                ).dict()
            
            else:
                # unknown 타입을 new_object로 처리
                logger.info("Unknown analysis type treated as new_object: %s", analysis_type)
                
                # YOLO detection 결과에서 상위 N개 추출 (신뢰도 기준)
                detection_candidates = []
                if detections:
                    # 신뢰도 기준으로 정렬 (DetectionItem 객체 또는 dict 모두 처리)
                    def get_confidence(det):
                        if isinstance(det, dict):
                            return det.get("confidence", 0.0)
                        return getattr(det, "confidence", 0.0)
                    
                    def get_class_name(det):
                        if isinstance(det, dict):
                            return det.get("class_name", "unknown")
                        return getattr(det, "class_name", "unknown")
                    
                    def get_bbox(det):
                        if isinstance(det, dict):
                            return det.get("bbox", [])
                        return getattr(det, "bbox", [])
                    
                    sorted_detections = sorted(
                        detections, 
                        key=get_confidence, 
                        reverse=True
                    )
                    # 상위 N개만 추출 (config에서 설정)
                    top_detections = sorted_detections[:VLM_TOP_DETECTION_CANDIDATES]
                    detection_candidates = [
                        DetectionCandidate(
                            class_name=get_class_name(det),
                            confidence=get_confidence(det),
                            bbox=get_bbox(det)
                        )
                        for det in top_detections
                    ]
                
                description = vlm_result.get("description", "")
                if not description:
                    description = "새로운 객체로 판단되었습니다. 상세 정보를 입력해주세요."
                
                return NewObjectAnalysisResponse(
                    success=True,
                    vlm_result=vlm_result,
                    yolo_result=yolo_result if detections else None,
                    detection_candidates=detection_candidates,
                    message=f"새로운 객체로 감지되었습니다. 유사한 품목을 찾기 위해 상위 {len(detection_candidates)}개의 탐지 결과를 제공합니다.",
                    description=description
                ).dict()
        
        except Exception as e:
            logger.error("Integrated analysis failed: %s", e)
            return ErrorAnalysisResponse(error=str(e)).dict()

    def _run_detection_with_fallback(self, image_bytes: bytes) -> Dict[str, Any]:
        """Run detection using trained model first, falling back to backbone on failure."""
        try:
            return self.detection_service.detect_objects(
                image_bytes, model_type=ModelType.TRAINED.value
            )
        except DetectionError as exc:
            if not getattr(exc, "retryable", True):
                raise
            logger.warning("Falling back to backbone detection: %s", exc)
            return self.detection_service.detect_objects(
                image_bytes, model_type=ModelType.BACKBONE.value
            )
