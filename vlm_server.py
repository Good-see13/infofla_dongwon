from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.models import VLMModelManager, VLMProcessor
from src.models.processors import ImageProcessor
from src.core.config import USE_VLM
from src.utils.logger import setup_logging

logger = setup_logging()

app = FastAPI(title="동원산업POC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vlm_model_manager = None
vlm_processor = None

@app.on_event("startup")
async def startup_event():
    global vlm_model_manager, vlm_processor
    logger.info("Starting VLM Model Server...")
    
    if USE_VLM:
        vlm_model_manager = VLMModelManager()
        if vlm_model_manager.load_model():
            vlm_processor = VLMProcessor(vlm_model_manager)
            logger.info("VLM model loaded successfully")
            
            # Warmup
            logger.info("Running VLM warmup...")
            try:
                import numpy as np
                dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
                vlm_processor.analyze_image(dummy_image)
                logger.info("VLM warmup complete")
            except Exception as e:
                logger.warning("VLM warmup failed: %s", e)
        else:
            logger.error("VLM model load failed")
    else:
        logger.warning("VLM disabled (USE_VLM=false)")

@app.on_event("shutdown")
async def shutdown_event():
    global vlm_model_manager
    logger.info("Shutting down VLM Model Server...")
    if vlm_model_manager and vlm_model_manager.is_ready():
        vlm_model_manager.unload_model()
        logger.info("VLM model unloaded")

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not vlm_processor:
        return {"type": "error", "message": "VLM not available"}
    
    try:
        image_bytes = await file.read()
        image = ImageProcessor.process_image(image_bytes)
        result = vlm_processor.analyze_image(image)
        return result
    except Exception as e:
        logger.error("VLM analysis error: %s", e)
        return {"type": "error", "message": str(e)}

@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {
        "status": "ok",
        "vlm_ready": vlm_processor is not None,
        "service": "VLM Model Server"
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=60005,
        access_log=True,
        timeout_keep_alive=120,
    )

