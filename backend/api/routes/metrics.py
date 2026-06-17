from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from models.schemas.chat import AggregateMetrics

router = APIRouter()


@router.get("/metrics", response_model=AggregateMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Return aggregate optimization metrics across all runs."""
    try:
        result = await db.execute(text("""
            SELECT
                COUNT(*)                          AS total_runs,
                AVG(token_reduction_pct)          AS avg_token_reduction,
                AVG(bert_score)                   AS avg_bert_score,
                AVG(quality_score)                AS avg_quality_score,
                SUM(cost_original - cost_optimized) AS total_cost_saved
            FROM optimization_runs
        """))
        row = result.mappings().one_or_none()
    except Exception:
        row = None

    if row is None or row["total_runs"] == 0:
        return AggregateMetrics(
            total_runs=0,
            avg_token_reduction_pct=0.0,
            avg_bert_score=0.0,
            avg_quality_score=0.0,
            total_cost_saved=0.0,
        )

    return AggregateMetrics(
        total_runs=row["total_runs"],
        avg_token_reduction_pct=round(row["avg_token_reduction"] or 0.0, 2),
        avg_bert_score=round(row["avg_bert_score"] or 0.0, 4),
        avg_quality_score=round(row["avg_quality_score"] or 0.0, 2),
        total_cost_saved=round(row["total_cost_saved"] or 0.0, 6),
    )
