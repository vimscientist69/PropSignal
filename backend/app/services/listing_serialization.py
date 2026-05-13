"""Serialize ``Listing`` ORM rows to JSON-friendly dicts for API responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.inspection import inspect

from app.models.listing import Listing


def _jsonable_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        text = value.isoformat()
        return text.replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    return str(value)


def listing_columns_public_dict(listing: Listing) -> dict[str, Any]:
    """All persisted listing columns as JSON-serializable values."""
    mapper = inspect(Listing)
    out: dict[str, Any] = {}
    for attr in mapper.mapper.column_attrs:
        key = attr.key
        out[key] = _jsonable_scalar(getattr(listing, key))
    return out
