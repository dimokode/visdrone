import time, json, os, cv2
from models.registry import ModelRegistry

from config import UPLOAD_FOLDER
from utils.utils import is_video

from app.queue_storage import get_task, get_db




# def worker_loop(executor):
#     print("WORKER STARTED", os.getpid())

#     while True:
#         db = get_db()

#         # row = db.execute("""
#         #     SELECT id, file, model
#         #     FROM tasks
#         #     WHERE status='queued'
#         #     AND file NOT IN (
#         #         SELECT file FROM tasks WHERE status='running'
#         #     )
#         #     ORDER BY created_at
#         #     LIMIT 1
#         # """).fetchone()

#         # row = db.execute("""
#         #     SELECT id, file, model
#         #     FROM tasks
#         #     WHERE status='queued'
#         #     AND file NOT IN (
#         #         SELECT file FROM tasks WHERE status='running'
#         #     )
#         #     ORDER BY id
#         #     LIMIT 1
#         # """).fetchone()

#         row = db.execute("""
#             SELECT id, file, model
#             FROM tasks
#             WHERE status='queued'
#             ORDER BY id
#             LIMIT 1
#         """).fetchone()

#         if row:
#             task_id, file, model_id = row

#             executor.submit(run_task, task_id, file, model_id)

#         time.sleep(0.5)

#         db.close()


# def worker_loop(executor):
#     while True:
#         db = get_db()

#         row = db.execute("""
#             SELECT id, file, model FROM tasks
#             WHERE status='queued'
#             ORDER BY created_at
#             LIMIT 1
#         """).fetchone()

#         if not row:
#             db.close()
#             time.sleep(1)
#             continue

#         id, file, model = row

#         task_id = id
#         # file = file
#         # model = model

#         # атомарный захват
#         updated = db.execute("""
#             UPDATE tasks
#             SET status='running'
#             WHERE id=? AND status='queued'
#         """, (task_id,))
#         db.commit()

#         if db.total_changes == 0:
#             db.close()
#             continue

#         db.close()

#         # process_task(task_id)
#         executor.submit(run_task, task_id, file, model)


def worker_loop():
    while True:
        db = get_db()

        row = db.execute("""
            SELECT id, file, model FROM tasks
            WHERE status='queued'
            ORDER BY created_at
            LIMIT 1
        """).fetchone()

        if not row:
            db.close()
            time.sleep(1)
            continue

        task_id, file, model = row

        updated = db.execute("""
            UPDATE tasks
            SET status='running'
            WHERE id=? AND status='queued'
        """, (task_id,))
        db.commit()

        if db.total_changes == 0:
            db.close()
            continue

        db.close()

        print("START TASK:", task_id)

        # 🔥 ВАЖНО — блокирующий вызов
        run_task(task_id, file, model)



def set_r_to_q():
    try:
        db = get_db()

        db.execute("""
            UPDATE tasks
            SET status='queued'
            WHERE status='running'
        """)

        db.commit()
        db.close()
        return True
    except Exception:
        return False



# def update_task_progress(task_id, progress, status=None):
#     db = get_db()

#     if status:
#         db.execute("""
#             UPDATE tasks
#             SET progress=?, status=?, updated_at=datetime('now')
#             WHERE id=?
#         """, (progress, status, task_id))
#     else:
#         db.execute("""
#             UPDATE tasks
#             SET progress=?, updated_at=datetime('now')
#             WHERE id=?
#         """, (progress, task_id))

#     db.commit()
#     db.close()



def run_task(task_id, file, model_id):

    db = get_db()

    # db.execute(
    #     "UPDATE tasks SET status='running' WHERE id=? AND status='queued'",
    #     (task_id,)
    # )
    # db.commit()

    # # db.close()
    # # проверяем что реально изменили строку

    # print('run_task', 'db.total_changes', db.total_changes)
    # if db.total_changes == 0:
    #     db.close()
    #     return

    model = ModelRegistry.get(model_id)
    path = os.path.join(UPLOAD_FOLDER, file)
    result_dir = os.path.join("results", file)
    os.makedirs(result_dir, exist_ok=True)

    # ---------- IMAGE ----------
    if not is_video(file):
        detections = model.predict(path)

        # сохранение image-детекций
        result_path = os.path.join(result_dir, f"{model_id}.json")
        with open(result_path, "w") as f:
            json.dump({
                "media_type": "image",
                "file": file,
                "model_id": model_id,
                "detections": detections
            }, f, indent=2)

        db.execute("""
            UPDATE tasks
            SET progress=1.0,
                updated_at=datetime('now')
            WHERE id=?
        """, (task_id,))
        db.commit()

        db.execute("""
            UPDATE tasks
            SET status='done',
                updated_at=datetime('now')
            WHERE id=?
        """, (task_id,))
        db.commit()


    else:
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
            SET progress=1.0,
                status='done',
                updated_at=datetime('now')
            WHERE id=?
            """,
            (task_id,)
        )
        db.commit()
    
    db.close()




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


def stop_task(task_id):
    db = get_db()

    db.execute(
        "UPDATE tasks SET status='stopped' WHERE id=?",
        (task_id,)
    )
    db.commit()

    return {"status": "stopped"}


def list_tasks():
    db = get_db()
    rows = db.execute(
        "SELECT id, file, model, status, progress FROM tasks WHERE status IN ('running', 'queued')"
    ).fetchall()

    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "file": row[1],
            "model": row[2],
            "status": row[3],
            "progress": row[4]
        })

    return tasks