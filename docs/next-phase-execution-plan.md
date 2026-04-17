# Next Phase Execution Plan (Implementation Order)

This is the practical execution sequence for the next feature branch, optimized for speed and low risk.

## Scope for This Branch

Implement Week 2 core only:
- advanced scoring (`advanced_v2`)
- structured reasoning payload
- evaluation gates for promotion/revert

Do not include:
- Week 3 dashboard/API strategy UX revamp
- broad external integrations

## Ordered Work Plan

## Phase 1: Scoring Core (must ship first)

1. Finalize scoring signal contract:
   - micro-comps signals
   - ROI proxy signals
   - confidence/risk signals
2. Implement comp segmentation + fallback logic.
3. Add anti-leakage safeguards:
   - exclude subject listing from own comps
   - minimum cohort sizing and fallback penalties.
4. Implement deterministic ROI proxy baseline (no LLM dependency).

## Phase 2: Reasoning and Explainability

1. Define explanation payload schema.
2. Persist concise reason + structured explanation.
3. Add tests ensuring explanation and score math stay aligned.

## Phase 3: Evaluation Gates

1. Implement automated quality checks from `docs/evaluation-review-protocol.md`.
2. Add stability checks:
   - top-N overlap
   - rank correlation
   - weight perturbation sensitivity
3. Add release decision output:
   - promote / revert / experimental.

## Phase 4: Performance Baseline

1. Apply MVP performance checklist from `docs/mvp-performance-plan.md`.
2. Add benchmark run for:
   - single dataset
   - multi-dataset selection.
3. Record SLO compliance and unresolved bottlenecks.

## Phase 5: Validation Cycle and Wrap-Up

1. Run one full manual review cycle.
2. Tune one controlled change set.
3. Re-run evaluation.
4. Freeze profile/version and document release decision.

## Definition of Done for Branch

- `advanced_v2` scoring path implemented and tested.
- reasoning payload present and validated.
- evaluation gates produce go/no-go output.
- performance baseline measured against initial SLOs.
- branch docs updated with decisions and known follow-ups.

## Handoff to Next Branch

After this branch merges:
- start Week 3 strategy-driven API/dashboard implementation,
- reuse scoring profiles and explanation payload from this branch as stable contracts.
