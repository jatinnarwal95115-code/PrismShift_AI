import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from Backend.Routes.auth import get_current_user
from Backend.services.database import (
    get_db,
    get_user_conversation,
    UPLOAD_DIR
)

router = APIRouter(
    prefix="/history",
    tags=["Conversation History"]
)


@router.get("/")
def get_history(user=Depends(get_current_user)):

    with get_db() as db:
        rows = db.execute("""
            SELECT
                id,
                title,
                mode,
                created_at,
                updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user["id"],)).fetchall()

    return {
        "success": True,
        "history": [dict(row) for row in rows]
    }


@router.get("/{conversation_id}")
def open_conversation(
    conversation_id: int,
    user=Depends(get_current_user)
):

    conversation = get_user_conversation(
        conversation_id,
        user["id"]
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    with get_db() as db:
        rows = db.execute("""
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """, (conversation_id,)).fetchall()

    conversation["messages"] = [
        dict(row) for row in rows
    ]
    try:
        conversation["input_data"] = json.loads(conversation.get("input_data") or "{}")
    except (TypeError, ValueError):
        conversation["input_data"] = {}
    conversation["image_url"] = (
        f"/history/{conversation_id}/image" if conversation.get("image_path") else None
    )
    conversation.pop("image_path", None)

    return {
        "success": True,
        "conversation": conversation
    }


@router.get("/{conversation_id}/image")
def get_conversation_image(
    conversation_id: int,
    user=Depends(get_current_user)
):
    conversation = get_user_conversation(conversation_id, user["id"])
    if not conversation or not conversation.get("image_path"):
        raise HTTPException(status_code=404, detail="Image not found.")

    image_path = Path(conversation["image_path"]).resolve()
    if image_path.parent != UPLOAD_DIR.resolve() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Saved image is no longer available.")

    media_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp"
    }.get(image_path.suffix.lower(), "application/octet-stream")
    return FileResponse(str(image_path), media_type=media_type)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user=Depends(get_current_user)
):

    conversation = get_user_conversation(
        conversation_id,
        user["id"]
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    with get_db() as db:
        db.execute("""
            DELETE FROM conversations
            WHERE id = ? AND user_id = ?
        """, (
            conversation_id,
            user["id"]
        ))

    return {
        "success": True,
        "message": "Conversation deleted."
    }