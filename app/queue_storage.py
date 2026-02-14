import os
import sqlite3, json, uuid, datetime

from config import DB_NAME


def get_db():
    # db = sqlite3.connect(DB_NAME, check_same_thread=False)
    # db.execute("PRAGMA journal_mode=WAL;")
    # db.close()
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    print("init_db")
    db = sqlite3.connect(DB_NAME)

    # db.execute("""
    # CREATE TABLE IF NOT EXISTS tasks (
    #     id TEXT PRIMARY KEY,
    #     status TEXT,
    #     file TEXT,
    #     model TEXT,
    #     progress REAL,
    #     created_at TEXT,
    #     updated_at TEXT
    # )
    # """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT,
        file TEXT,
        model TEXT,
        progress REAL,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    db.execute("PRAGMA journal_mode=WAL;")

    db.execute("""
        UPDATE tasks
        SET status='queued', progress=0
        WHERE status='running'
    """)

    db.commit()
    db.execute("""
        DELETE FROM tasks
        WHERE status='done'
    """)
    db.commit()

    db.close()




def enqueue_task(file, model):
    # task_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()

    db = get_db()
    # INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)

    cursor = db.execute("""
        INSERT INTO tasks(status, file, model, progress, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)
        """, (
        "queued",
        file,
        model,
        0.0,
        now,
        now
    ))
    db.commit()
    task_id = cursor.lastrowid
    return task_id





def get_task(task_id):
    db = get_db()
    row = db.execute(
        """
        SELECT id, status, file, model,
               progress, created_at, updated_at
        FROM tasks
        WHERE id = ?
        """,
        (task_id,)
    ).fetchone()

    db.close()

    if not row:
        return None

    return {
        "id": row[0],
        "status": row[1],
        "file": row[2],
        "model": row[3],
        "progress": row[4],
        "created_at": row[5],
        "updated_at": row[6]
    }
