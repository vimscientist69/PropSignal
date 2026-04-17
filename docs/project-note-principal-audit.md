# PROJECT_NOTE Principal Audit

This document captures a principal-engineering + product-lead audit of `@.cursor/rules/PROJECT_NOTE.md`, including:
- a reusable enhanced audit prompt,
- prioritized findings,
- and a must-fix checklist before production investor use.

## Enhanced Audit Prompt (Reusable)

Audit `@.cursor/rules/PROJECT_NOTE.md` as a **Principal Engineer + Product Lead** preparing this system for **real-world investor decisioning**.

### Objective
Identify everything missing, unclear, risky, or misaligned that could reduce:
- business value,
- decision accuracy,
- trust/explainability,
- maintainability,
- delivery speed.

### Review Dimensions

1. **Business/Product Alignment**
- Does each roadmap item tie to investor outcomes for `rental`, `resale/arbitrage`, `refurbishment/value-add`, and `balanced`?
- Are success metrics tied to decision quality and adoption (not just technical output)?
- Are user personas, core workflows, and “job to be done” explicit?
- Are assumptions about user behavior, risk tolerance, or data availability documented?

2. **Scoring/Analytics Correctness**
- Missing edge cases for sparse/skewed/noisy data, outliers, null-heavy segments, duplicates, and stale data.
- Leakage risks (self-inclusion in comps, future info leakage, cross-run contamination).
- Bias/calibration risks across cities/property types/price bands.
- Stability risks (weight sensitivity, rank churn, noisy top-N).
- Plausible-but-wrong failure modes and how they are detected.

3. **Reasoning/Explainability Quality**
- Is explanation format decision-grade (not just cosmetic)?
- Are uncertainty and missing-data impacts surfaced clearly?
- Can a user trace each score back to concrete signal inputs and assumptions?
- Is there an explanation QA rubric?

4. **Data/ML/LLM Risk Management**
- Data contract versioning, schema drift handling, and source provenance.
- LLM extraction risks: hallucination, confidence misuse, prompt injection, drift.
- Fallback behavior and guardrails when enrichment is low-confidence.
- Model/version governance and reproducibility.

5. **Architecture/Execution Feasibility**
- Scope realism by week (is timeline overpacked?).
- Dependency ordering and critical path clarity.
- Missing backend/API/CLI contracts for stated dashboard features.
- Operational readiness: background jobs, retries, idempotency, observability, rollback.

6. **Validation and Iteration Framework**
- Are offline/online evaluation metrics explicit and thresholded?
- Is there a clear “promote/revert” process for scoring/profile changes?
- Is there a repeatable tuning loop with decision logs?
- Are strategy-level acceptance criteria defined?

7. **Security/Compliance/Trust**
- Upload/API hardening, abuse handling, auth/authz, rate limits.
- PII handling (agent details), retention policy, access controls.
- Investor trust safeguards: disclaimer boundaries, confidence gating, audit trail.

8. **Documentation and Rules Completeness**
- Missing docs: runbooks, model cards, scoring profile specs, API contracts, failure playbooks.
- Missing project rules: migration safety, config change controls, feature flags, experiment governance.

### Output Format
- Findings prioritized by **Critical / High / Medium / Low**.
- For each: `Issue`, `Impact`, `Evidence`, `Recommendation`.
- Include a final section: **Top 10 must-fix before production investor use**.

---

## Audit Findings

### Critical

1. **No explicit business KPIs or acceptance thresholds by strategy mode**
- **Impact:** Cannot prove investor usefulness; tuning can optimize vanity metrics.
- **Evidence:** Week plans describe features and loops but not hard go/no-go thresholds per strategy.
- **Recommendation:** Define per-strategy release gates (e.g., precision@K, false-positive cap, trust threshold).

2. **Comps methodology lacks anti-leakage and reliability controls**
- **Impact:** Scores can appear correct while being statistically biased.
- **Evidence:** Micro-comps are defined without self-exclusion, minimum cohort sizing, or shrinkage rules.
- **Recommendation:** Add self-exclusion, minimum sample size, reliability weighting, and confidence penalties.

3. **LLM upfront-cost estimation lacks hard safety policy**
- **Impact:** Hallucinated costs can silently distort rankings.
- **Evidence:** LLM cost extraction is included, but no strict schema validation/calibration/fallback contract.
- **Recommendation:** Require typed schema, confidence calibration, and deterministic fallback below threshold.

4. **No explicit evaluation split protocol**
- **Impact:** Overfitting risk and false improvement claims.
- **Evidence:** Baseline vs v2 comparisons are requested, but no temporal/geographic holdout requirements.
- **Recommendation:** Add evaluation protocol with temporal + geography holdouts and fixed test slices.

### High

1. **Timeline is still overcompressed for production-grade scope**
- **Impact:** Delivery risk and quality debt.
- **Evidence:** Week 2 and 3 include advanced scoring, LLM, strategy tooling, API/CLI revamps, and diagnostics.
- **Recommendation:** Separate must-ship MVP from stretch goals with hard timeboxes.

2. **API contracts are under-specified for strategy workflows**
- **Impact:** Frontend/backend/CLI drift.
- **Evidence:** Endpoint intent exists, but contract schemas and behavior constraints are not explicit.
- **Recommendation:** Add request/response contract specs and deterministic sorting/pagination rules.

3. **No governance model for scoring profile changes**
- **Impact:** Silent ranking drift and trust erosion.
- **Evidence:** Presets and tuning are planned, but no profile registry, owners, or approval flow.
- **Recommendation:** Add profile versioning, change logs, approval gates, and rollback policy.

4. **Cross-source entity resolution strategy is missing**
- **Impact:** Duplicate/misaligned listings can corrupt comps and rankings.
- **Evidence:** Multi-source merge is planned without canonical identity resolution rules.
- **Recommendation:** Define entity resolution heuristics and confidence metrics with dedupe audits.

5. **No SLO/latency targets**
- **Impact:** UX and scalability risk at 10k–100k records.
- **Evidence:** Performance tuning is listed, but no explicit service targets.
- **Recommendation:** Add p95 latency and throughput goals for ranking, filtering, export, and validation jobs.

### Medium

1. **“Real-time updates per dataset” is ambiguous for a batch-heavy pipeline**
- **Impact:** Product expectation mismatch.
- **Recommendation:** Define update cadence and freshness semantics.
TIP: update when manually triggered in ui, but make it robust and optimised for performance.

2. **Reasoning quality lacks explicit QA rubric**
- **Impact:** Explanations may be verbose but not decision-useful.
- **Recommendation:** Add rubric for correctness, actionability, and uncertainty disclosure.

3. **Investor workflow assumptions are implicit**
- **Impact:** Risk of technically rich but decision-poor outputs.
- **Recommendation:** Add core user journeys for each strategy and required artifacts per journey.

4. **Security/compliance plan remains thin**
- **Impact:** Production-readiness gap.
- **Recommendation:** Add upload hardening, authz, rate limits, PII handling, and audit logging requirements.

5. **PDF export appears in output goals without explicit implementation plan**
- **Impact:** Hidden scope creep.
- **Recommendation:** Either defer PDF for MVP or define generation pipeline and quality criteria.
TIP: defer PDF for MVP

### Low

1. **Architecture section is partially stale vs current evolving code layout**
- **Impact:** Onboarding friction.
- **Recommendation:** Keep architecture map synchronized with implemented modules.

2. **Terminology is not fully normalized**
- **Impact:** Ambiguity in planning and execution.
- **Recommendation:** Add glossary for terms like `confidence`, `risk`, `resale/arbitrage`, `refurbishment`.

---

## Missing Docs / Rules to Add

- Model/scoring card per `model_version`
- Strategy profile specification (objective, signals, weights, guardrails)
- Evaluation protocol document (splits, metrics, thresholds, promotion/revert)
- Data provenance and schema-drift playbook
- Incident response runbook for ranking quality regressions
- Config/profile change governance rule (review + rollback required)

---

## Top 10 Must-Fix Before Production Investor Use

1. Define strategy-specific business KPIs and release thresholds.
2. Formalize leakage-safe comps methodology with confidence penalties.
3. Add deterministic evaluation split protocol (temporal + geo holdouts).
4. Add scoring profile governance (versioning, approval, rollback).
5. Lock API/CLI contracts for ranking and diagnostics.
6. Add strict LLM safety policy and deterministic fallback guarantees.
7. Define cross-source entity resolution and dedupe quality metrics.
8. Add performance SLOs and capacity targets.
9. Add security/compliance baseline (auth, uploads, PII retention, audit logs).
10. Publish model/scoring/evaluation docs for trust and maintainability.

