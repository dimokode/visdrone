
import os

from models.registry import ModelRegistry
from models.yolo_ultralytics import UltralyticsYoloModel
from models.custom_torch import CustomTorchModel

from SSD.model_v1 import VisDroneSSD
from SSD.model_v2 import VisDroneSSD2

from utils.patch import download_weights


DB_NAME = "queue.db"

ALLOWED_EXT = ('jpg', 'mp4')
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
WEIGHTS_FOLDER = "weights"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

if not os.path.exists(WEIGHTS_FOLDER):
    print("Folder 'weights' doesn't exist")
    os.makedirs(WEIGHTS_FOLDER, exist_ok=True)
    download_weights()


# Регистрация моделей
ModelRegistry.register(
    UltralyticsYoloModel(
        model_id="y8m_1024_7cls",
        name="YOLOv8m img_size=1024 cls=7",
        weights_path="weights/y8m_1024_7cls.pt"
    )
)

ModelRegistry.register(
    UltralyticsYoloModel(
        model_id="yolov8n",
        name="YOLOv8n original",
        weights_path="weights/yolov8n.pt"
    )
)

ModelRegistry.register(
    UltralyticsYoloModel(
        model_id="best_50",
        name="YOLOv8m img_size=960 cls=7",
        weights_path="weights/best_50.pt"
    )
)

# ModelRegistry.register(
#     CustomTorchModel(
#         model = VisDroneSSD,
#         model_id="SSD",
#         name="My SSD",
#         model_path="weights/best_ssd7_1024_big.pth"
#     )
# )

# ModelRegistry.register(
#     CustomTorchModel(
#         model=VisDroneSSD2,
#         model_id="ssd8_1024_big",
#         name="My SSD img_size=1024",
#         model_path="weights/ssd8_1024_big.pth"
#     )
# )