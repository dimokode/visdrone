import os
import sqlite3, json, uuid, datetime

from config import DB_NAME


def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        status TEXT,
        file TEXT,
        model TEXT,
        progress REAL,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    db.commit()


def enqueue_task(file, model):
    task_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()

    db = get_db()
    db.execute("""
        INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        task_id,
        "queued",
        file,
        model,
        0.0,
        now,
        now
    ))
    db.commit()
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
