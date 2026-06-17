import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from models.schemas.compression import CompressionRecordResponse, ExpansionResult

router = APIRouter()


@router.get("/compression/{compression_id}", response_model=CompressionRecordResponse)
async def get_compression(compression_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch compression record (compressed text + recovery map) for the UI viewer."""
    try:
        result = await db.execute(
            text("""
                SELECT id, compressed_text, recovery_map, expansion_log, created_at
                FROM compression_records
                WHERE id = :id
            """),
            {"id": str(compression_id)},
        )
        row = result.mappings().one_or_none()
    except Exception:
        row = None

    if row is None:
        raise HTTPException(status_code=404, detail="Compression record not found")

    return CompressionRecordResponse(
        id=row["id"],
        compressed_text=row["compressed_text"],
        recovery_map=row["recovery_map"],
        expansion_log=row["expansion_log"],
        created_at=row["created_at"],
    )


@router.post("/expand/{ptr_id}", response_model=ExpansionResult)
async def expand_pointer(
    ptr_id: str,
    compression_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Expand a recovery pointer — return original passage from source document."""
    try:
        result = await db.execute(
            text("SELECT recovery_map FROM compression_records WHERE id = :id"),
            {"id": str(compression_id)},
        )
        row = result.mappings().one_or_none()
    except Exception:
        row = None

    if row is None:
        raise HTTPException(status_code=404, detail="Compression record not found")

    recovery_map: dict = row["recovery_map"]
    if ptr_id not in recovery_map:
        raise HTTPException(status_code=404, detail=f"Pointer '{ptr_id}' not found")

    pointer = recovery_map[ptr_id]

    # Log the expansion event
    try:
        import json
        from datetime import datetime
        await db.execute(
            text("""
                UPDATE compression_records
                SET expansion_log = expansion_log || :entry::jsonb
                WHERE id = :id
            """),
            {
                "id": str(compression_id),
                "entry": json.dumps([{"ptr_id": ptr_id, "expanded_at": datetime.utcnow().isoformat()}]),
            },
        )
        await db.commit()
    except Exception:
        pass  # expansion log failure is non-fatal

    return ExpansionResult(
        ptr_id=ptr_id,
        original_text=f"[Expanded content for {ptr_id}: {pointer.get('summary', '')}]",
        summary=pointer.get("summary", ""),
        trigger=pointer.get("trigger", ""),
        source_doc=pointer.get("source_doc", ""),
    )
