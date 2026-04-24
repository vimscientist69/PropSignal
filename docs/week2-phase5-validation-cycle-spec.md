# Week 2 Phase 5 Spec: Validation Cycle and Release Decision

This spec operationalizes Phase 5 from `docs/week-2-execution-plan.md`:

1. run one full validation cycle,
2. apply one controlled change set,
3. rerun and evaluate against baseline,
4. freeze profile/version and document release decision.

---

## 1) Scope

- Dataset: `data/samples/propflux_pp_1000_listings.json`
- Baseline run: ingest + score + validate-dataset (evaluation deferred until comparison step)
- Controlled change: exactly one scoring config bundle
- Candidate run: ingest + score + validate-dataset
- Evaluation: candidate vs baseline
- Finalization: freeze or revert + decision record

Out of scope:

- multi-bundle tuning in a single cycle
- architecture/performance refactors
- Week 3/4 API enhancements

---

## 2) Execution Steps

### Step A: Baseline run

Run:

- `ingest <dataset>`
- `score <baseline_job_id>`
- `validate-dataset <baseline_job_id>`

Capture:

- baseline job ID
- validation report path
- notable quality warnings/errors

### Step B: Controlled change set (single bundle)

Apply one bounded, auditable scoring change:

- allowed: weight-only or threshold-only bundle
- disallowed: mixed refactors and multiple independent tuning bundles

Record:

- exact before/after values
- rationale

### Step C: Candidate run

Run same pipeline on same dataset:

- `ingest <dataset>`
- `score <candidate_job_id>`
- `validate-dataset <candidate_job_id>`

Capture candidate artifacts.

### Step D: Evaluation compare

Run:

- `evaluate-scoring <candidate_job_id> --reference-job-id <baseline_job_id> --top-n 20`

Capture:

- decision
- failed/warning gates
- report path

### Step E: Finalization

- If decision is `promote`: freeze changed profile/version.
- If decision is `revert`: rollback controlled change set and freeze previous profile.
- Write release decision record artifact.

---

## 3) Required Artifacts

Produce a decision record containing:

- dataset used
- baseline job ID + validation report path
- controlled change set details
- candidate job ID + validation report path
- evaluation report path and gate outcome
- final decision (`promote`/`revert`/`experimental`)
- freeze/rollback action taken
- follow-up tasks

---

## 4) Acceptance Criteria

Phase 5 is complete when:

1. baseline run completed and recorded,
2. one controlled change set applied and documented,
3. candidate run completed and recorded,
4. evaluation run completed with explicit decision,
5. profile/version frozen via promote freeze or revert rollback,
6. decision record artifact written.

---

## 5) Operational Notes

- Keep commands and dataset constant between baseline and candidate.
- If ancillary command paths fail (for example non-critical analytics command issues),
  continue required Phase 5 evaluation flow and document blocker in decision record.
- Prefer small reversible change bundles to maximize comparability.

