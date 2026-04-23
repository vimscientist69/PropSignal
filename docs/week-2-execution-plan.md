# Next Phase Execution Plan (Implementation Order)

This is the practical execution sequence for the next feature branch, optimized for speed and low risk.

## Scope for This Branch:

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

Goal in simple terms:
- Before we trust `advanced_v2`, we need a repeatable "quality referee" that checks data health, score sanity, ranking stability, and explanation integrity.
- If checks pass, we can promote; if critical checks fail, we revert; if mixed, we keep the change experimental.

### Phase 3.1 Automated Quality Checks (required baseline)

What this means (simple):
- Every evaluation run should generate a machine-readable report saying pass/warn/fail for required gates.
- This removes guesswork and reduces intuition-only release decisions.

Implementation steps:
1. Define a scoring evaluation report schema that includes:
   - run metadata (job_id, model_version, config/threshold snapshot, timestamp)
   - gate results (data quality, scoring sanity, stability, explainability)
   - final decision and rationale (`promote` / `revert` / `experimental`)
2. Implement gate calculations aligned to `docs/evaluation-review-protocol.md`:
   - data quality: valid rate, duplicate rate, null-rate checks
   - scoring sanity: score bounds, impossible top-ranked record checks, signal dominance cap
   - explainability: explanation present and score-math consistency checks for top-N
3. Persist the evaluation artifact in a predictable path:
   - `output/evaluations/<run_id>/scoring_evaluation.json`
4. Keep thresholds configurable (from `config/scoring.yaml`) with safe defaults.

### Phase 3.2 Stability Checks (required release gate)

What this means (simple):
- If tiny config changes completely reshuffle rankings, the model is too fragile.
- Stability checks tell us whether ranking behavior is reliable enough to ship.

Implementation steps:
1. Add segment overlap + ordering metrics:
   - compute Jaccard overlap and rank correlation for:
     - `top_band` (critical)
     - `middle_band` (warning)
     - `bottom_band` (warning)
   - compare against config thresholds under `evaluation_thresholds.stability.segments`
2. Add rank displacement metrics (global-rank based):
   - compute `median_abs_rank_shift` and `p90_rank_shift` for shared listings
   - compute normalized forms `median_abs_rank_shift_pct` and `p90_rank_shift_pct`
   - gate on normalized (`*_pct`) thresholds so behavior scales across dataset sizes
3. Add weight perturbation sensitivity for top band:
   - run controlled +/-5% to +/-10% weight perturbation experiments
   - measure whether top ranking collapses beyond acceptable limits
4. Add full-dataset displacement context:
   - compute global displacement metrics for full dataset
   - treat full-dataset displacement breaches as warning-level context
5. Store all stability metrics in the same evaluation artifact for auditability.

### Phase 3.3 Release Decision Output (promote/revert/experimental)

What this means (simple):
- We need one clear answer at the end of each run: ship it, roll it back, or keep testing.

Decision logic:
1. `promote` if all required automated gates pass and no critical failures exist.
2. `revert` if any critical gate fails (data quality hard fail, severe instability, or broken explainability).
3. `experimental` if results are mixed (non-critical warnings, marginal stability, or pending manual review).

Output requirements:
- Include machine-readable fields:
  - `decision`
  - `decision_reasons[]`
  - `failed_gates[]`
  - `warning_gates[]`
  - `recommended_next_actions[]`

### Code Changes Required (implementation checklist)

Create/modify these files during implementation:

1. **Evaluation service**
   - Create: `backend/app/services/scoring_evaluation.py`
   - Responsibility:
     - load scored results for current and reference runs
     - compute gate metrics + pass/warn/fail statuses
     - compute final decision output
     - write evaluation artifact to `output/evaluations/<run_id>/`

2. **Dataset validation integration**
   - Modify: `backend/app/services/dataset_validation.py`
   - Responsibility:
     - expose reusable data quality metrics for evaluation gates
     - align threshold usage with config-driven defaults where applicable

3. **Scoring config thresholds**
   - Modify: `config/scoring.yaml`
   - Add/confirm:
     - data quality thresholds (valid/duplicate/null rate)
     - stability thresholds (segment overlap, rank correlation, displacement)
     - sensitivity thresholds (acceptable perturbation drift)
     - gate severity mapping (critical `top_band` vs warning-level non-top/full-dataset)

4. **CLI entrypoint (CLI-first workflow)**
   - Modify: `backend/app/cli.py`
   - Add:
     - `evaluate-scoring` command (or equivalent) that runs evaluation and prints decision summary
   - Keep:
     - output concise for terminal use and deterministic for automation

5. **Tests**
   - Update/Create:
     - `backend/tests/test_dataset_validation_service.py`
     - `backend/tests/test_scoring_algorithms.py`
     - `backend/tests/test_scoring_service.py`
     - `backend/tests/test_scoring_v2_evaluation.py` (new)
   - Cover:
     - metric correctness for segment overlap/correlation/displacement
     - perturbation sensitivity behavior for stable vs unstable cases
     - decision classification (`promote`/`revert`/`experimental`)
     - artifact shape and required fields

### Phase 3 Done Criteria (review gate before moving to Phase 4)

- Automated evaluation report is generated from CLI for a scoring run.
- Stability metrics are present and thresholded.
- Decision output is deterministic for identical inputs/config.
- Tests cover gate calculations and decision branching.
- Docs remain aligned with:
  - `docs/evaluation-review-protocol.md`
  - `docs/week2-interface-contract.md`
  - `docs/week2-implementation-playbook.md`

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
