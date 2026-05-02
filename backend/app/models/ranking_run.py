from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RankingRun(Base):
    __tablename__ = "ranking_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    query_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    strategy_preset: Mapped[str] = mapped_column(String(64))
    resolved_profile_id: Mapped[str] = mapped_column(String(128))
    profile_row_id: Mapped[int] = mapped_column(
        ForeignKey("scoring_profile_backups.id"), index=True
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_window: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
