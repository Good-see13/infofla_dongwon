"""
YOLO/VLM Model Management Module.
"""

from __future__ import annotations

import logging
import os
import types
from enum import Enum
from typing import Dict, Optional, Tuple, Union

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from ultralytics import YOLO

from src.core.config import (
    VLM_MODEL_CACHE_DIR,
    VLM_MODEL_NAME,
    VLM_DEVICE_MAP,
    YOLO_BACKBONE_MODEL,
    YOLO_TRAINED_MODEL,
)
from src.models.exceptions import ModelLoadError, ModelNotAvailableError, build_error_message

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Supported YOLO model variants."""

    BACKBONE = "backbone"
    TRAINED = "trained"

    @classmethod
    def from_value(cls, value: Union[str, "ModelType"]) -> "ModelType":
        """Coerce incoming value to a ModelType enum."""
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Unsupported model type: {value!r}")


class YOLOModelManager:
    """Manages YOLO model lifecycle."""

    _MODEL_LABELS = {
        ModelType.BACKBONE: "Backbone (COCO)",
        ModelType.TRAINED: "Trained (Sprocket)",
    }

    def __init__(
        self,
        backbone_model_path: str = YOLO_BACKBONE_MODEL,
        trained_model_path: str = YOLO_TRAINED_MODEL,
    ):
        self._model_paths: Dict[ModelType, str] = {
            ModelType.BACKBONE: backbone_model_path,
            ModelType.TRAINED: trained_model_path,
        }
        self._models: Dict[ModelType, Optional[YOLO]] = {
            ModelType.BACKBONE: None,
            ModelType.TRAINED: None,
        }
        self._load_attempted: Dict[ModelType, bool] = {
            model_type: False for model_type in ModelType
        }
        self._load_errors: Dict[ModelType, Optional[str]] = {
            model_type: None for model_type in ModelType
        }

    def load_models(self) -> None:
        """Eagerly load available YOLO models."""
        for model_type in ModelType:
            self._models[model_type] = None
            self._load_attempted[model_type] = False
            self._load_errors[model_type] = None
        self._load_model(ModelType.BACKBONE, required=True)
        self._load_model(ModelType.TRAINED, required=False)

    def ensure_loaded(self, model_type: Union[str, ModelType]) -> None:
        """Guarantee that the requested model is loaded."""
        model_enum = ModelType.from_value(model_type)
        if self._models.get(model_enum) is not None:
            return

        if self._load_attempted.get(model_enum):
            error = self._load_errors.get(model_enum)
            if error:
                if model_enum is ModelType.BACKBONE:
                    raise ModelLoadError(error)
                logger.debug(
                    "Skipping reload for %s model after previous failure: %s",
                    model_enum.value,
                    error,
                )
            return

        self._load_model(model_enum, required=model_enum is ModelType.BACKBONE)

    def get_model(self, model_type: Union[str, ModelType]) -> Tuple[YOLO, str]:
        """Retrieve YOLO model instance and display label."""
        model_enum = ModelType.from_value(model_type)
        model = self._models.get(model_enum)
        if model is None:
            detail = self._load_errors.get(model_enum) or self._maybe_missing_path(
                model_enum
            )
            raise ModelNotAvailableError(
                build_error_message(
                    f"{model_enum.value} model not loaded",
                    detail=detail,
                )
            )
        return model, self._MODEL_LABELS[model_enum]

    def is_ready(self, model_type: Union[str, ModelType] = ModelType.BACKBONE) -> bool:
        """Check if the requested model has been loaded."""
        model_enum = ModelType.from_value(model_type)
        return self._models.get(model_enum) is not None

    def get_status(self) -> Dict[str, bool]:
        """Return readiness flags for available models."""
        return {model_type.value: self.is_ready(model_type) for model_type in ModelType}

    def _load_model(self, model_type: ModelType, required: bool) -> None:
        path = self._model_paths[model_type]
        self._load_attempted[model_type] = True
        self._load_errors[model_type] = None
        self._models[model_type] = None

        if not os.path.exists(path):
            message = build_error_message(
                f"Model file not found for {model_type.value}", detail=path
            )
            self._load_errors[model_type] = message
            if required:
                logger.error(message)
                raise ModelLoadError(message)
            logger.warning(message)
            return

        try:
            self._models[model_type] = YOLO(path)
            logger.info("YOLO %s model loaded from %s", model_type.value, path)
            self._load_errors[model_type] = None
        except Exception as exc:
            message = build_error_message(
                f"Failed to load {model_type.value} model", detail=str(exc)
            )
            self._load_errors[model_type] = message
            if required:
                logger.error(message)
                raise ModelLoadError(message) from exc
            logger.warning(message)

    def _maybe_missing_path(self, model_type: ModelType) -> Optional[str]:
        path = self._model_paths.get(model_type)
        if path and not os.path.exists(path):
            return f"path missing ({path})"
        return None

    def unload_models(self) -> None:
        """Unload all YOLO models and free memory."""
        logger.info("Unloading YOLO models...")
        for model_type in ModelType:
            if self._models.get(model_type) is not None:
                try:
                    # YOLO 모델은 Python의 가비지 컬렉터가 처리하지만,
                    # 명시적으로 None으로 설정하여 참조 제거
                    self._models[model_type] = None
                    logger.info("YOLO %s model unloaded", model_type.value)
                except Exception as e:
                    logger.warning("Failed to unload %s model: %s", model_type.value, e)
        logger.info("YOLO models unloaded")


class VLMModelManager:
    """Qwen3-VL model manager."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or VLM_MODEL_CACHE_DIR
        self.model: Optional[Qwen3VLForConditionalGeneration] = None
        self.processor: Optional[AutoProcessor] = None
        self.model_name: Optional[str] = None
        self._load_attempted: bool = False
        self._load_error: Optional[str] = None

    def load_model(self) -> bool:
        """Load the Qwen3-VL model, preferring local cache."""
        logger.info("Loading VLM...")
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            self._ensure_torch_compiler_shims()
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                VLM_MODEL_NAME,
                cache_dir=self.cache_dir,
                dtype=torch.float32,
                device_map=VLM_DEVICE_MAP,
            )
            self.processor = AutoProcessor.from_pretrained(
                VLM_MODEL_NAME,
                cache_dir=self.cache_dir,
            )
            self.model_name = VLM_MODEL_NAME.split("/")[-1]
            logger.info("VLM loaded: %s", self.model_name)
            self._load_attempted = True
            self._load_error = None
            return True
        except Exception as exc:
            message = build_error_message("VLM load failed", detail=str(exc))
            logger.error(message)
            self.model = None
            self.processor = None
            self.model_name = None
            self._load_attempted = True
            self._load_error = message
            return False

    def ensure_loaded(self) -> None:
        """Ensure the VLM assets are loaded."""
        if not self.is_ready():
            if self._load_attempted and self._load_error:
                raise ModelLoadError(self._load_error)
            if not self.load_model():
                raise ModelLoadError(self._load_error or "Unable to load VLM model")

    def is_ready(self) -> bool:
        """Check if VLM model and processor are available."""
        return self.model is not None and self.processor is not None

    def get_model_info(self) -> Dict[str, Optional[Union[str, bool]]]:
        """Return metadata about the VLM model."""
        return {
            "model_name": self.model_name,
            "cache_dir": self.cache_dir,
            "is_ready": self.is_ready(),
            "last_error": self._load_error,
        }

    def unload_model(self) -> None:
        """Unload VLM model and processor, free memory."""
        logger.info("Unloading VLM model...")
        try:
            if self.model is not None:
                # PyTorch 모델을 CPU로 이동 후 메모리 해제
                if hasattr(self.model, "cpu"):
                    self.model.cpu()
                # 모델 참조 제거
                del self.model
                self.model = None
                logger.info("VLM model unloaded")
            
            if self.processor is not None:
                del self.processor
                self.processor = None
                logger.info("VLM processor unloaded")
            
            # Python 가비지 컬렉터가 메모리 정리하도록 명시적 호출
            import gc
            gc.collect()
            
            # PyTorch 캐시 정리
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("VLM model memory freed")
        except Exception as e:
            logger.warning("Failed to unload VLM model: %s", e)

    @staticmethod
    def _ensure_torch_compiler_shims() -> None:
        """Provide torch.compiler shims when running on older torch builds."""
        compiler_module = getattr(torch, "compiler", None)
        if compiler_module is None:
            compiler_module = types.SimpleNamespace()
            setattr(torch, "compiler", compiler_module)
        if not hasattr(compiler_module, "is_compiling"):
            compiler_module.is_compiling = lambda: False  # type: ignore[attr-defined]
        if not hasattr(compiler_module, "is_exporting"):
            compiler_module.is_exporting = lambda: False  # type: ignore[attr-defined]
