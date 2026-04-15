# Baseline Scoring (Week 1) Implementation

## What "Baseline Scoring" Means

In Week 1, baseline scoring means a **stable, explainable first-pass score** that works end-to-end on
normalized PropFlux listings. It is intentionally simpler than Week 2 advanced scoring.

The goal is to ship a scoring pipeline that:

- produces a consistent `score` for every valid normalized listing
- generates a basic `confidence` value
- writes a short `deal_reason` summary
- is configurable via `config/scoring.yaml`
- is testable and deterministic

## Week 1 vs Week 2 Boundary

- Week 1 baseline:
  - rule-based weighted scoring
  - uses available normalized listing attributes directly
  - no heavy comparable clustering or advanced reasoning
- Week 2 advanced:
  - deeper market comparables and dynamic weighting
  - richer explanation engine
  - stronger confidence modeling with variance and consistency signals

## Baseline Scoring Inputs

Use normalized canonical records from `listings` and include only fields currently available:

- `price`
- `bedrooms`, `bathrooms`
- `erf_size`, `floor_size`
- `property_type`
- `date_posted` (if available)
- completeness indicators (required + optional presence)

## Baseline Score Model

Use a bounded weighted model mapped to `0-100`.

Example structure:

1. Compute component scores in `0-1` range:
   - `price_signal`
   - `size_value_signal`
   - `time_on_market_signal` (if `date_posted` is present, else neutral default)
   - `feature_density_signal` (bed/bath/size relationship)
2. Combine with config weights from `config/scoring.yaml`.
3. Clamp final score to `0-100`.

Reference formula:

`score_0_1 = w_price*price_signal + w_size*size_value_signal + w_time*time_on_market_signal + w_feature*feature_density_signal`

`score = round(score_0_1 * 100, 2)`

## Confidence (Week 1 Baseline)

Compute confidence as a simple completeness and quality proxy:

- start from data completeness ratio
- penalize missing high-value fields (`date_posted`, `floor_size`, `listing_id`)
- clamp to `0-1`

`confidence = round(clamp(completeness - penalties, 0, 1), 2)`

## Deal Reason (Week 1 Baseline)

Build a compact string/list from top contributing factors, for example:

- "Strong size-to-price profile"
- "Recent listing with complete metadata"
- "Limited size data reduced confidence"

Week 1 requirement is clarity, not narrative depth.

## Implementation Tasks

1. Add scoring service module (`backend/app/services/scoring.py`) baseline function:
   - input: normalized listing row
   - output: `score`, `confidence`, `deal_reason`, `model_version`
2. Persist results to `score_results`.
3. Add CLI scoring command behavior:
   - `score <job_id>` computes baseline for listings tied to job
4. Make weights configurable in `config/scoring.yaml`.
5. Add tests:
   - deterministic score for fixture listing
   - bounds checks (`score` in `0-100`, `confidence` in `0-1`)
   - reason generation for low-completeness and high-completeness examples

## Definition of Done (Week 1 Baseline Scoring)

- Running `score <job_id>` writes score rows for all valid listings in job.
- Every scored listing has:
  - `score`
  - `confidence`
  - `deal_reason`
  - `model_version = "baseline_v1"`
- Tests pass for deterministic behavior and score bounds.
- Configuration-only tuning is possible through `config/scoring.yaml`.
