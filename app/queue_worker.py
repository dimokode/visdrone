import time, json, os, cv2
from models.registry import ModelRegistry

from config import UPLOAD_FOLDER
from utils.utils import is_video

from app.queue_storage import get_task, get_db



def worker_loop():
    while True:
        db = get_db()
        row = db.execute(
            "SELECT id, status FROM tasks WHERE status='queued' ORDER BY created_at LIMIT 1"
        ).fetchone()

        print('ROW', row)

        if not row:
            time.sleep(1)
            continue

        task_id = row[0]
        status = row[1]

        if status == "stopped":
            break

        run_task(task_id)



def run_task(task_id):
    task = get_task(task_id)
    file = task["file"]
    model_id = task["model"]

    db = get_db()
    db.execute(
        "UPDATE tasks SET status='running' WHERE id=?",
        (task_id,)
    )
    db.commit()

    model = ModelRegistry.get(model_id)
    path = os.path.join(UPLOAD_FOLDER, file)
    result_dir = os.path.join("results", file)
    os.makedirs(result_dir, exist_ok=True)

    # ---------- IMAGE ----------
    if not is_video(file):
        detections = model.predict(path)

        # save_image_result(result_dir, model_id, detections)
        # сохранение image-детекций
        result_path = os.path.join(result_dir, f"{model_id}.json")
        with open(result_path, "w") as f:
            json.dump({
                "media_type": "image",
                "file": file,
                "model_id": model_id,
                "detections": detections
            }, f, indent=2)

        db.execute(
            """
            UPDATE tasks
            SET progress=1.0, status='done'
            WHERE id=?
            """,
            (task_id,)
        )
        db.commit()
        return

    # ---------- VIDEO ----------
    cap = cv2.VideoCapture(path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    frames = {}
    idx = 0

    while cap.isOpened():

        if get_task(task_id)["status"] == "stopped":
            cap.release()
            return

        ret, frame = cap.read()
        if not ret:
            break

        detections = model.predict(frame)
        frames[str(idx)] = detections

        progress = (idx + 1) / total_frames

        db.execute(
            """
            UPDATE tasks
            SET progress=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (progress, task_id)
        )
        db.commit()

        idx += 1

    cap.release()

    # with open(os.path.join(result_dir, f"{model_id}.json"), "w") as f:
    #     json.dump({
    #         "media_type": "video",
    #         "frames": frames
    #     }, f, indent=2)

    with open(os.path.join(result_dir, f"{model_id}.json"), "w") as f:
        json.dump({
            "media_type": "video",
            "file": file,
            "model_id": model_id,
            "fps": fps,
            "frames": frames
        }, f, indent=2)

    db.execute(
        """
        UPDATE tasks
        SET progress=1.0, status='done'
        WHERE id=?
        """,
        (task_id,)
    )
    db.commit()


def clear_all_tasks():
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Удалить все записи из таблицы
        cursor.execute("DELETE FROM tasks")
        
        db.commit()
        return {
            "success": True,
            "msg": "All tasks has been removed"
        }
    except Exception as exc_msg:
        return {
            "success": False,
            "msg": "Error by clearing tasks",
            "err_msg": str(exc_msg)
        }

