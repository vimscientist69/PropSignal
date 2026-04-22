# Scoring Evaluation Spec: Middle and Bottom Gating

This document defines how to extend `backend/app/services/scoring_evaluation.py` with segment-based stability diagnostics (`top_band`, `middle_band`, `bottom_band`), where `top_band` remains the release-critical gate.

## 1) Why this change is needed

Current stability logic focuses on top-N behavior, which is correct for release-critical outcomes.

However, on larger datasets, exact slice overlap in middle and bottom windows is naturally noisy:
- many listings are near-tied,
- small score perturbations move boundary memberships,
- exact 20-row windows can show low overlap despite no meaningful regression.

The result is that middle/bottom instability is either:
- invisible (if only top-N is evaluated), or
- over-penalized (if exact fixed windows are treated like top-N).

We need a more robust way to monitor non-top behavior.

## 2) Goals and non-goals

### Goals
- Add middle and bottom stability diagnostics that scale to large datasets.
- Use percentile bands instead of tiny fixed windows for overlap checks.
- Add rank displacement metrics to quantify movement magnitude, not just membership/order agreement.
- Keep release decision logic stable: top-band remains hard gate; middle/bottom are warning diagnostics.
- Produce actionable violation details in report output for manual inspection.

### Non-goals
- Do not change top-band policy from fail-capable to warning-only.
- Do not make middle/bottom hard fail criteria in first rollout.
- Do not alter scoring math itself; this is evaluation/reporting logic only.

## 3) Proposed logic (high-level)

### 3.1 Segment definitions

Introduce stable percentile segments from ranked rows:
- `top_band`: first `top_n` rows (release-critical)
- `middle_band`: percentile range, default `0.45` to `0.60`
- `bottom_band`: percentile range, default `0.85` to `1.00`

Bands are calculated by index range on sorted ranks, not score thresholds.

### 3.2 Metrics per segment

For each segment compare current job vs reference job:
- `jaccard_overlap`: set overlap of listing identities
- `rank_correlation`: ordering consistency within the segment identity intersection
- `median_abs_rank_shift`: typical absolute movement in **global rank position** for shared listings
- `p90_rank_shift`: tail movement in **global rank position** for shared listings

For middle/bottom, `jaccard_overlap` is interpreted as diagnostic (not fail) due to expected boundary churn.

### 3.2b Should displacement be per band or full dataset?

Use both:
- **Per-band displacement** (`top_band`, `middle_band`, `bottom_band`) for localized movement signals.
- **Full-dataset displacement** for a global movement pulse check.

Important semantics:
- All displacement metrics use **global-rank shift** (`|new_global_rank - old_global_rank|`),
  not band-local positional shift.

Policy in this spec:
- `top_band` displacement is fail-capable (release-critical).
- `middle_band` and `bottom_band` displacement is warning-level in v1.
- `full_dataset` displacement is warning-level context in v1.

### 3.3 Perturbation behavior

Keep existing perturbation sensitivity based on full ranked list.
Do not add separate perturbation per segment in v1 to avoid metric bloat.

### 3.4 Gate interpretation

- Top segment:
  - existing thresholds stay release-critical (`fail` can trigger `revert`).
- Middle and bottom segments:
  - produce `warn` when below configured thresholds.
  - warnings surface in `warning_gates` and detailed report payload.
  - do not convert to `fail` in v1.

## 4) Specific code changes

All edits are in `backend/app/services/scoring_evaluation.py` unless noted.

### 4.1 Add helper: `_segment_bounds(total_count, start_pct, end_pct) -> tuple[int, int]`

Purpose:
- Convert percentile band into safe index bounds.

Rules:
- clamp percentile inputs to `[0.0, 1.0]`
- guarantee `start < end` where possible
- return empty window when dataset too small

### 4.2 Add helper: `_segment_identities(rows, identity_map, start_idx, end_idx) -> list[str]`

Purpose:
- Return identity list for a ranked slice (`listing_id` external identity when available).

Why:
- keeps identity mapping logic centralized and consistent across metrics.

### 4.3 Add helper: `_segment_rank_correlation(current_ids, reference_ids) -> float`

Purpose:
- Compute rank correlation for a segment, using shared intersection only.

Note:
- can call existing `_spearman_rank_correlation` directly if signatures match.
- this helper is optional if reuse is clean.

### 4.4 Add helper: `_evaluate_segment_stability(...) -> dict[str, Any]`

Inputs:
- segment name
- current/reference ranked rows
- current/reference identity maps
- optional thresholds

Outputs:
- status (`pass` or `warn` for non-top bands)
- metrics (`jaccard_overlap`, `rank_correlation`, displacement metrics, counts)
- thresholds used
- `violation_details` for low-overlap/correlation cases

### 4.4b Add helper: `_rank_displacement_metrics(current_ids, reference_ids) -> dict[str, float]`

Purpose:
- Compute absolute rank shift statistics for shared listing identities.

Outputs:
- `median_abs_rank_shift`
- `p90_rank_shift`
- `intersection_count`

Semantics:
- Rank shifts are computed using global ranking positions in each run.

### 4.5 Extend stability section in `run_scoring_evaluation(...)`

Current behavior:
- computes top-N jaccard
- computes full-list rank correlation
- computes perturbation overlap

New behavior:
- replace the current top-only stability payload with segment-based stability diagnostics:
  - `top_band` remains release-critical
  - middle and bottom are warning diagnostics in v1
- add nested segment diagnostics under `stability.metrics.segments`:
  - `top_band`
  - `middle_band`
  - `bottom_band`
- middle/bottom status contributes warnings only
- add global displacement context under `stability.metrics.full_dataset`

### 4.6 Extend warning accumulation logic

When middle/bottom segment status is `warn`, append warning keys:
- `stability_middle_band`
- `stability_bottom_band`

These should not be included in `failed_gates` in v1.

## 5) Config changes

Update `config/scoring.yaml` and defaults in `backend/app/services/scoring.py`:

```yaml
evaluation_thresholds:
  stability:
    segments:
      top_band:
        mode: top_n
        top_n: 20
        jaccard_min: 0.70
        rank_correlation_min: 0.80
        perturbation_overlap_min: 0.60
        median_abs_rank_shift_max: 30
        p90_rank_shift_max: 120
      middle_band:
        start_pct: 0.45
        end_pct: 0.60
        jaccard_warn_min: 0.30
        rank_correlation_warn_min: 0.50
        median_abs_rank_shift_warn_max: 250
        p90_rank_shift_warn_max: 1200
      bottom_band:
        start_pct: 0.85
        end_pct: 1.00
        jaccard_warn_min: 0.25
        rank_correlation_warn_min: 0.40
        median_abs_rank_shift_warn_max: 300
        p90_rank_shift_warn_max: 1500
    full_dataset:
      median_abs_rank_shift_warn_max: 200
      p90_rank_shift_warn_max: 1000
```

Notes:
- These thresholds are intentionally conservative warning-level defaults.
- Tune by dataset size and empirical behavior after initial runs.
- Segment thresholds live under `stability.segments.*`.
- Full-dataset displacement thresholds live under `stability.full_dataset`.
- Full-dataset displacement thresholds are warning-level context in v1.
- Displacement thresholds apply to global-rank-shift metrics, not band-local shifts.

## 6) Report schema (replacement)

Inside `report["gates"]["stability"]`:

- Use a segment-first schema (no backward-compatibility constraint for this rollout).
- Replace old top-level stability metric locations with:
  - `metrics.segments.top_band`
  - `metrics.segments.middle_band`
  - `metrics.segments.bottom_band`
- Each segment includes:
  - `sample_size_current`
  - `sample_size_reference`
  - `intersection_count`
  - `jaccard_overlap`
  - `rank_correlation`
  - `median_abs_rank_shift`
  - `p90_rank_shift`
  - `thresholds` (segment-scoped; exact keys depend on band)
  - `status`
  - `violation_details` (if warning/fail)
- Threshold storage path is per segment:
  - `metrics.segments.top_band.thresholds`
  - `metrics.segments.middle_band.thresholds`
  - `metrics.segments.bottom_band.thresholds`
- Expected threshold keys by segment:
  - `top_band.thresholds`: `jaccard_min`, `rank_correlation_min`, `perturbation_overlap_min`, `median_abs_rank_shift_max`, `p90_rank_shift_max`
  - `middle_band.thresholds`: `jaccard_warn_min`, `rank_correlation_warn_min`, `median_abs_rank_shift_warn_max`, `p90_rank_shift_warn_max`
  - `bottom_band.thresholds`: `jaccard_warn_min`, `rank_correlation_warn_min`, `median_abs_rank_shift_warn_max`, `p90_rank_shift_warn_max`
- Include full-dataset displacement block:
  - `metrics.full_dataset.intersection_count`
  - `metrics.full_dataset.median_abs_rank_shift`
  - `metrics.full_dataset.p90_rank_shift`
  - `metrics.full_dataset.thresholds`
  - `metrics.full_dataset.status` (`pass`/`warn` in v1)
- Remove old top-level top-N metric locations from report payload:
  - `metrics.top_n_jaccard`
  - `metrics.rank_correlation`
  - `thresholds.top_n_jaccard_min`
  - `thresholds.rank_correlation_min`
- Keep perturbation output under top band context (segment-scoped), not as an orphan top-level metric.

Also add warning key(s) at top report level where applicable.

## 7) Test plan

Update `backend/tests/test_scoring_v2_evaluation.py`:

1. `test_middle_and_bottom_bands_reported_for_large_dataset`
   - assert `top_band`, `middle_band`, and `bottom_band` segment blocks exist
   - assert metrics fields present and numeric
   - assert thresholds are present inside each segment block
   - assert displacement metrics are present inside each segment block

2. `test_middle_band_warning_does_not_force_revert`
   - craft case with top passing, middle warning
   - expect overall decision remains `promote` or `experimental` (not `revert` solely from segment warning)

3. `test_bottom_band_warning_populates_warning_gates`
   - assert `stability_bottom_band` appears in `warning_gates`

4. `test_segment_bounds_small_dataset_safe`
   - ensure no crashes for tiny datasets and empty bands return deterministic outputs

5. `test_reference_missing_keeps_existing_warn_behavior`
   - no reference job -> existing stability warn path unchanged

6. `test_top_band_displacement_threshold_can_fail`
   - craft case where top-band displacement exceeds max thresholds
   - assert top-band status becomes `fail` and can influence overall `revert`

7. `test_full_dataset_displacement_warning_is_context_only`
   - craft case where full-dataset displacement exceeds warn threshold
   - assert `metrics.full_dataset.status == "warn"` and this alone does not force `revert`

## 8) Rollout plan

### Phase 1 (this change)
- Add segment diagnostics and warnings only.
- Keep `top_band` stability as the only fail-capable path.
- Add displacement metrics:
  - `top_band` displacement fail-capable
  - `middle_band`/`bottom_band` displacement warning-level
  - `full_dataset` displacement warning-level context

### Phase 2 (optional, after observation)
- If segment warnings correlate with quality regressions, consider making severe repeated warnings fail-capable.
- Consider making `full_dataset` displacement fail-capable if empirically justified.

## 9) Acceptance criteria

- Evaluation artifact includes segment diagnostics for `top_band`, `middle_band`, and `bottom_band`.
- Stability config uses segmented keys under `evaluation_thresholds.stability`:
  - `stability.segments.*` for band-level thresholds
  - `stability.full_dataset.*` for global displacement thresholds
- Decision logic unchanged for `top_band` pass/fail cases.
- Middle/bottom instability appears as warning keys, not hard fail.
- Thresholds are emitted under each segment block in report output (no top-level stability threshold fields).
- Displacement metrics are emitted per band and for full dataset.
- Tests cover happy path, warning path, and small dataset edge cases.

## 10) Why this is better than exact middle/bottom fixed windows

Percentile bands are less brittle than fixed 20-row windows:
- less boundary noise sensitivity,
- more representative of cohort behavior,
- more useful on large datasets where dense score regions are common.

This yields better operational signal without creating false regressions.
