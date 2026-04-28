from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrategyPreset(StrEnum):
    rental_income = "rental_income"
    resale_arbitrage = "resale_arbitrage"
    refurbishment_value_add = "refurbishment_value_add"
    balanced_long_term = "balanced_long_term"


class RankingFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    province: str | None = None
    city: str | None = None
    suburb: str | None = None
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    property_type: str | None = None
    bedrooms_min: int | None = Field(default=None, ge=0)
    bathrooms_min: float | None = Field(default=None, ge=0)
    confidence_min: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_price_bounds(self) -> RankingFilters:
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min must be less than or equal to price_max")
        return self


class RankingStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: StrategyPreset
    weight_overrides: dict[str, float] = Field(default_factory=dict)


class ResultWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_n: int | None = Field(default=None, ge=1, le=500)
    page: int | None = Field(default=None, ge=1)
    page_size: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def validate_window_mode(self) -> ResultWindow:
        has_top_n = self.top_n is not None
        has_pagination = self.page is not None or self.page_size is not None
        if has_top_n and has_pagination:
            raise ValueError("top_n cannot be combined with page/page_size")
        if (self.page is None) != (self.page_size is None):
            raise ValueError("page and page_size must both be provided for pagination")
        return self


class RankingQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_sources: list[str] = Field(min_length=1)
    filters: RankingFilters = Field(default_factory=RankingFilters)
    strategy: RankingStrategy
    result_window: ResultWindow = Field(default_factory=ResultWindow)
    sort_mode: str = "score_desc"

    @model_validator(mode="after")
    def validate_dataset_sources(self) -> RankingQueryRequest:
        if any(not source.strip() for source in self.dataset_sources):
            raise ValueError("dataset_sources entries must be non-empty strings")
        if self.sort_mode != "score_desc":
            raise ValueError("sort_mode must be 'score_desc' for Week 3")
        return self


class RankingResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_id: int
    score: float
    deal_reason: str
    confidence: float = Field(ge=0, le=1)
    summary: dict[str, Any] = Field(default_factory=dict)
    detail_ref: str


class ResolvedProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    profile_version: str
    resolved_weights: dict[str, float]
    enabled_signals: list[str]


class DatasetContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_sources: list[str]
    records_considered: int = Field(ge=0)
    last_ingested_at: str | None = None
    last_scored_at: str | None = None
    model_version: str | None = None
    profile_version: str | None = None


class PaginationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "pagination"
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_count: int = Field(ge=0)


class TopNEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "top_n"
    top_n_requested: int = Field(ge=1, le=500)
    top_n_returned: int = Field(ge=0)


class RankingQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    query_fingerprint: str
    resolved_profile: ResolvedProfile
    dataset_context: DatasetContext
    results: list[RankingResultItem]
    pagination: PaginationEnvelope | None = None
    top_n: TopNEnvelope | None = None

    @model_validator(mode="after")
    def validate_envelope(self) -> RankingQueryResponse:
        if (self.pagination is None) == (self.top_n is None):
            raise ValueError("exactly one of pagination or top_n must be provided")
        return self


class ListingDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_core: dict[str, Any]
    score_summary: dict[str, Any]
    diagnostics: dict[str, Any]


class ProfileSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: StrategyPreset
    label: str
    description: str


class ProfileDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: StrategyPreset
    profile_id: str
    profile_version: str
    default_weights: dict[str, float]
    enabled_signals: list[str]
    safe_override_bounds: dict[str, dict[str, float]]


class ErrorField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    field_errors: list[ErrorField] = Field(default_factory=list)
    request_id: str
