import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from models.schemas.chat import ConversationListResponse, ConversationDetail

router = APIRouter()


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.get("/history", response_model=ConversationListResponse)
async def get_history(
    user_id: uuid.UUID = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated conversation history for a user."""
    try:
        result = await db.execute(
            text("""
                SELECT id, title, model, created_at, updated_at
                FROM conversations
                WHERE user_id = :user_id
                ORDER BY COALESCE(updated_at, created_at) DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": str(user_id), "limit": limit, "offset": offset},
        )
        rows = result.mappings().all()
        conversations = [
            ConversationDetail(
                id=row["id"],
                title=row["title"] or "Untitled",
                model=row["model"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
    except Exception:
        conversations = []

    return ConversationListResponse(conversations=conversations, total=len(conversations))


@router.get("/history/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all messages for a specific conversation."""
    try:
        result = await db.execute(
            text("""
                SELECT id, role, content, token_count, created_at
                FROM messages
                WHERE conversation_id = :conv_id
                ORDER BY created_at ASC
            """),
            {"conv_id": str(conversation_id)},
        )
        rows = result.mappings().all()
        return {"conversation_id": str(conversation_id), "messages": list(rows)}
    except Exception:
        return {"conversation_id": str(conversation_id), "messages": []}


@router.patch("/history/{conversation_id}")
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: RenameConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rename a conversation."""
    title = body.title.strip()[:200] or "Untitled"
    try:
        result = await db.execute(
            text("UPDATE conversations SET title = :title, updated_at = NOW() "
                 "WHERE id = :id"),
            {"title": title, "id": str(conversation_id)},
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"id": str(conversation_id), "title": title}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Rename failed: {e}")


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and its messages."""
    try:
        # Delete leaf tables first (FK order matters):
        # compression_records and validation_results → optimization_runs → messages/conversations
        await db.execute(
            text("""
                DELETE FROM compression_records
                WHERE run_id IN (
                    SELECT id FROM optimization_runs WHERE conversation_id = :id
                )
            """),
            {"id": str(conversation_id)},
        )
        await db.execute(
            text("""
                DELETE FROM validation_results
                WHERE run_id IN (
                    SELECT id FROM optimization_runs WHERE conversation_id = :id
                )
            """),
            {"id": str(conversation_id)},
        )
        await db.execute(
            text("DELETE FROM optimization_runs WHERE conversation_id = :id"),
            {"id": str(conversation_id)},
        )
        await db.execute(
            text("DELETE FROM messages WHERE conversation_id = :id"),
            {"id": str(conversation_id)},
        )
        await db.execute(
            text("DELETE FROM conversations WHERE id = :id"),
            {"id": str(conversation_id)},
        )
        await db.commit()
        return {"deleted": True, "id": str(conversation_id)}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
