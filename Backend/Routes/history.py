from fastapi import APIRouter, Depends, HTTPException

from Backend.Routes.auth import get_current_user
from Backend.services.database import (
    get_db,
    get_user_conversation
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

    return {
        "success": True,
        "conversation": conversation
    }


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