import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    query: Mapped[str] = mapped_column(String, nullable=False)
    original_token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    optimized_token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    token_reduction_pct: Mapped[float] = mapped_column(Float, nullable=True)
    cost_original: Mapped[float] = mapped_column(Float, nullable=True)
    cost_optimized: Mapped[float] = mapped_column(Float, nullable=True)
    bert_score: Mapped[float] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    engine_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="optimization_runs")
    compression_records: Mapped[list["CompressionRecord"]] = relationship("CompressionRecord", back_populates="optimization_run", cascade="all, delete-orphan")

class CompressionRecord(Base):
    __tablename__ = "compression_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("optimization_runs.id"), nullable=True)
    compressed_text: Mapped[str] = mapped_column(String, nullable=False)
    recovery_map: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {ptr_id: {source, byte_range, summary, trigger}}
    expansion_log: Mapped[list] = mapped_column(JSONB, default=list)  # which pointers were expanded and when
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    optimization_run: Mapped["OptimizationRun"] = relationship("OptimizationRun", back_populates="compression_records")
