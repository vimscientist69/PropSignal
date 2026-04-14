from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)

    # Required PropFlux fields
    title: Mapped[str] = mapped_column(String(512))
    price: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(String(512))
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[float] = mapped_column(Float)
    property_type: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)

    # Optional PropFlux fields
    agent_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    agent_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agency_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    listing_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    date_posted: Mapped[date | None] = mapped_column(Date, nullable=True)
    erf_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    rates_and_taxes: Mapped[float | None] = mapped_column(Float, nullable=True)
    levies: Mapped[float | None] = mapped_column(Float, nullable=True)
    garages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    en_suite: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lounges: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backup_power: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    security: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pets_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Common metadata present in PropFlux payloads
    listing_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    suburb: Mapped[str | None] = mapped_column(String(256), nullable=True)
    city: Mapped[str | None] = mapped_column(String(256), nullable=True)
    province: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_auction: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_private_seller: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_site: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
