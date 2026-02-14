import os
import json
import cv2
import time

from flask import Flask, render_template, request, jsonify, send_file, Response
from concurrent.futures import ThreadPoolExecutor
import threading

from models.registry import ModelRegistry
# from models.yolo_ultralytics import UltralyticsYoloModel
# from models.custom_torch import CustomTorchModel
from utils.visualize import draw_detections

# from SSD.model_v1 import VisDroneSSD
# from SSD.model_v2 import VisDroneSSD2

# from utils.utils import count_files_in_directory

from config import UPLOAD_FOLDER, ALLOWED_EXT, DB_NAME

from app.queue_worker import worker_loop, clear_all_tasks, stop_task, list_tasks, set_r_to_q
from app.queue_storage import get_task, init_db, enqueue_task, get_db
from app.files import delete_files


# MAX_WORKERS = 1
# executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


progress = {}

app = Flask(__name__)

app.static_folder = ''

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

@app.post("/delete_files_with_results")
def delete_files_with_results():

    data = request.get_json()
    print(data)

    if not data:
        return jsonify({"error": "No JSON body"}), 400

    files = data.get("files")
    # print(files)
    result: dict = delete_files(files)

    return jsonify(result)



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



# @app.route("/tasks_stream")
# def tasks_stream():
#     def generate():
#         last_update = {}

#         while True:
#             db = get_db()
#             rows = db.execute("""
#                 SELECT id, file, model, progress, status, updated_at
#                 FROM tasks
#             """).fetchall()
#             db.close()

#             for row in rows:
#                 task_id = row["id"]
#                 updated_at = row["updated_at"]

#                 # отправляем только если изменилось
#                 if (
#                     task_id not in last_update or
#                     last_update[task_id] != updated_at
#                 ):
#                     last_update[task_id] = updated_at

#                     yield f"data: {json.dumps({
#                         "id": row["id"],
#                         "file": row["file"],
#                         "model": row["model"],
#                         "progress": row["progress"],
#                         "status": row["status"]
#                     })}\n\n"

#             time.sleep(0.5)

#     return Response(
#         generate(),
#         mimetype="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "X-Accel-Buffering": "no"
#         }
#     )


@app.route("/tasks_stream")
def tasks_stream():
    def generate():
        last_update = {}

        while True:
            db = get_db()
            rows = db.execute("""
                SELECT id, file, model, progress, status, updated_at
                FROM tasks
            """).fetchall()
            db.close()

            for row in rows:
                id, file, model, progress, status, updated_at = row
                task_id = id
                updated_at = updated_at

                # отправляем только если изменилось
                if (
                    task_id not in last_update or
                    last_update[task_id] != updated_at
                ):
                    last_update[task_id] = updated_at

                    yield f"data: {json.dumps({
                        "id": id,
                        "file": file,
                        "model": model,
                        "progress": progress,
                        "status": status
                    })}\n\n"

            time.sleep(0.5)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


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


# @app.route("/run_inference_sse")
# def run_inference_sse():
#     task_id = request.args["task"]

#     def stream():
#         last = None
#         while True:
#             task = get_task(task_id)
#             # print("task", task)
#             if not task:
#                 break

#             if task != last:
#                 yield f"data: {json.dumps(task)}\n\n"
#                 last = task

#             if task["status"] in ("done", "stopped"):
#                 yield f"data: {json.dumps({'type':'done'})}\n\n"
#                 break

#             time.sleep(0.5)

#     return Response(stream(), mimetype="text/event-stream")




@app.post("/stop_task/<task_id>")
def stop_task_post(task_id):
    response = stop_task(task_id)
    return jsonify(response)



@app.route("/tasks")
def tasks():
    tasks = list_tasks()

    return jsonify(tasks)


@app.route("/set_r_to_q")
def set_r_to_q_get():
    response = set_r_to_q()
    
    return jsonify({
        'set_r_to_q': response
    })


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
    init_db()

    # данная проверка необходима, чтобы worker запускался только в основном потоке при запуске app с флагом debug=True
    # Запускает первый процесс (контроллер)
    # Потом делает "Restarting with stat"
    # Запускает второй процесс (реальный сервер)
    # if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    #     print("Starting worker in PID", os.getpid())
    #     threading.Thread(
    #         target=worker_loop,
    #         args=(executor,),
    #         daemon=True
    #     ).start()

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("Starting worker in PID", os.getpid())
        threading.Thread(
            target=worker_loop,
            daemon=True
        ).start()

    app.run(debug=True)
