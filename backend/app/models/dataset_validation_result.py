from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DatasetValidationResult(Base):
    __tablename__ = "dataset_validation_results"
    __table_args__ = (UniqueConstraint("job_id", name="uq_dataset_validation_results_job_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    valid_rate: Mapped[float] = mapped_column(Float)
    invalid_rate: Mapped[float] = mapped_column(Float)
    duplicate_rate: Mapped[float] = mapped_column(Float)
    price_null_rate: Mapped[float] = mapped_column(Float)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    report_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
