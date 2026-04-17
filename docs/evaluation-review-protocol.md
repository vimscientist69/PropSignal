# Evaluation and Review Protocol

This document defines how to evaluate and review scoring quality in a repeatable way, even without deep real-estate domain expertise.

It is designed for:
- manual reviewer guidance,
- automated validation checks,
- optional LLM-assisted review support,
- and release promotion/revert decisions.

---

## 1) Purpose

Ensure ranking outputs are:
- accurate enough to be useful for investors,
- stable across runs and tuning changes,
- explainable and auditable,
- safe to ship without hidden regressions.

---

## 2) Review Modes

Use all three modes together:

1. **Automated review (required)**
   - hard checks and thresholds.
2. **Manual review (required)**
   - structured checklist on sampled listings.
3. **LLM-assisted review (optional)**
   - helper for consistency and summarization, not final authority.

---

## 3) Dataset and Run Setup

For each evaluation cycle:
- choose dataset(s): latest real data + at least one stable reference dataset.
- run ingestion, scoring, and analytics end-to-end.
- store run metadata:
  - dataset id/name/version
  - scoring profile and model version
  - config version / weight profile version
  - run timestamp and commit SHA

Keep all comparisons run-to-run on equivalent filters and strategy profile.

---

## 4) Automated Review Requirements (Required)

## 4.1 Data quality gates

- valid rate above minimum threshold
- no critical schema drift unaddressed
- duplicate rate within tolerance
- required field null rates within tolerance (especially price/location/type)

Suggested defaults (adjust later):
- valid_rate >= 0.85
- duplicate_rate <= 0.05
- price_null_rate <= 0.10

## 4.2 Scoring sanity gates

- score range uses expected bounds (0-100)
- no impossible top-ranked records (for example, missing price with high score)
- no single-signal dominance above configured cap

## 4.3 Stability gates

- top-N overlap vs previous version/run
- rank correlation across full set
- controlled sensitivity under weight perturbation (+/-5 to 10%)

Suggested defaults:
- top20_jaccard >= 0.70
- rank correlation >= 0.80
- no severe rank collapse from minor weight changes

## 4.4 Explainability gates

- explanation payload present for top-N listings
- top signal contributions match score math
- confidence and missing-field notes present when applicable

---

## 5) Manual Review Protocol (Required)

## 5.1 Sampling

Per strategy profile (`rental`, `resale`, `refurbishment`, `balanced`):
- review top 20
- review middle 20
- review bottom 20

If dataset is small, use at least:
- top 10 / middle 10 / bottom 10.

## 5.2 Manual checklist per listing

For each sampled listing, assess:

1. **Ranking plausibility**
   - Does rank roughly match available evidence?
2. **Comps correctness**
   - Are selected comparables reasonable for location/type?
   - Was fallback path sensible?
3. **ROI signal plausibility**
   - Are rent/cost assumptions realistic enough for this segment?
4. **Explanation quality**
   - Is the reason understandable and aligned with actual signals?
5. **Confidence alignment**
   - Does confidence reflect data completeness and uncertainty?
6. **Risk flags**
   - Any major risk omitted or understated?

Score each dimension:
- Pass / Concern / Fail

Record short notes with evidence.

## 5.3 Manual review output

For each strategy profile, publish:
- pass rate
- top recurring failure patterns
- examples of false positives and false negatives
- recommended tuning actions

---

## 6) LLM-Assisted Review Protocol (Optional)

Use LLM only as a reviewer assistant, not as final decision authority.

Allowed LLM tasks:
- summarize manual reviewer notes
- detect checklist omissions
- flag explanation inconsistencies
- propose candidate tuning hypotheses

Not allowed as sole basis for:
- promotion decisions
- truth-label assignment
- critical risk acceptance

LLM safeguards:
- provide structured input schema
- require machine-readable output schema
- keep deterministic fallback if LLM output is invalid/low-confidence
- preserve all prompts/outputs for audit logging

---

## 7) Promotion/Revert Decision Rules

Promote scoring/profile change only if:
1. all automated required gates pass,
2. manual review passes minimum threshold,
3. no critical failure mode introduced,
4. explanation correctness remains acceptable.

Revert or keep experimental if:
- any critical gate fails,
- false-positive behavior worsens materially,
- top-N quality degrades for target strategy,
- rank instability rises beyond threshold.

---

## 8) Iteration Loop (Weekly Cadence)

1. run ingestion + scoring + analytics
2. run automated checks
3. run manual sampled review
4. run optional LLM-assisted summarization
5. propose one controlled tuning bundle
6. rerun evaluation
7. decide promote/revert
8. log outcomes and decisions

Change only one tuning bundle at a time where possible.

---

## 9) Minimum Required Artifacts Per Cycle

- validation report (data quality + drift + duplicates)
- scoring metrics report (quality + stability + sensitivity)
- manual review notes with sample IDs
- decision record:
  - keep/revert
  - rationale
  - changed parameters
  - owner and timestamp

Store artifacts in a predictable path (for example `output/evaluations/<run_id>/`).

---

## 10) Example Review Template

Use this lightweight template per cycle:

```text
Run ID:
Dataset:
Strategy Profile:
Model/Profile Version:

Automated Gates:
- Data quality: Pass/Fail
- Scoring sanity: Pass/Fail
- Stability: Pass/Fail
- Explainability: Pass/Fail

Manual Review Summary:
- Top sample pass rate:
- Middle sample pass rate:
- Bottom sample pass rate:
- Key concerns:

LLM-Assisted Notes (optional):
- Consistency flags:
- Suggested hypotheses:

Decision:
- Promote / Revert / Keep Experimental
- Rationale:
- Next actions:
```

---

## 11) Practical Notes for This Project

- Because domain expertise is still developing, prioritize:
  - explicit checklists,
  - stable thresholds,
  - auditable decision logs.
- This process is intended to reduce intuition-only changes and improve reliability over time.
- As domain knowledge grows, update strategy-specific thresholds and heuristics carefully.

