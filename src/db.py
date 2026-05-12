import aiosqlite
from datetime import datetime

DB_NAME = "studyhelper.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            deadline TEXT,
            created_at TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weekday INTEGER NOT NULL,
            time TEXT NOT NULL,
            subject TEXT NOT NULL
        )
        """)

        await db.commit()


# ---------------------------------------------------------------------------
# Helpers: resolve user-facing sequential number → real DB id
# ---------------------------------------------------------------------------

async def _resolve_task_id(db, user_id: int, user_num: int, only_active: bool = False) -> int | None:
    """
    Возвращает реальный DB id задачи по её порядковому номеру у данного пользователя.
    Нумерация: 1 = самая старая (по created_at ASC).
    """
    where = "WHERE user_id=?"
    params = [user_id]
    if only_active:
        where += " AND done=0"

    cursor = await db.execute(f"""
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (
                       ORDER BY deadline IS NULL, deadline ASC, created_at ASC
                   ) AS rn
            FROM tasks {where}
        )
        WHERE rn = ?
    """, params + [user_num])
    row = await cursor.fetchone()
    return row[0] if row else None


async def _resolve_note_id(db, user_id: int, user_num: int) -> int | None:
    """Возвращает реальный DB id заметки по её порядковому номеру (1 = самая старая)."""
    cursor = await db.execute("""
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY id ASC) AS rn
            FROM notes WHERE user_id=?
        )
        WHERE rn = ?
    """, (user_id, user_num))
    row = await cursor.fetchone()
    return row[0] if row else None


async def _resolve_lesson_id(db, user_id: int, user_num: int) -> int | None:
    """Возвращает реальный DB id пары по её порядковому номеру (1 = пн, самая ранняя)."""
    cursor = await db.execute("""
        SELECT id FROM (
            SELECT id,
                   ROW_NUMBER() OVER (ORDER BY weekday ASC, time ASC) AS rn
            FROM schedule WHERE user_id=?
        )
        WHERE rn = ?
    """, (user_id, user_num))
    row = await cursor.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

async def add_task(user_id: int, title: str, deadline: str | None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO tasks (user_id, title, deadline, created_at, done) VALUES (?, ?, ?, ?, 0)",
            (user_id, title, deadline, datetime.now().isoformat())
        )
        await db.commit()


async def get_tasks(user_id: int, only_active: bool = True):
    """
    Возвращает (user_num, title, deadline, done).
    user_num — порядковый номер задачи у данного пользователя,
    начиная с 1; сначала задачи с дедлайном (по возрастанию), потом без.
    """
    where = "WHERE user_id=?"
    params = [user_id]
    if only_active:
        where += " AND done=0"

    query = f"""
        SELECT ROW_NUMBER() OVER (
                   ORDER BY deadline IS NULL, deadline ASC, created_at ASC
               ) AS rn,
               title, deadline, done
        FROM tasks {where}
        ORDER BY deadline IS NULL, deadline ASC, created_at ASC
    """

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(query, params)
        return await cursor.fetchall()


async def mark_task_done(user_id: int, user_num: int) -> bool:
    """Отмечает задачу выполненной по пользовательскому номеру. Возвращает True если нашли."""
    async with aiosqlite.connect(DB_NAME) as db:
        real_id = await _resolve_task_id(db, user_id, user_num, only_active=True)
        if real_id is None:
            return False
        await db.execute(
            "UPDATE tasks SET done=1 WHERE id=?", (real_id,)
        )
        await db.commit()
        return True


async def delete_task(user_id: int, user_num: int) -> bool:
    """Удаляет задачу по пользовательскому номеру. Возвращает True если нашли."""
    async with aiosqlite.connect(DB_NAME) as db:
        real_id = await _resolve_task_id(db, user_id, user_num)
        if real_id is None:
            return False
        await db.execute("DELETE FROM tasks WHERE id=?", (real_id,))
        await db.commit()
        return True


async def get_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor1 = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=?", (user_id,)
        )
        total = (await cursor1.fetchone())[0]

        cursor2 = await db.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id=? AND done=1", (user_id,)
        )
        done = (await cursor2.fetchone())[0]

        return total, done


async def get_deadline_tasks(user_id: int):
    """Возвращает активные задачи с дедлайном: (user_num, title, deadline)."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT ROW_NUMBER() OVER (
                       ORDER BY deadline IS NULL, deadline ASC, created_at ASC
                   ) AS rn,
                   title, deadline
            FROM tasks
            WHERE user_id=? AND done=0 AND deadline IS NOT NULL
            ORDER BY deadline ASC
        """, (user_id,))
        return await cursor.fetchall()


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

async def add_note(user_id: int, title: str, content: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO notes (user_id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, title, content, datetime.now().isoformat())
        )
        await db.commit()


async def get_notes(user_id: int):
    """Возвращает (user_num, title, created_at). 1 = самая старая заметка."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT ROW_NUMBER() OVER (ORDER BY id ASC) AS rn,
                   title, created_at
            FROM notes
            WHERE user_id=?
            ORDER BY id ASC
        """, (user_id,))
        return await cursor.fetchall()


async def get_note_by_user_num(user_id: int, user_num: int):
    """Читает заметку по пользовательскому номеру."""
    async with aiosqlite.connect(DB_NAME) as db:
        real_id = await _resolve_note_id(db, user_id, user_num)
        if real_id is None:
            return None
        cursor = await db.execute(
            "SELECT title, content, created_at FROM notes WHERE id=?", (real_id,)
        )
        return await cursor.fetchone()


# Оставляем для обратной совместимости с командой /note <id>
async def get_note_by_id(user_id: int, note_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT title, content, created_at FROM notes WHERE user_id=? AND id=?",
            (user_id, note_id)
        )
        return await cursor.fetchone()


async def search_notes(user_id: int, query: str):
    """Возвращает (user_num, title) для найденных заметок."""
    q = f"%{query.lower()}%"
    async with aiosqlite.connect(DB_NAME) as db:
        # Сначала получаем все заметки с их порядковыми номерами
        cursor = await db.execute("""
            SELECT ROW_NUMBER() OVER (ORDER BY id ASC) AS rn, id, title, content
            FROM notes
            WHERE user_id=?
        """, (user_id,))
        rows = await cursor.fetchall()

    results = []
    for rn, note_id, title, content in rows:
        if q[1:-1] in title.lower() or q[1:-1] in content.lower():
            results.append((rn, title))
    return results


async def delete_note(user_id: int, user_num: int) -> bool:
    """Удаляет заметку по пользовательскому номеру. Возвращает True если нашли."""
    async with aiosqlite.connect(DB_NAME) as db:
        real_id = await _resolve_note_id(db, user_id, user_num)
        if real_id is None:
            return False
        await db.execute("DELETE FROM notes WHERE id=?", (real_id,))
        await db.commit()
        return True


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

async def add_lesson(user_id: int, weekday: int, time: str, subject: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO schedule (user_id, weekday, time, subject) VALUES (?, ?, ?, ?)",
            (user_id, weekday, time, subject)
        )
        await db.commit()


async def get_schedule(user_id: int, weekday: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, time, subject FROM schedule WHERE user_id=? AND weekday=? ORDER BY time ASC",
            (user_id, weekday)
        )
        return await cursor.fetchall()


async def delete_lesson(user_id: int, user_num: int) -> bool:
    """Удаляет пару по пользовательскому номеру. Возвращает True если нашли."""
    async with aiosqlite.connect(DB_NAME) as db:
        real_id = await _resolve_lesson_id(db, user_id, user_num)
        if real_id is None:
            return False
        await db.execute("DELETE FROM schedule WHERE id=?", (real_id,))
        await db.commit()
        return True


async def get_all_lessons(user_id: int):
    """Возвращает (user_num, weekday, time, subject)."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT ROW_NUMBER() OVER (ORDER BY weekday ASC, time ASC) AS rn,
                   weekday, time, subject
            FROM schedule
            WHERE user_id=?
            ORDER BY weekday ASC, time ASC
        """, (user_id,))
        return await cursor.fetchall()