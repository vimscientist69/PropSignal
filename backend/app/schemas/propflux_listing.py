from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError


class RecordValidationError(BaseModel):
    record_index: int
    error_code: str
    error_detail: str
    payload: dict[str, Any]


class PropfluxListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required fields
    title: str
    price: float
    location: str
    bedrooms: int
    bathrooms: float
    property_type: str
    description: str

    # Optional fields
    agent_name: str | None = None
    agent_phone: str | None = None
    agency_name: str | None = None
    listing_id: str | None = None
    date_posted: date | None = None
    erf_size: float | None = None
    floor_size: float | None = None
    rates_and_taxes: float | None = None
    levies: float | None = None
    garages: int | None = None
    parking: int | None = None
    en_suite: int | None = None
    lounges: int | None = None
    backup_power: bool | None = None
    security: bool | None = None
    pets_allowed: bool | None = None

    # Common metadata fields from PropFlux-style payloads
    listing_url: str | None = None
    suburb: str | None = None
    city: str | None = None
    province: str | None = None
    is_auction: bool | None = None
    is_private_seller: bool | None = None
    source_site: str | None = None
    scraped_at: datetime | None = None


def validate_propflux_payload(payload: Any) -> list[PropfluxListing]:
    if not isinstance(payload, list):
        raise ValueError("PropFlux payload must be a JSON array of listing objects.")
    listings: list[PropfluxListing] = []
    for index, row in enumerate(payload):
        try:
            listings.append(PropfluxListing.model_validate(row))
        except ValidationError as exc:
            raise ValueError(f"Invalid listing at index {index}: {exc}") from exc
    return listings


def load_propflux_file(path: Path) -> list[PropfluxListing]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return validate_propflux_payload(payload)


def load_propflux_payload(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_propflux_payload_partial(
    payload: Any,
) -> tuple[list[tuple[int, PropfluxListing]], list[RecordValidationError]]:
    if not isinstance(payload, list):
        raise ValueError("PropFlux payload must be a JSON array of listing objects.")

    valid: list[tuple[int, PropfluxListing]] = []
    invalid: list[RecordValidationError] = []

    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            invalid.append(
                RecordValidationError(
                    record_index=index,
                    error_code="invalid_record_type",
                    error_detail="Record must be a JSON object",
                    payload={"_raw": row},
                )
            )
            continue
        try:
            parsed = PropfluxListing.model_validate(row)
            valid.append((index, parsed))
        except ValidationError as exc:
            invalid.append(
                RecordValidationError(
                    record_index=index,
                    error_code="validation_error",
                    error_detail=exc.json(),
                    payload=row,
                )
            )
    return valid, invalid
