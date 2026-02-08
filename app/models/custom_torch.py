import numpy as np
import torch
from models.base import BaseDetectionModel
import torchvision.transforms as transforms
from PIL import Image
import cv2


class CustomTorchModel(BaseDetectionModel):
    def __init__(self, model, model_id, name, model_path):
        self.model = model
        self.id = model_id
        self.name = name

        self.model = self.model(num_real_classes=7, img_size=1024)

        checkpoint = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

        self.class_names = [
            'bg', 'car', 'van', 'truck',
            'tricycle', 'awning-tricycle', 'bus', 'motor'
        ]

        self.transform = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225]
            )
        ])

    def predict(self, image_path):
        # Check if image is a numpy array
        if isinstance(image_path, np.ndarray):
            # Convert numpy array to PIL Image
            img = Image.fromarray(image_path).convert("RGB")
        else:
            # Assume it's a file path
            img = Image.open(image_path).convert("RGB")


        w, h = img.size

        img_tensor = self.transform(img).unsqueeze(0)

        with torch.no_grad():
            loc_preds, cls_preds = self.model(img_tensor)

        preds = self.model.decode_predictions(
            loc_preds[0],
            cls_preds[0],
            confidence_threshold=0.7,
            nms_threshold=0.45
        )

        detections = []
        for bbox, class_id, conf in preds:
            xmin, ymin, xmax, ymax = bbox

            detections.append({
                "bbox": [
                    int(xmin * w),
                    int(ymin * h),
                    int(xmax * w),
                    int(ymax * h)
                ],
                "class_id": int(class_id),
                "class_name": self.class_names[class_id],
                "confidence": float(conf)
            })

        return detections
