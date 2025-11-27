import os
from ultralytics import YOLO
from src.core.config import YOLO_BACKBONE_MODEL, YOLO_TRAINED_MODEL

class YOLOModelLoader:
    
    def __init__(self, backbone_path=None, trained_path=None):
        self.backbone_model_path = backbone_path or YOLO_BACKBONE_MODEL
        self.trained_model_path = trained_path or YOLO_TRAINED_MODEL
        self.backbone_model = None
        self.trained_model = None
    
    def load_models(self):
        self.backbone_model = YOLO(self.backbone_model_path)
        try:
            if os.path.exists(self.trained_model_path):
                self.trained_model = YOLO(self.trained_model_path)
            else:
                self.trained_model = None
        except Exception:
            self.trained_model = None
        return self.backbone_model, self.trained_model
    
    def predict(self, img, model_type="backbone", conf=None):
        from src.core.config import BACKBONE_CONFIDENCE, TRAINED_CONFIDENCE
        if model_type == "trained" and self.trained_model:
            results = self.trained_model.predict(source=img, verbose=False, conf=conf or TRAINED_CONFIDENCE)
            return results, "Trained", (0, 0, 255)
        results = self.backbone_model.predict(source=img, verbose=False, conf=conf or BACKBONE_CONFIDENCE)
        name = "Backbone" if model_type == "backbone" else "Backbone (Fallback)"
        color = (0, 255, 0) if model_type == "backbone" else (0, 255, 255)
        return results, name, color

