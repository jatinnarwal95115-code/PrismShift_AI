from fastapi import APIRouter, Depends, HTTPException

from Backend.Routes.auth import get_current_user
from Backend.services.database import (
    get_db,
    get_user_conversation,
    delete_user_conversation,
    delete_image_file,
    to_iso_utc
)

router = APIRouter(
    prefix="/history",
    tags=["Conversation History"]
)


@router.get("/")
def get_history(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, mode, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user["id"],)
        ).fetchall()

    history = []

    for row in rows:
        item = dict(row)
        item["created_at"] = to_iso_utc(item["created_at"])
        item["updated_at"] = to_iso_utc(item["updated_at"])
        history.append(item)

    return {"success": True, "history": history}


@router.get("/{conversation_id}")
def open_conversation(
    conversation_id: int,
    user=Depends(get_current_user)
):
    # get_user_conversation already returns the messages in order.
    conversation = get_user_conversation(conversation_id, user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conversation.pop("image_path", None)  # server file path: not for clients
    conversation["created_at"] = to_iso_utc(conversation["created_at"])
    conversation["updated_at"] = to_iso_utc(conversation["updated_at"])

    return {"success": True, "conversation": conversation}


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user=Depends(get_current_user)
):
    conversation = get_user_conversation(conversation_id, user["id"])

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    delete_user_conversation(conversation_id, user["id"])
    delete_image_file(conversation.get("image_path"))

    return {"success": True, "message": "Conversation deleted."}
