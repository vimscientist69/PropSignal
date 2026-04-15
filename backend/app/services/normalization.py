from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from app.schemas.propflux_listing import PropfluxListing

PROPERTY_TYPE_MAP = {
    "house": "house",
    "apartment": "apartment",
    "flat": "apartment",
    "townhouse": "townhouse",
    "duplex": "duplex",
    "vacant land": "vacant_land",
}


def _normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned if cleaned else None


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d+]", "", value)
    return digits or None


def _normalize_property_type(value: str) -> str:
    normalized = _normalize_whitespace(value)
    if normalized is None:
        return "unknown"
    return PROPERTY_TYPE_MAP.get(normalized.lower(), normalized.lower().replace(" ", "_"))


@dataclass
class NormalizedListing:
    payload: dict[str, object]
    source_hash: str


def normalize_listing(record: PropfluxListing) -> NormalizedListing:
    payload = record.model_dump(mode="json")

    payload["title"] = _normalize_whitespace(record.title) or record.title
    payload["location"] = _normalize_whitespace(record.location) or record.location
    payload["description"] = _normalize_whitespace(record.description) or record.description
    payload["property_type"] = _normalize_property_type(record.property_type)
    payload["agent_name"] = _normalize_whitespace(record.agent_name)
    payload["agency_name"] = _normalize_whitespace(record.agency_name)
    payload["agent_phone"] = _normalize_phone(record.agent_phone)
    payload["suburb"] = _normalize_whitespace(record.suburb)
    payload["city"] = _normalize_whitespace(record.city)
    payload["province"] = _normalize_whitespace(record.province)

    numeric_fields = [
        "price",
        "bathrooms",
        "erf_size",
        "floor_size",
        "rates_and_taxes",
        "levies",
    ]
    for numeric_field in numeric_fields:
        value = payload.get(numeric_field)
        if isinstance(value, (int, float)):
            payload[numeric_field] = round(float(value), 2)

    hash_input = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    source_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    return NormalizedListing(payload=payload, source_hash=source_hash)
