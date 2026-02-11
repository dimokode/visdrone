
import os

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
