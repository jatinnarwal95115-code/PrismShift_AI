import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = BASE_DIR / "generated" / "reports"

DB_PATH = DATA_DIR / "prismshift.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Open a database connection and close it safely."""

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row

    # SQLite ignores foreign keys unless this is enabled on EVERY connection.
    # Without it, deleting a conversation left its messages behind.
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create all database tables if they do not exist."""

    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            mode TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                ON DELETE CASCADE
        );
        """)

        # Remove messages orphaned by the old, non-cascading deletes.
        db.execute(
            """
            DELETE FROM messages
            WHERE conversation_id NOT IN (SELECT id FROM conversations)
            """
        )


def create_conversation(user_id, title, mode, image_path=None):
    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO conversations
            (user_id, title, mode, image_path)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, mode, image_path)
        )

        return cursor.lastrowid


def save_message(conversation_id, role, content):
    with get_db() as db:
        db.execute(
            """
            INSERT INTO messages
            (conversation_id, role, content)
            VALUES (?, ?, ?)
            """,
            (conversation_id, role, content)
        )

        db.execute(
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (conversation_id,)
        )


def get_user_conversations(user_id):
    with get_db() as db:
        rows = db.execute(
            """
            SELECT * FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def get_user_conversation(conversation_id, user_id):
    with get_db() as db:
        conversation = db.execute(
            """
            SELECT * FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id)
        ).fetchone()

        if not conversation:
            return None

        messages = db.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

        result = dict(conversation)
        result["messages"] = [dict(message) for message in messages]

        return result


def delete_user_conversation(conversation_id, user_id):
    with get_db() as db:
        cursor = db.execute(
            """
            DELETE FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id)
        )

        return cursor.rowcount > 0

def to_iso_utc(value):
    """SQLite CURRENT_TIMESTAMP is UTC but has no zone marker, so browsers
    read it as local time. Return an explicit ISO-8601 UTC string."""

    if not value:
        return value

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value

    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def delete_image_file(image_path):
    """Delete an uploaded image, but only if it is inside the upload folder."""

    if not image_path:
        return

    try:
        path = Path(image_path).resolve()

        if path.parent == UPLOAD_DIR.resolve() and path.is_file():
            path.unlink()
    except OSError:
        pass
