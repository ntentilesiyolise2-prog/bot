import cv2
import numpy as np
from ultralytics import YOLO
import os
from utils.logger import setup_logger

logger = setup_logger(__name__)

class YOLOScanner:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            # Using a generic pre-trained model; fine-tune later on candlestick patterns
            self.model = YOLO('yolov8n.pt')
            logger.info("YOLO model loaded.")
        except Exception as e:
            logger.error(f"YOLO load failed: {e}. Vision scanner disabled.")
            self.model = None

    def scan(self, image_bytes):
        if self.model is None:
            return []
        try:
            # Convert bytes to image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            results = self.model(img)
            detections = []
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        detections.append({
                            'class': self.model.names[cls],
                            'confidence': round(conf * 100, 2)
                        })
            return detections
        except Exception as e:
            logger.error(f"YOLO scan error: {e}")
            return []
