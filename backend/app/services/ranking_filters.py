"""Apply Week 3 ranking filters to listing rows (in-memory, post-merge)."""

from __future__ import annotations

from app.models.listing import Listing
from app.schemas.ranking import RankingFilters
from app.services.scoring import _confidence_signal


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def listing_matches_filters(listing: Listing, filters: RankingFilters) -> bool:
    if filters.province and _norm(listing.province) != _norm(filters.province):
        return False
    if filters.city and _norm(listing.city) != _norm(filters.city):
        return False
    if filters.suburb and _norm(listing.suburb) != _norm(filters.suburb):
        return False
    if filters.price_min is not None and listing.price < filters.price_min:
        return False
    if filters.price_max is not None and listing.price > filters.price_max:
        return False
    if filters.property_type:
        if filters.property_type.lower() not in (listing.property_type or "").lower():
            return False
    if filters.bedrooms_min is not None and (listing.bedrooms or 0) < filters.bedrooms_min:
        return False
    if filters.bathrooms_min is not None and (listing.bathrooms or 0.0) < filters.bathrooms_min:
        return False
    if filters.confidence_min is not None:
        if _confidence_signal(listing) < filters.confidence_min:
            return False
    return True


def apply_ranking_filters(listings: list[Listing], filters: RankingFilters) -> list[Listing]:
    return [L for L in listings if listing_matches_filters(L, filters)]
