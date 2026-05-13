from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RankingRunListing(Base):
    """Per-run snapshot for listings returned in a ranking response window."""

    __tablename__ = "ranking_run_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ranking_run_id: Mapped[int] = mapped_column(
        ForeignKey("ranking_runs.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    deal_reason: Mapped[str] = mapped_column(Text)
    explanation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
