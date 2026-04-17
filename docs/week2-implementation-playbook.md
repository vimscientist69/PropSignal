# Week 2 Implementation Playbook

This is the single Week 2 implementation document that combines:
- plain-language intent (why each feature matters),
- code-level change map (what files to change),
- chronological execution order (how to implement safely).

It merges and supersedes the intent of:
- `docs/week-2-execution-plan.md`
- `docs/week2-advanced-scoring-explained.md`

---

## 1) Week 2 Outcome

Deliver `advanced_v2` scoring that is:
- more locally accurate than baseline (micro-comps),
- closer to investor ROI priorities (yield + cost proxy),
- explainable per listing (structured reasoning),
- measurable with explicit evaluation gates.

Do **not** include Week 3 dashboard/API strategy UX revamp in this branch.

---

## 2) Scope (In / Out)

## In scope

- Advanced scoring service (`advanced_v2`)
- Micro-comps signals with safe fallback
- ROI proxy signals (deterministic baseline)
- Structured reasoning payload
- Evaluation/stability gates and promotion decision output
- MVP performance safeguards for Week 2 query/compute paths

## Out of scope (for this branch)

- Full strategy-driven dashboard workflows
- Multi-provider external integrations
- Default-on LLM scoring influence (LLM remains optional/flagged)

---

## 3) Feature Intent (Simple)

## 3.1 Micro-comps

Use local comparables (suburb/city/province/property type/bed-bath buckets) so "cheap vs expensive" is judged in the correct local context.

## 3.2 ROI proxy

Estimate practical investment attractiveness with:
- transaction-cost adjustment,
- net-yield proxy using rent estimate and operating-cost assumptions.

## 3.3 Reasoning payload

Every score should be inspectable:
- concise reason string,
- structured machine-readable explanation for UI/exports/debugging.

## 3.4 Evaluation gates

Only promote scoring changes when quality and stability pass explicit thresholds.

---

## 4) Code-Level Change Map

## 4.1 Scoring core

- Update: `backend/app/services/scoring.py`
  - Add `advanced_v2` signal pipeline:
    - comps segmentation + fallback selection
    - price-vs-comp and ppsqm-vs-comp signals
    - ROI proxy signals (transaction cost + net yield baseline)
    - confidence/risk adjustments
  - Add anti-leakage logic:
    - exclude subject listing from its own comp cohort
    - minimum cohort size with fallback and confidence penalty
  - Keep idempotent run behavior for same job.

## 4.2 Scoring model persistence

- Update: `backend/app/models/score_result.py`
  - Keep existing fields.
  - Add structured explanation field (JSON), for example:
    - `explanation: dict[str, Any]`
  - Keep concise `deal_reason`.

- Add migration:
  - `backend/alembic/versions/<new_revision>_score_result_explanation.py`
  - Adds explanation JSON column and any required indexes.

## 4.3 Scoring config

- Update: `config/scoring.yaml`
  - Add Week 2 weights/rules sections:
    - comps settings (min cohort size, fallback order)
    - ROI settings (cost assumptions, rent heuristics)
    - stability/safety flags
  - Keep backward-compatible defaults.

## 4.4 CLI integration

- Update: `backend/app/cli.py`
  - Keep `score <job-id>` command.
  - Add optional score mode/profile flags if needed (minimal for Week 2).
  - Ensure output includes active model version.

## 4.5 Evaluation and validation integration

- Update: `backend/app/services/dataset_validation.py` (or add dedicated scoring-eval service)
  - Add stability metrics artifacts:
    - top-N overlap (Jaccard)
    - rank correlation
    - perturbation sensitivity summary
  - Emit promotion recommendation:
    - `promote` / `revert` / `experimental`.

## 4.6 Tests

- Update and extend:
  - `backend/tests/test_scoring_algorithms.py`
  - `backend/tests/test_scoring_service.py`
  - `backend/tests/test_dataset_validation_service.py`
  - add `backend/tests/test_scoring_v2_evaluation.py` (new)
- Test categories:
  - signal correctness
  - fallback logic
  - anti-leakage
  - explanation-score alignment
  - idempotency
  - stability gate calculations.

## 4.7 Docs updates (after implementation)

- Update:
  - `docs/cli-usage.md`
  - `docs/current-project-status.md`
  - `README.md` command/status snippets

---

## 5) Chronological Implementation Order

## Phase 0: Branch setup and guardrails (Day 0)

1. Create feature branch scoped to Week 2 core only.
2. Freeze interface expectations:
   - `advanced_v2` output schema
   - explanation payload schema
3. Confirm promotion thresholds from:
   - `docs/evaluation-review-protocol.md`.

Checkpoint:
- no Week 3 scope items in branch TODO.

## Phase 1: Scoring contract and config skeleton (Day 1)

1. Define signal contract and normalized ranges.
2. Extend `config/scoring.yaml` with Week 2 sections.
3. Add unit tests for config parsing defaults and overrides.

Checkpoint:
- config supports all planned signals/rules with safe defaults.

## Phase 2: Micro-comps engine (Days 1-2)

1. Implement segmented comp stats and fallback resolver.
2. Implement anti-leakage exclusion and cohort-size rules.
3. Add comp coverage counters for diagnostics.
4. Add tests for sparse cohorts and fallback correctness.

Checkpoint:
- comp signals correct on small deterministic fixtures.

## Phase 3: ROI proxy baseline (Days 2-3)

1. Add deterministic transaction-cost adjustment.
2. Add heuristic rent and net-yield proxy signals.
3. Guard against missing data and impossible values.
4. Add tests for edge cases and neutral defaults.

Checkpoint:
- ROI signals stable and bounded under sparse data.

## Phase 4: Reasoning payload and persistence (Day 3)

1. Add structured explanation payload model + migration.
2. Populate explanation for each scored listing.
3. Ensure concise reason and structured explanation remain aligned.
4. Add regression tests for explanation integrity.

Checkpoint:
- top-ranked listings include complete explanations.

## Phase 5: Evaluation/stability gates (Day 4)

1. Implement top-N overlap and rank correlation metrics.
2. Implement perturbation sensitivity checks.
3. Produce clear go/no-go decision artifact per run.
4. Add tests for metric calculation correctness.

Checkpoint:
- scoring run outputs promotion recommendation deterministically.

## Phase 6: Performance baseline (Day 4-5)

1. Apply `docs/mvp-performance-plan.md` checklist for Week 2 paths.
2. Benchmark:
   - single dataset path
   - multi-dataset selection path
3. Record SLO compliance and bottlenecks.

Checkpoint:
- no critical unindexed query path for core ranking filters.

## Phase 7: Validation cycle and branch wrap-up (Day 5)

1. Run one full manual review cycle (top/mid/bottom samples).
2. Tune one controlled change bundle.
3. Re-run gates and confirm release status.
4. Update status docs and handoff notes.

Checkpoint:
- branch passes definition of done and is ready to merge.

---

## 6) Week 2 Definition of Done

- `advanced_v2` scoring implemented and tested.
- micro-comps + ROI proxy signals active with bounded behavior.
- explanation JSON payload persisted and consistent with score math.
- evaluation gates produce reproducible promote/revert output.
- baseline performance measured with documented SLO result.
- docs updated with usage and known follow-ups.

---

## 7) Risks and Mitigations

1. **Risk:** Overpacked scope delays branch.
   - **Mitigation:** keep LLM scoring influence gated/off by default.
2. **Risk:** unstable rankings from noisy signals.
   - **Mitigation:** enforce stability gates and contribution caps.
3. **Risk:** incorrect comp cohorts.
   - **Mitigation:** anti-leakage + minimum cohort constraints + tests.
4. **Risk:** explainability drift from score math.
   - **Mitigation:** explanation-score consistency tests.

---

## 8) After Week 2

When this branch merges:
- start Week 3 strategy-driven API/dashboard implementation,
- reuse Week 2 scoring profiles and explanation schema as stable contracts.

