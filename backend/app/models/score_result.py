from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class ScoreResult(Base):
    __tablename__ = "score_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    deal_reason: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), default="v0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
