# Week 2 Advanced Scoring Explained (Simple Version)

This document explains the Week 2 plan in plain language: what each part means, why it matters, and how it works.

## What "comps" means

Comps means **comparables**.

In property terms, comps are listings that are similar enough to compare against:
- similar area (suburb/city/province)
- similar property type (house/apartment/etc.)
- similar size/features (beds, baths, floor size when available)

We use comps to answer: "Is this listing expensive or cheap **for this local segment**?"

### Comps coverage

Comps coverage means: for how many listings we had enough data to use:
- suburb-level comps (best),
- city-level comps (fallback),
- province-level comps (fallback),
- global comps (last fallback).

Higher local comps coverage generally means better pricing accuracy.

## Week 2 goal

Build an ROI-first scoring system that is:
- more accurate than Week 1 baseline,
- explainable (not a black box),
- measurable (we can prove it improved),
- scope-controlled (no endless feature creep).

---

## 1) Advanced scoring system (v2)

### 1.1 Micro-comps pricing signals

### Why this matters
Week 1 used broad medians. That can be misleading because markets differ by area and property type.

### How it works
- Group listings into local segments (suburb/type/beds/baths).
- Compute local medians.
- Compare each listing against its segment median.
- If segment is too small, fallback: suburb -> city -> province -> global.

### Core signals
- `price_vs_comp_median`
- `price_per_sqm_vs_comp_median` (if `floor_size` exists)

---

### 1.2 ROI proxy signals

These are practical approximations of investment return, without building a full financial model.

#### Transaction-cost adjustment
- Purchase price is not the full cost.
- Add upfront cost assumptions (transfer/legal/etc.) to get a truer acquisition cost.

#### Net-yield proxy
- Estimate annual rent.
- Subtract operating costs (levies/rates/vacancy/maintenance assumptions).
- Compute yield-like return signal.

This helps rank listings by likely cashflow attractiveness.

---

### 1.3 Liquidity and risk adjustments

### Why this matters
Some properties are easier to buy/sell/rent than others. Missing or weak data also increases uncertainty.

### How it works
- Improve time-on-market signal with a better curve (avoid over-rewarding very stale listings).
- Keep separate notions of:
  - `data_confidence` (how complete/reliable the record is),
  - `investment_risk` (risk-related listing characteristics).

---

### 1.4 Scoring versioning

Keep baseline and advanced versions side by side:
- `baseline_v1`
- `advanced_v2`

This allows comparison and rollback.

---

## 2) Reasoning engine (explainability)

### Why this matters
A score without explanation is hard to trust and hard to debug.

### How it works
For each listing, store:
- short summary reason (`deal_reason`),
- structured explanation JSON (top drivers, raw values, normalized contributions, confidence notes).

This supports future UI details and auditing.

---

## 3) Analytics engine (quality and insight)

### Why this matters
Without analytics, we cannot prove Week 2 improved anything.

### How it works
Generate per-job summaries:
- score distribution stats,
- top-N listing summaries with key drivers,
- missingness report on critical fields,
- comps coverage report,
- ranking sanity/stability checks.

---

## 4) LLM enrichment prototype (optional, gated)

### Why this matters
Important details are often hidden in descriptions (condition, upgrades, amenities, rental clues).

### How it works
- Use LLM to extract a small set of pre-set high-value features from description text.
- Store enrichment in a separate payload.
- Only influence scoring behind an experiment flag until validated.

### Gate
Enable by default only if offline evaluation shows clear improvement and stability.

---

## 5) Evaluation and gates (scope control)

Compare `baseline_v1` vs `advanced_v2` on:
- top-N quality sanity,
- missing-data behavior,
- comps usage quality,
- stability under weight changes.

If changes do not improve measurable outcomes, they do not become default.

---

## Suggested implementation order

1. Micro-comps computation and comp-based pricing signals  
2. ROI proxy (transaction costs + yield proxy)  
3. Reasoning payload format  
4. Analytics summaries + evaluation checks  
5. LLM enrichment prototype + decision gate

---

## Brainstormed future enhancements

These are good ideas and should be tracked as future design options.

### A) LLM-derived upfront cost estimates for ROI proxy

Idea:
- Instead of a static transaction-cost %, use LLM + listing context to estimate likely upfront costs.

Potential approach:
- Extract cues from structured fields + description.
- Produce cost components with confidence score.
- Use as optional override or adjustment to config defaults.

Guardrail:
- Keep deterministic fallback (config static %) when confidence is low.

---

### B) Turn this into a configurable investor tool

Idea:
- Users upload/select a dataset, apply filters, and choose ranking mode by strategy.

Possible strategy presets:
- Rental income focus (cashflow/yield)
- Resale/arbitrage focus
- Refurbishment/value-add focus
- Balanced long-term hold

Possible controls:
- location filters (province/city/suburb)
- budget range
- risk tolerance
- confidence threshold
- strategy-specific weights

---

### C) Rich per-listing detail output

Idea:
- Keep short reasons, but also produce detailed listing-level diagnostics.

Useful future fields:
- full signal breakdown
- comps segment used and fallback path
- yield assumptions used
- risk/confidence flags
- ranking sensitivity notes (which factors changed rank most)

This will make the system much more useful for serious investors and future UI workflows.
