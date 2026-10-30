import hashlib
import hmac
import secrets

from Backend.config import SESSION_DAYS
from Backend.services.database import get_db


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, original_hash = stored_hash.split("$", 1)

        new_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            200_000
        ).hex()

        return hmac.compare_digest(new_hash, original_hash)

    except (ValueError, AttributeError):
        return False


def create_user(name: str, email: str, password: str):
    password_hash = hash_password(password)

    with get_db() as db:
        cursor = db.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
            """,
            (name, email.lower().strip(), password_hash)
        )

        return cursor.lastrowid


def authenticate_user(email: str, password: str):
    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower().strip(),)
        ).fetchone()

    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return dict(user)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)

    with get_db() as db:
        db.execute(
            """
            INSERT INTO sessions (user_id, token)
            VALUES (?, ?)
            """,
            (user_id, token)
        )

    return token


def get_user_from_token(token: str):
    with get_db() as db:
        user = db.execute(
            """
            SELECT users.*
            FROM users
            JOIN sessions ON users.id = sessions.user_id
            WHERE sessions.token = ?
              AND sessions.created_at > datetime('now', ?)
            """,
            (token, f"-{SESSION_DAYS} days")
        ).fetchone()

    return dict(user) if user else None


def delete_expired_sessions():
    with get_db() as db:
        db.execute(
            "DELETE FROM sessions WHERE created_at <= datetime('now', ?)",
            (f"-{SESSION_DAYS} days",)
        )


def delete_session(token: str):
    with get_db() as db:
        db.execute(
            "DELETE FROM sessions WHERE token = ?",
            (token,)
        )