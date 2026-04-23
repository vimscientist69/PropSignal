# Week 2 Interface Contract

This document freezes the Week 2 output interface expectations before implementation work proceeds.

It defines:
- `advanced_v2` scoring output contract,
- structured explanation payload contract,
- promotion threshold references.

---

## 1) Scoring Output Contract (`advanced_v2`)

For each scored listing:

- `job_id` (int)
- `listing_id` (int)
- `score` (float, 0-100)
- `confidence` (float, 0-1)
- `deal_reason` (short string)
- `model_version` (string, expected: `advanced_v2`)
- `explanation` (JSON object, schema below)

Backward compatibility:
- `baseline_v1` output remains supported in parallel.

---

## 2) Explanation Payload Contract

Expected top-level shape:

```json
{
  "summary": {
    "primary_driver": "price_vs_comp_median",
    "confidence_note": "Data completeness acceptable",
    "fallbacks_used": ["city"]
  },
  "signals": [
    {
      "name": "price_vs_comp_median",
      "raw_value": -0.14,
      "normalized_score": 0.81,
      "weight": 0.32,
      "weighted_contribution": 0.2592
    }
  ],
  "comps_context": {
    "segment_level": "suburb",
    "cohort_size": 18,
    "fallback_path": ["suburb", "city", "province", "global"]
  },
  "roi_assumptions": {
    "transaction_cost_pct": 0.08,
    "vacancy_allowance_pct": 0.05,
    "maintenance_pct": 0.04,
    "management_pct": 0.08
  },
  "risk_flags": [],
  "missing_fields": []
}
```

Contract rules:
- `signals` must align with score math and contain at most configured top contributors.
- `comps_context.cohort_size` must reflect actual cohort after self-exclusion.
- `fallback_path` must preserve evaluation order used by resolver.

---

## 3) Promotion Threshold References

Phase 0 freeze references these default thresholds from:
- `docs/evaluation-review-protocol.md`
- `config/scoring.yaml` (`evaluation_thresholds`)

Current defaults:
- `evaluation_thresholds.stability.segments.top_band.jaccard_min = 0.70`
- `evaluation_thresholds.stability.segments.top_band.rank_correlation_min = 0.80`
- `evaluation_thresholds.stability.segments.top_band.perturbation_overlap_min = 0.60`
- `evaluation_thresholds.stability.segments.top_band.median_abs_rank_shift_pct_max = 0.15`
- `evaluation_thresholds.stability.segments.top_band.p90_rank_shift_pct_max = 0.60`
- `evaluation_thresholds.stability.full_dataset.median_abs_rank_shift_pct_warn_max = 0.35`
- `evaluation_thresholds.stability.full_dataset.p90_rank_shift_pct_warn_max = 0.80`

These thresholds gate promote/revert decisions for Week 2 scoring changes.

---

## 4) ROI Assumption Status (Important)

The ROI rates in Phase 0/1 config are MVP heuristic defaults for bootstrapping:
- `transaction_cost_pct`
- `vacancy_allowance_pct`
- `maintenance_pct`
- `management_pct`
- `insurance_pct`

They are **not** sourced as market-calibrated constants in this phase.

Expected progression:
1. Start with explicit defaults for deterministic behavior.
2. Validate and tune per target market/dataset during Week 2/4 evaluation loops.
3. Optionally augment with external data or guarded LLM estimates only after thresholded validation.

---

## 5) Scope Guardrail

This contract is only for Week 2 scoring and reasoning outputs.

It intentionally excludes:
- Week 3 dashboard/API strategy workflow contracts,
- multi-provider external integrations,
- default-on LLM scoring influence.
