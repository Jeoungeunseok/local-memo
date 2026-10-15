import os
import sqlite3
from typing import Optional, List
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("DB_PATH", "sticky_notes.db")

app = FastAPI(title="Sticky Notes & Calendar API")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sticky_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_date TEXT,
            content TEXT,
            color TEXT,
            is_pinned INTEGER,
            pos_x INTEGER,
            pos_y INTEGER,
            width INTEGER,
            height INTEGER
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

class NoteCreate(BaseModel):
    target_date: Optional[str] = None
    content: Optional[str] = ""
    color: Optional[str] = "yellow"
    is_pinned: Optional[int] = 0
    pos_x: Optional[int] = 160
    pos_y: Optional[int] = 140
    width: Optional[int] = 320
    height: Optional[int] = 280

class NoteUpdate(BaseModel):
    target_date: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    is_pinned: Optional[int] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

@app.get("/api/notes")
def list_notes(date_filter: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if date_filter:
        cursor.execute("SELECT * FROM sticky_notes WHERE target_date = ? ORDER BY is_pinned DESC, id ASC", (date_filter,))
    else:
        cursor.execute("SELECT * FROM sticky_notes ORDER BY is_pinned DESC, id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/notes")
def create_note(note: NoteCreate):
    conn = get_db()
    cursor = conn.cursor()
    target_date = note.target_date or date.today().isoformat()
    cursor.execute(
        """
        INSERT INTO sticky_notes (target_date, content, color, is_pinned, pos_x, pos_y, width, height)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_date,
            note.content or "",
            note.color or "yellow",
            note.is_pinned or 0,
            note.pos_x if note.pos_x is not None else 160,
            note.pos_y if note.pos_y is not None else 140,
            note.width or 320,
            note.height or 280,
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM sticky_notes WHERE id = ?", (new_id,))
    created_note = dict(cursor.fetchone())
    conn.close()
    return created_note

@app.put("/api/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sticky_notes WHERE id = ?", (note_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        raise HTTPException(status_code=404, detail="Note not found")

    target_date = note.target_date if note.target_date is not None else current["target_date"]
    content = note.content if note.content is not None else current["content"]
    color = note.color if note.color is not None else current["color"]
    is_pinned = note.is_pinned if note.is_pinned is not None else current["is_pinned"]
    pos_x = note.pos_x if note.pos_x is not None else current["pos_x"]
    pos_y = note.pos_y if note.pos_y is not None else current["pos_y"]
    width = note.width if note.width is not None else current["width"]
    height = note.height if note.height is not None else current["height"]

    cursor.execute(
        """
        UPDATE sticky_notes
        SET target_date = ?, content = ?, color = ?, is_pinned = ?, pos_x = ?, pos_y = ?, width = ?, height = ?
        WHERE id = ?
        """,
        (target_date, content, color, is_pinned, pos_x, pos_y, width, height, note_id),
    )
    conn.commit()
    cursor.execute("SELECT * FROM sticky_notes WHERE id = ?", (note_id,))
    updated_note = dict(cursor.fetchone())
    conn.close()
    return updated_note

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sticky_notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted_id": note_id}

@app.get("/api/summary")
def get_summary():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT target_date, color, COUNT(*) as count FROM sticky_notes GROUP BY target_date, color")
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) as total FROM sticky_notes")
    total = cursor.fetchone()["total"]
    conn.close()
    return {"total": total, "groups": [dict(r) for r in rows]}

# Serve static files and UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
