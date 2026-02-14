from ultralytics import YOLO
from models.base import BaseDetectionModel


class UltralyticsYoloModel(BaseDetectionModel):
    def __init__(self, model_id, name, weights_path):
        self.id = model_id
        self.name = name
        self.model = YOLO(weights_path)

    def predict(self, image_path):
        results = self.model(image_path, verbose=False)[0]

        detections = []
        for box in results.boxes:
            xmin, ymin, xmax, ymax = map(int, box.xyxy[0].tolist())
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = self.model.names[class_id]

            detections.append({
                "bbox": [xmin, ymin, xmax, ymax],
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence
            })

        return detections
