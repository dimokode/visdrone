import os
import json
import cv2
import time

from flask import Flask, render_template, request, jsonify, send_file, Response


from models.registry import ModelRegistry
from models.yolo_ultralytics import UltralyticsYoloModel
from models.custom_torch import CustomTorchModel
from utils.visualize import draw_detections

from SSD.model_v1 import VisDroneSSD
from SSD.model_v2 import VisDroneSSD2

# from utils.utils import count_files_in_directory

from config import UPLOAD_FOLDER, ALLOWED_EXT, DB_NAME

import threading
from app.queue_worker import worker_loop, clear_all_tasks
from app.queue_storage import get_task, init_db, enqueue_task

if not os.path.exists(DB_NAME):
    init_db()

threading.Thread(
    target=worker_loop,
    daemon=True
).start()


progress = {}

app = Flask(__name__)

app.static_folder = ''


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


# def is_video(filename):
#     return filename.lower().endswith((".mp4", ".avi", ".mkv", ".mov"))


def run_video_inference(model, video_path):
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0
    results = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = model.predict(frame)
        results[str(frame_idx)] = detections

        frame_idx += 1

    cap.release()
    return results, fps


@app.route('/results/<path:filename>')
def results(filename):
    return app.send_static_file(os.path.join('results', filename))

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return app.send_static_file(os.path.join("uploads", filename))



@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("images")
    # session_id = str(uuid.uuid4())

    # session_dir = os.path.join("uploads", session_id)
    session_dir = os.path.join("uploads")
    os.makedirs(session_dir, exist_ok=True)

    filenames = []
    for f in files:
        path = os.path.join(session_dir, f.filename)
        f.save(path)
        filenames.append(f.filename)

    return jsonify({
        # "session_id": session_id,
        "files": filenames
    })


@app.route("/get_files", methods=["POST"])
def get_files():
    filenames = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(ALLOWED_EXT)]

    return jsonify({
        "files": filenames
    })

@app.route("/clear_queue", methods=["POST"])
def clear_queue():
    return jsonify(
        clear_all_tasks()
    )


@app.route("/enqueue_task", methods=["POST"])
def enqueue():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    file = data.get("file")
    model = data.get("model")

    if not file or not model:
        return jsonify({"error": "file and model required"}), 400

    # 🔒 Проверяем, что файл существует
    file_path = os.path.join(UPLOAD_FOLDER, file)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # 🔒 Проверяем, что модель существует
    try:
        ModelRegistry.get(model)
    except Exception:
        return jsonify({"error": "Model not found"}), 404

    # 🧠 Создаём задачу
    task_id = enqueue_task(file, model)

    return jsonify({
        "task_id": task_id,
        "file": file,
        "model": model,
        "status": "queued"
    })


@app.route("/get_models", methods=["POST"])
def get_models():
    models = [{'id': model.id, 'name': model.name} for model in ModelRegistry.list()]
    return jsonify({
        "models": models
    })

@app.route("/get_models_index", methods=["POST"])
def get_models_index():
    models = {model.id: model.name for model in ModelRegistry.list()}
    return jsonify(models)

@app.route("/results/<image_name>/list")
def list_image_results(image_name):
    result_dir = os.path.join("results", image_name)
    if not os.path.exists(result_dir):
        return jsonify([])

    models = [
        f.replace(".json", "")
        for f in os.listdir(result_dir)
        if f.endswith(".json")
    ]

    return jsonify(models)


@app.route("/results/<image_name>/<model_id>")
def get_image_result(image_name, model_id):
    path = os.path.join("results", image_name, f"{model_id}.json")
    return send_file(path, mimetype="application/json")


@app.route("/run_inference_sse")
def run_inference_sse():
    task_id = request.args["task"]

    def stream():
        last = None
        while True:
            task = get_task(task_id)
            print("task", task)
            if not task:
                break

            if task != last:
                yield f"data: {json.dumps(task)}\n\n"
                last = task

            if task["status"] in ("done", "stopped"):
                yield f"data: {json.dumps({'type':'done'})}\n\n"
                break

            time.sleep(0.5)

    return Response(stream(), mimetype="text/event-stream")





# @app.post("/stop_task/<task_id>")
# def stop_task(task_id):
#     set_task_status(task_id, "stopped")
#     return {"ok": True}




# @app.route("/run_inference_sse")
# def run_inference_sse():
#     files = request.args.getlist("images")
#     model_ids = request.args.getlist("models")

#     upload_dir = UPLOAD_FOLDER

#     def generate():
#         # глобальный прогресс = file × model
#         total_units = len(files) * len(model_ids)
#         done_units = 0

#         # основной инференс
#         for file in files:
#             path = os.path.join(upload_dir, file)
#             result_dir = os.path.join("results", file)
#             os.makedirs(result_dir, exist_ok=True)

#             for model_id in model_ids:
#                 model = ModelRegistry.get(model_id)

#                 # ---------- VIDEO ----------
#                 if is_video(file):
#                     cap = cv2.VideoCapture(path)
#                     total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#                     fps = cap.get(cv2.CAP_PROP_FPS)

#                     frame_idx = 0
#                     frames_result = {}

#                     while cap.isOpened():
#                         ret, frame = cap.read()
#                         if not ret:
#                             break

#                         detections = model.predict(frame)
#                         frames_result[str(frame_idx)] = detections

#                         model_progress = (frame_idx + 1) / total_frames

#                         progress_data = json.dumps({
#                             "type": "progress",
#                             "file": file,
#                             "model": model_id,
#                             "frame": frame_idx,

#                             "model_progress": round(model_progress, 4),

#                             "progress": round(done_units / total_units, 4)
#                         })

#                         yield f"data: {progress_data}\n\n"

#                         frame_idx += 1

#                     cap.release()

#                     # сохранение видео-детекций
#                     result_path = os.path.join(result_dir, f"{model_id}.json")
#                     with open(result_path, "w") as f:
#                         json.dump({
#                             "media_type": "video",
#                             "file": file,
#                             "model_id": model_id,
#                             "fps": fps,
#                             "frames": frames_result
#                         }, f, indent=2)

#                     # файл для модели ЗАВЕРШЁН
#                     done_units += 1

#                     progress_data = json.dumps({
#                         "type": "progress",
#                         "file": file,
#                         "model": model_id,
#                         "model_progress": 1.0,
#                         "progress": round(done_units / total_units, 4)
#                     })

#                     yield f"data: {progress_data}\n\n"

#                 # ---------- IMAGE ----------
#                 else:
#                     detections = model.predict(path)

#                     # сохранение image-детекций
#                     result_path = os.path.join(result_dir, f"{model_id}.json")
#                     with open(result_path, "w") as f:
#                         json.dump({
#                             "media_type": "image",
#                             "file": file,
#                             "model_id": model_id,
#                             "detections": detections
#                         }, f, indent=2)

#                     done_units += 1

#                     progress_data = json.dumps({
#                         "type": "progress",
#                         "file": file,
#                         "model": model_id,
#                         "model_progress": 1.0,
#                         "progress": round(done_units / total_units, 4)
#                     })

#                     yield f"data: {progress_data}\n\n"

#         yield f"data: {json.dumps({'type': 'done'})}\n\n"

#     return Response(
#         generate(),
#         mimetype="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "X-Accel-Buffering": "no"
#         }
#     )









@app.route("/")
def index():
    return render_template("index.html")

@app.route("/progress/<task_id>")
def get_progress(task_id):
    p = progress.get(task_id, {})
    return jsonify(p)


@app.route("/predict", methods=["POST"])
def predict():
    file = request.files["image"]
    model_id = request.form["model"]

    model = ModelRegistry.get(model_id)

    input_path = os.path.join(UPLOAD_FOLDER, file.filename)

    file.save(input_path)

    detections = model.predict(input_path)

    return jsonify({
        "detections": detections,
        "image_url": f"uploads/{file.filename}"
    })


if __name__ == "__main__":
    app.run(debug=True)
    # app.run(host="0.0.0.0.", port=5000)

