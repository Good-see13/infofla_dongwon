import cv2
from src.core.config import CAMERA_ID, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

class Camera:
    
    def __init__(self, camera_id=None, width=None, height=None, fps=None):
        self.camera_id = camera_id or CAMERA_ID
        self.width = width or CAMERA_WIDTH
        self.height = height or CAMERA_HEIGHT
        self.fps = fps or CAMERA_FPS
        self.cap = None
    
    def open(self):
        self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            print("ERROR: Cannot open webcam")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        return True
    
    def read(self):
        return (False, None) if self.cap is None else self.cap.read()
    
    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
        cv2.waitKey(1)
    
    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

