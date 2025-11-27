import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import requests

from src.core.config import (
    API_SERVER_URL,
    API_TIMEOUT,
    DETECTION_UPLOAD_ENDPOINT,
    ITEM_API_PAGE_SIZE,
    ITEM_ID_DEFAULT,
    OUTPUT_DIR,
)
from src.utils.common import get_timestamp


def _warn(message: str):
    print("Warning: " + message)


def _translate_to_korean(text: str) -> str:
    if not text:
        return text
    try:
        params = {"client": "gtx", "sl": "auto", "tl": "ko", "dt": "t", "q": text}
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params=params,
            timeout=5,
        )
        if response.status_code == 200:
            translated = "".join(segment[0] for segment in response.json()[0])
            return translated.strip() or text
    except Exception as exc:
        _warn("Translation failed: " + str(exc))
    return text


class APIClient:
    def __init__(self, api_url: Optional[str] = None, timeout: Optional[int] = None, output_dir: Optional[str] = None, auth_token: str = ""):
        self.api_url = (api_url or API_SERVER_URL).rstrip("/")
        self.timeout = timeout or API_TIMEOUT
        self.output_dir = output_dir or OUTPUT_DIR
        self.auth_token = auth_token.strip()
        self.detection_endpoint = DETECTION_UPLOAD_ENDPOINT
        self._item_catalog: Optional[Dict[str, int]] = None

    # ------------------------------------------------------------------ #
    # Public API

    def analyze_integrated(self, img, auto_save: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
        try:
            # 이미지 저장 (output 폴더에 저장)
            timestamp = get_timestamp().replace(":", "").replace("-", "").replace(".", "")[:18]
            result_dir = os.path.join(self.output_dir, "integrated_" + timestamp)
            os.makedirs(result_dir, exist_ok=True)
            image_path = os.path.join(result_dir, "captured_image.jpg")
            cv2.imwrite(image_path, img)

            _, buffer = cv2.imencode(".jpg", img)
            response = requests.post(
                self.api_url + "/analyze",
                files={"file": ("image.jpg", buffer.tobytes(), "image/jpeg")},
                timeout=self.timeout,
            )

            if response.status_code != 200:
                _warn("API error (" + str(response.status_code) + "): " + response.text)
                return None, None

            result = response.json()
            self._display_result(result)
            context = {"result_dir": result_dir, "image_path": image_path}
            if auto_save:
                self._save_result(result, img, result_dir)
            return result, context

        except requests.exceptions.ConnectionError:
            print("ERROR: Cannot connect to API server at " + self.api_url)
            print("Solution: Start API server with 'uvicorn app:app --reload'")
        except requests.exceptions.Timeout:
            print("ERROR: Request timeout (" + str(self.timeout) + "s) - VLM may be warming up")
            print("Solution: Wait for VLM warmup to complete and try again")
        except Exception as exc:
            print("ERROR: " + str(exc))
        return None, None

    def _localize_vlm_result(self, result: Dict[str, Any]):
        vlm_result = result.get("vlm_result")
        if isinstance(vlm_result, dict):
            description = vlm_result.get("description", "")
            if description:
                vlm_result.setdefault("description_en", description)
                translated = _translate_to_korean(description)
                if translated:
                    vlm_result["description_ko"] = translated

    def prepare_for_display(self, result: Dict[str, Any]):
        if result:
            self._localize_vlm_result(result)

    def finalize_result(self, result: Dict[str, Any], img, context: Dict[str, str], confirmed: bool):
        if not result:
            return

        result["confirmation_response"] = bool(confirmed)
        result["confirmation_answer"] = "YES" if confirmed else "NO"

        self._localize_vlm_result(result)

        # object 타입과 paper 타입 모두 업로드
        analysis_type = result.get("analysis_type") or result.get("vlm_result", {}).get("type", "unknown")
        if analysis_type in ("object", "paper"):
            upload_meta = self._submit_detection_upload(result, context, confirmed)
            if upload_meta:
                result["detection_upload"] = upload_meta
                # 업로드된 item_id를 result에 포함 (나중에 detection list 조회 시 사용)
                if upload_meta.get("item_id"):
                    result["uploaded_item_id"] = upload_meta.get("item_id")
                    print(f"Detection upload completed with item_id: {upload_meta.get('item_id')}")

        # 파일 저장 (output 폴더에 저장)
        result_dir = context.get("result_dir")
        if result_dir:
            self._save_result(result, img, result_dir)
            print("User confirmation saved: " + ("YES" if confirmed else "NO"))
        else:
            _warn("Result directory missing; unable to persist analysis.")
        
        print("User confirmation: " + ("YES" if confirmed else "NO"))

    # ------------------------------------------------------------------ #
    # Helpers

    def _display_result(self, result: Dict[str, Any]):
        print("\n" + "=" * 70)
        print("Analysis Result Summary")
        print("=" * 70)
        print("Success:", result.get("success"))
        print("Type:", result.get("type", result.get("analysis_type")))

        vlm = result.get("vlm_result") or {}
        if vlm:
            print("\nVLM Analysis:")
            print("   Type:", vlm.get("type"))
            print("   Count:", vlm.get("count", 0))
            print("   Description:", vlm.get("description", "N/A"))

        if result.get("analysis_type") == "object":
            detections = result.get("yolo_result", {}).get("detections") or []
            print("\nYOLO Detection:")
            print("   Count:", result.get("count", 0))
            if detections:
                print("   Objects:")
                for index, det in enumerate(detections[:5], start=1):
                    label = det.get("class_name", "unknown")
                    confidence = det.get("confidence", 0.0) * 100.0
                    print("      " + str(index) + ". " + label + " (" + str(int(confidence)) + "%)")
        else:
            text = result.get("extracted_text", "")
            print("\nPaper Analysis:")
            if text:
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                print("   OCR text:")
                for line in lines[:3]:
                    print("      " + line)
                if len(lines) > 3:
                    print("      ...")
            else:
                print("   OCR: extraction failed")

        print("\nMessage:", result.get("message"))
        print("Confirmation:", result.get("confirmation_prompt", "N/A"))
        print("\nNext action:", result.get("next_action"))

    def _save_result(self, result: Dict[str, Any], img, result_dir: str):
        import json

        json_path = os.path.join(result_dir, "analysis_result.json")
        with open(json_path, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)

        if result.get("analysis_type") == "object":
            detections = result.get("yolo_result", {}).get("detections") or []
            if detections:
                from .display import DisplayManager

                display = DisplayManager(create_window=False)
                model_name = result.get("yolo_result", {}).get("model", "Unknown")
                annotated = display.draw_bbox_on_image(
                    img,
                    detections,
                    "Integrated Analysis - " + model_name,
                )
                cv2.imwrite(os.path.join(result_dir, "result_with_bbox.jpg"), annotated)

        print("Results saved in: " + result_dir + "/")

    # ------------------------------------------------------------------ #
    # Detection upload

    def _submit_detection_upload(
        self,
        result: Dict[str, Any],
        context: Dict[str, str],
        confirmed: bool,
    ) -> Optional[Dict[str, Any]]:
        if not self.detection_endpoint:
            _warn("Detection upload skipped: endpoint not configured")
            return {"status": "skipped", "reason": "endpoint_not_configured"}

        print(f"[DEBUG] Detection upload: endpoint={self.detection_endpoint}, confirmed={confirmed}")
        
        payload = self._build_detection_payload(result, context)
        if not payload:
            _warn("Detection upload skipped: payload unavailable (item_id or item_count missing)")
            return {"status": "skipped", "reason": "payload_unavailable"}
        
        print(f"[DEBUG] Detection payload: item_id={payload.get('item_id')}, item_count={payload.get('item_count')}, image_path={payload.get('image_path')}")

        item_id = payload["item_id"]
        
        # /api/web/item/{item_id}로 item 조회 (업로드 전 검증)
        item_info = None
        headers = {}
        if self.auth_token:
            headers["Authorization"] = "Bearer " + self.auth_token
        
        try:
            item_response = requests.get(
                self.api_url + f"/api/web/item/{item_id}",
                headers=headers if headers else None,
                timeout=self.timeout,
            )
            if item_response.status_code == 200:
                item_info = item_response.json()
                _warn(f"Item verified before upload: id={item_id}, name={item_info.get('itemName', 'N/A')}")
            else:
                _warn(f"Item verification failed: item_id={item_id}, status={item_response.status_code}, response={item_response.text}")
                # item 조회 실패해도 업로드는 진행 (서버에서 다시 검증함)
        except requests.exceptions.RequestException as exc:
            _warn(f"Item verification request failed: {exc}")
            # item 조회 실패해도 업로드는 진행 (서버에서 다시 검증함)

        # auth_token이 있으면 헤더에 추가, 없으면 헤더 없이 전송 (선택적 인증)
        if not self.auth_token:
            _warn("Detection upload: No auth token provided, sending without authentication (optional auth)")

        try:
            upload_url = self.api_url + self.detection_endpoint
            print(f"[DEBUG] Sending detection upload to: {upload_url}")
            print(f"[DEBUG] Upload data: item_id={payload['item_id']}, detection_status={'true' if confirmed else 'false'}, item_count={payload['item_count']}, description={payload.get('description', '')[:50]}...")
            
            # 전송 데이터 구성
            upload_data = {
                "item_id": str(payload["item_id"]),
                "detection_status": "true" if confirmed else "false",
                "item_count": str(payload["item_count"]),
            }
            
            # description이 있으면 추가 (GUI에 표시된 값 그대로)
            if payload.get("description"):
                upload_data["description"] = payload["description"]
            
            with open(payload["image_path"], "rb") as stream:
                files = {"file": (os.path.basename(payload["image_path"]), stream, "image/jpeg")}
                response = requests.post(
                    upload_url,
                    data=upload_data,
                    files=files,
                    headers=headers if headers else None,  # 빈 헤더 딕셔너리는 None으로 전달
                    timeout=self.timeout,
                )
                print(f"[DEBUG] Detection upload response: status={response.status_code}")
        except FileNotFoundError:
            _warn("Captured image missing; upload skipped.")
            return {"status": "error", "message": "image_not_found"}
        except requests.exceptions.RequestException as exc:
            _warn("Detection upload request failed: " + str(exc))
            return {"status": "error", "message": str(exc)}

        if response.status_code in (200, 201):
            response_data = response.json()
            detection_result = response_data.get("detection_result", {})
            uploaded_item_id = detection_result.get("itemId")
            
            print("Detection result uploaded to web service.")
            if uploaded_item_id:
                print(f"Uploaded item_id: {uploaded_item_id}")
            
            return {
                "status": "success",
                "http_status": response.status_code,
                "response": response_data,
                "item_id": uploaded_item_id,  # item_id를 반환값에 포함
            }

        _warn("Detection upload failed (" + str(response.status_code) + "): " + response.text)
        return {
            "status": "error",
            "http_status": response.status_code,
            "message": response.text,
        }

    def _build_detection_payload(self, result: Dict[str, Any], context: Dict[str, str]) -> Optional[Dict[str, Any]]:
        image_path = context.get("image_path")
        if not image_path or not os.path.exists(image_path):
            _warn("Detection payload skipped: image path missing.")
            return None

        # 선택한 품목명 확인 (2단계 검증에서 사용자가 선택한 품목)
        selected_item_name = result.get("selected_item_name")
        
        # analysis_type 확인
        analysis_type = result.get("analysis_type") or result.get("vlm_result", {}).get("type", "unknown")
        
        # 선택한 품목명이 있으면 우선 사용 (2단계 검증)
        if selected_item_name:
            item_name = selected_item_name
            print(f"[DEBUG] Using selected item_name from 2nd verification: '{item_name}'")
        # Paper 타입인 경우 물품명을 "ocr"로 설정
        elif analysis_type == "paper":
            item_name = "ocr"
            print("[DEBUG] Paper type: using item_name='ocr'")
        elif analysis_type == "object":
            # Object 타입인 경우: GUI에 표시되는 물품명 결정 (GUI와 동일한 로직)
            detections = result.get("yolo_result", {}).get("detections") or []
            counts: Dict[str, int] = {}
            for detection in detections:
                label = detection.get("class_name", "미확인")
                counts[label] = counts.get(label, 0) + 1
            
            # GUI와 동일하게: 탐지가 있으면 class_name, 없으면 "new item"
            if counts:
                item_name = next(iter(counts.keys()))
            else:
                item_name = "new item"
        else:
            # unknown 타입 등 기타 경우
            item_name = "new item"
            print(f"[DEBUG] Unknown analysis_type='{analysis_type}', using item_name='new item'")
        
        # GUI에 표시된 물품명으로 item_id 찾기 (직접 API 조회)
        print(f"[DEBUG] Looking up item_id for item_name='{item_name}'")
        item_id = self._lookup_item_id_by_name(item_name)
        
        if item_id is None:
            if ITEM_ID_DEFAULT > 0:
                item_id = ITEM_ID_DEFAULT
                _warn(f"Using default item_id: {item_id} (item_name='{item_name}' not found in API)")
                print(f"[DEBUG] Using default item_id: {item_id} for item_name='{item_name}'")
            else:
                _warn(f"Detection upload skipped: unable to resolve item_id for item_name='{item_name}'. ITEM_ID_DEFAULT={ITEM_ID_DEFAULT}")
                print(f"[DEBUG] Detection upload skipped: item_name='{item_name}' not found, ITEM_ID_DEFAULT={ITEM_ID_DEFAULT}")
                return None
        else:
            print(f"[DEBUG] Item found via API lookup: '{item_name}' -> item_id={item_id}")

        count = result.get("count")
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = None
        
        # Paper 타입은 count를 1로 고정 (문서이므로)
        if analysis_type == "paper":
            count = 1  # Paper 타입은 항상 1로 고정
            print("[DEBUG] Paper type: count fixed to 1")
        else:
            # Object 타입인 경우
            if not count or count <= 0:
                count = len(detections) if detections else result.get("vlm_count") or result.get("count", 0)
            if count <= 0:
                _warn(f"Detection upload skipped: item_count is zero. detections={len(detections)}, vlm_count={result.get('vlm_count')}, count={result.get('count')}")
                print(f"[DEBUG] Detection upload skipped: item_count={count}, detections={len(detections)}, result.count={result.get('count')}")
                return None

        # GUI에 표시되는 description 추출 (GUI와 동일한 로직)
        vlm = result.get("vlm_result", {}) or {}
        
        # Paper 타입인 경우: OCR 결과 처리
        if analysis_type == "paper":
            text_content = vlm.get("text_content", "") or ""
            
            # 정형화된 문서인지 확인 (Commission, Mat no, Description 파싱 시도)
            commission = ""
            mat_no = ""
            parsed_description = ""
            
            if text_content:
                for line in text_content.split("\n"):
                    line = line.strip()
                    if line.startswith("Commission:"):
                        commission = line.replace("Commission:", "").strip()
                    elif line.startswith("Mat no:"):
                        mat_no = line.replace("Mat no:", "").strip()
                    elif line.startswith("Description:"):
                        parsed_description = line.replace("Description:", "").strip()
            
            # 정형화된 문서인 경우: 파싱된 정보만 전송
            if commission or mat_no or parsed_description:
                # 파싱된 정보를 포맷팅하여 전송
                parts = []
                if commission:
                    parts.append(f"Commission: {commission}")
                if mat_no:
                    parts.append(f"Mat no: {mat_no}")
                if parsed_description:
                    parts.append(f"Description: {parsed_description}")
                description = "\n".join(parts)
                print("[DEBUG] Paper type: structured document, sending parsed information only")
            else:
                # 비정형화된 문서인 경우: 전체 text_content 전송
                description = text_content
                print("[DEBUG] Paper type: unstructured document, sending full text_content")
        else:
            # Object/Unknown 타입인 경우: 기존 로직 사용
            description = (
                vlm.get("description_ko")
                or vlm.get("description")
                or result.get("message")
                or "No description provided."
            ).strip()
            
            # sprocket인 경우 설명을 더 자세히 표시 (GUI와 동일)
            if item_name and "sprocket" in item_name.lower():
                # description이 짧으면 더 자세한 정보 요청 메시지 추가
                if len(description) < 50:
                    description += " (상세 정보: 이빨 수, 직경, 재질, 마킹 등을 확인하세요)"
            
            # 마지막에 .이 없으면 추가 (GUI와 동일)
            if description and not description.endswith("."):
                description += "."
        
        print(f"[DEBUG] Detection payload built: item_id={item_id}, item_count={count}, image_path={image_path}, description={description[:50]}...")
        return {"image_path": image_path, "item_id": item_id, "item_count": count, "description": description}

    # ------------------------------------------------------------------ #
    # Item catalog

    def _lookup_item_id_by_name(self, item_name: str) -> Optional[int]:
        """
        직접 API로 item 이름으로 item_id 조회 (catalog가 비어있을 때 사용)
        """
        headers = {}
        if self.auth_token:
            headers["Authorization"] = "Bearer " + self.auth_token
        
        try:
            # 품목 목록 조회 API로 검색
            response = requests.get(
                self.api_url + "/api/web/item/",
                headers=headers if headers else None,
                params={"page": 1, "page_size": 100, "search": item_name},
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                payload = response.json()
                items = payload.get("items") or []
                item_name_lower = item_name.strip().strip('"').strip("'").lower()
                
                # 정확한 이름으로 먼저 검색 (따옴표 제거)
                for item in items:
                    db_item_name = (item.get("itemName") or "").strip().strip('"').strip("'").lower()
                    if db_item_name == item_name_lower:
                        item_id = item.get("id")
                        if item_id:
                            print(f"[DEBUG] Direct API lookup found: '{item_name}' -> item_id={item_id}")
                            return item_id
                
                # 부분 일치로 검색 (따옴표 제거)
                for item in items:
                    db_item_name = (item.get("itemName") or "").strip().strip('"').strip("'").lower()
                    if item_name_lower in db_item_name or db_item_name in item_name_lower:
                        item_id = item.get("id")
                        if item_id:
                            print(f"[DEBUG] Direct API lookup found (partial): '{item_name}' -> '{item.get('itemName')}' (id={item_id})")
                            return item_id
            else:
                print(f"[DEBUG] Direct API lookup failed: status={response.status_code}")
        except Exception as exc:
            print(f"[DEBUG] Direct API lookup error: {exc}")
        
        return None

    def _resolve_item_id(self, detections: List[Dict[str, Any]]) -> Optional[int]:
        def lookup() -> Optional[int]:
            catalog = self._get_item_catalog()
            for detection in detections:
                name = (detection.get("class_name") or "").strip().lower()
                if name and name in catalog:
                    return catalog[name]
            return None

        item_id = lookup()
        if item_id is not None:
            return item_id

        self._get_item_catalog(force_refresh=True)
        item_id = lookup()
        if item_id is not None:
            return item_id

        if ITEM_ID_DEFAULT > 0:
            return ITEM_ID_DEFAULT
        return None

    def _get_item_catalog(self, force_refresh: bool = False) -> Dict[str, int]:
        if self._item_catalog is None or force_refresh:
            self._item_catalog = self._fetch_item_catalog()
        return self._item_catalog or {}

    def _fetch_item_catalog(self) -> Dict[str, int]:
        # auth_token이 없어도 catalog 조회 시도 (선택적 인증)
        headers = {}
        if self.auth_token:
            headers["Authorization"] = "Bearer " + self.auth_token
        else:
            print("[DEBUG] Fetching item catalog without auth token (optional auth)")
        page = 1
        catalog: Dict[str, int] = {}

        while page <= 50:
            try:
                response = requests.get(
                    self.api_url + "/api/web/item/",
                    headers=headers,
                    params={"page": page, "page_size": ITEM_API_PAGE_SIZE},
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as exc:
                _warn("Item lookup failed (" + str(exc) + ").")
                break

            if response.status_code != 200:
                _warn("Item lookup failed (" + str(response.status_code) + "): " + response.text)
                break

            payload = response.json()
            items = payload.get("items") or []
            for item in items:
                name = (item.get("itemName") or "").strip().strip('"').strip("'").lower()  # 따옴표 제거
                item_id = item.get("id")
                if name and isinstance(item_id, int):
                    catalog[name] = item_id

            pagination = payload.get("pagination") or {}
            total_pages = pagination.get("total_pages") or page
            if page >= total_pages or not items:
                break
            page += 1

        if not catalog:
            _warn("Item lookup returned no results.")
        return catalog
