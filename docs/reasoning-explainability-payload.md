# Reasoning and Explainability Payload

This document defines the scoring explanation payload in `score_results.explanation`, including:
- what each field means,
- why it matters for investor trust and debugging,
- how to interpret it safely.

This payload complements (not replaces) the concise `deal_reason` string.

---

## Why this payload exists

A single score value is not enough for real decisioning. The explanation payload provides:
- **transparency** (why this listing ranked where it did),
- **auditability** (can we trace score math?),
- **debuggability** (which signal caused unexpected outcomes),
- **tuning feedback** (which assumptions or weights need adjustment).

---

## Top-level structure

Current payload shape:

```json
{
  "summary": {},
  "signals": [],
  "score_math": {},
  "comps_context": {},
  "roi_assumptions": {},
  "risk_flags": [],
  "missing_fields": []
}
```

---

## Field-by-field reference

## `summary`

### `summary.primary_driver` (string)
- **Meaning:** signal with the highest weighted contribution.
- **Importance:** quick explanation of the biggest reason for rank.
- **Example:** `"price_vs_comp"`

### `summary.confidence_note` (string)
- **Meaning:** short confidence interpretation based on completeness/quality.
- **Importance:** warns users when score reliability is reduced.
- **Example:** `"Limited metadata reduced confidence"`

### `summary.fallbacks_used` (array of strings)
- **Meaning:** fallback comparator levels used (`city`, `province`, `global`).
- **Importance:** indicates local comp quality; too many broad fallbacks reduce trust.
- **Example:** `["city"]`

---

## `signals` (array)

Each element represents one scoring signal.

### `signals[].name` (string)
- **Meaning:** signal identifier.
- **Importance:** ties contribution to specific model component.
- **Common values:** `price_vs_comp`, `size_vs_comp`, `time_on_market`, `feature_value`, `confidence`, `roi_proxy`

### `signals[].raw_value` (number)
- **Meaning:** numeric value used for this signal in current implementation.
- **Importance:** useful for low-level diagnostics and regression analysis.

### `signals[].normalized_score` (number, usually 0..1)
- **Meaning:** comparable normalized signal value prior to weighting.
- **Importance:** puts different signal types on common scale.

### `signals[].weight` (number)
- **Meaning:** configured signal importance.
- **Importance:** clarifies strategy bias and tuning intent.

### `signals[].weighted_contribution` (number)
- **Meaning:** contribution to weighted sum (`normalized_score * weight`).
- **Importance:** this is the direct impact on final score.

---

## `score_math`

### `score_math.weighted_sum_0_to_1` (number)
- **Meaning:** summed weighted contributions after clamp to model scale.
- **Importance:** canonical intermediate used to derive final score.

### `score_math.final_score_0_to_100` (number)
- **Meaning:** final persisted score shown to users.
- **Importance:** must match `score_results.score`.

---

## `comps_context`

### `comps_context.segment_level` (string or null)
- **Meaning:** comp level actually used (`suburb`, `city`, `province`, `global`), or `null` if no valid cohort.
- **Importance:** indicates locality quality of benchmark.

### `comps_context.cohort_size` (int)
- **Meaning:** comparable listing count after self-exclusion.
- **Importance:** small cohorts are less reliable.

### `comps_context.fallback_path` (array of strings)
- **Meaning:** configured fallback order attempted.
- **Importance:** explains how model searched for usable cohorts.

### `comps_context.fallback_penalty` (number)
- **Meaning:** penalty applied when broader fallback level used.
- **Importance:** discourages overconfidence on weak comp locality.

---

## `roi_assumptions`

### `transaction_cost_pct`, `vacancy_allowance_pct`, `maintenance_pct`, `management_pct`, `insurance_pct` (numbers)
- **Meaning:** assumptions used to compute ROI proxy.
- **Importance:** makes hidden financial assumptions explicit and reviewable.
- **Note:** these are MVP heuristic defaults until calibrated by market.

---

## `risk_flags` (array of strings)

- **Meaning:** explicit risk markers (for example `low_confidence`).
- **Importance:** quick screening for caution conditions.

---

## `missing_fields` (array of strings)

- **Meaning:** key data points unavailable for this listing.
- **Importance:** helps detect why score is neutralized/less reliable.
- **Examples:** `["price"]`, `["floor_size", "date_posted"]`

---

## Interpretation guidance

Use payload in this order:

1. Check `risk_flags` and `missing_fields`.
2. Check `summary.primary_driver` and `signals` ranking.
3. Confirm `comps_context.segment_level` and `cohort_size`.
4. Review `roi_assumptions` before acting on high ROI-driven scores.
5. Verify `score_math` alignment if debugging.

Do not treat a high score as high confidence if:
- comp level is too broad (`global`),
- cohort size is very small,
- missing fields are critical.

---

## Validation requirements

For each scored listing:
- `score_math.final_score_0_to_100` must equal stored `score`.
- Sum of `signals[].weighted_contribution` must equal `score_math.weighted_sum_0_to_1` (within rounding tolerance).
- `summary.primary_driver` must match top contribution signal.

---

## Future extensions (non-breaking)

Recommended additions:
- `version_meta` (model/profile/config revision IDs),
- uncertainty interval fields,
- strategy profile name and objective,
- external data provenance markers.

