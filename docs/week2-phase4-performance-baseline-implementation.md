# Week 2 Phase 4 Implementation Doc: Performance Baseline

This document defines exactly what to implement for Phase 4 in Week 2:

- establish a repeatable performance baseline,
- record measurable evidence,
- avoid premature optimization work that belongs in Week 3/4.

Canonical phase reference: `docs/week-2-execution-plan.md` (Phase 4).

---

## 1) Goal

Create a deterministic, CLI-first baseline run that measures core pipeline timings and writes machine-readable artifacts for later comparison.

This phase is measurement-first, not optimization-first.

---

## 2) Scope

### In Scope (Week 2)

1. Run baseline timings for core pipeline stages:
   - ingest
   - score
   - validate-dataset
   - evaluate-scoring
2. Support baseline runs for:
   - single dataset
   - multi-dataset proxy (run multiple datasets in one benchmark invocation)
3. Record and persist:
   - per-stage durations
   - p50/p95 stage durations
   - SLO assessment (met/missed/deferred)
   - unresolved bottlenecks and follow-up actions
4. Expose as one CLI command.

### Out of Scope (defer to Week 3/4)

- query/index refactors
- API latency optimization
- async orchestration and job status APIs
- caching/invalidation framework
- large-scale performance tuning loops

---

## 3) Deliverables

1. New service:
   - `backend/app/services/performance_baseline.py`
2. New CLI command:
   - `benchmark-baseline` in `backend/app/cli.py`
3. Generated artifacts:
   - `output/performance/<run_id>/baseline_metrics.json`
   - `output/performance/<run_id>/baseline_summary.md`
4. Tests:
   - `backend/tests/test_performance_baseline.py`

---

## 4) CLI Contract

Command:

- `benchmark-baseline`

Suggested options:

- `--dataset <path>` (repeatable, required)
- `--top-n <int>` (optional, default 20)
- `--output-dir <path>` (optional; default `output/performance/<run_id>/`)

Example:

- `./scripts/cli-local.sh benchmark-baseline --dataset "/abs/path/a.json" --dataset "/abs/path/b.json" --top-n 20`

---

## 5) Execution Flow

For each dataset path:

1. Ingest dataset and capture duration.
2. Score the produced job and capture duration.
3. Validate dataset and capture duration.
4. Evaluate scoring and capture duration.
   - Week 2 baseline mode can use `reference_job_id = job_id` for deterministic smoke measurement.
5. Collect paths to generated validation/evaluation artifacts.
6. Append stage timings into run-level aggregation.

After all datasets:

1. Compute run-level p50/p95 per stage.
2. Build SLO assessment:
   - met
   - missed
   - deferred (for API or optimization-heavy SLOs not in Week 2 scope)
3. Write JSON + Markdown summary artifacts.
4. Print concise terminal summary with output paths.

---

## 6) Input and Output Shapes

### Input (CLI)

- `datasets: list[str]`
- `top_n: int` (optional)
- `output_dir: str` (optional)

### Output (`baseline_metrics.json`)

Top-level schema (minimum):

- `run_id: str`
- `timestamp_utc: str`
- `scope: "week2_phase4_minimal_baseline"`
- `datasets: list[dataset_result]`
- `aggregate: { stage_stats }`
- `slo_targets: { ... }`
- `slo_assessment: { met: [], missed: [], deferred: [] }`
- `bottlenecks: list[str]`
- `week3_week4_followups: list[str]`

`dataset_result` minimum:

- `dataset_path: str`
- `job_id: int | null`
- `durations_s: { ingest, score, validate_dataset, evaluate_scoring }`
- `artifacts: { validation_report_path, evaluation_report_path }`
- `status: "pass" | "warn" | "fail" | "error"`
- `error: str | null`

### Output (`baseline_summary.md`)

Human-readable summary with:

- run metadata
- per-stage p50/p95
- SLO status by item
- unresolved bottlenecks
- explicit Week 3/4 follow-ups

---

## 7) SLO Handling for Week 2

Use `docs/mvp-performance-plan.md` targets as references, but classify by implementation feasibility:

- CLI pipeline timing targets: evaluate directly (score/validation duration targets).
- API p95 targets: mark as deferred if API benchmark harness is not in Week 2 scope.

This keeps the baseline honest without forcing premature architecture work.

---

## 8) Automation Details

Automation is complete when one command:

- runs all selected datasets end-to-end,
- records stage timings,
- computes p50/p95,
- writes both artifacts,
- exits non-zero only on command/runtime errors (not on SLO misses).

SLO misses should be reported in artifacts, not treated as process crashes.

---

## 9) Code Change Checklist

1. Add `performance_baseline.py` service with:
   - orchestration logic
   - timing collection (`time.perf_counter`)
   - percentile helper
   - artifact writers
2. Add `benchmark-baseline` CLI command in `backend/app/cli.py`.
3. Add tests for:
   - single dataset run
   - multi-dataset run
   - artifact structure
   - p50/p95 aggregation behavior
4. Update docs references if command is surfaced in README/CLI docs.

---

## 10) Acceptance Criteria (Phase 4 Done, Week 2 Minimal)

Phase 4 is considered done when:

1. `benchmark-baseline` exists and is runnable from CLI.
2. It supports one or many datasets in one run.
3. It produces:
   - `baseline_metrics.json`
   - `baseline_summary.md`
4. Artifacts include:
   - per-stage durations
   - p50/p95 by stage
   - SLO met/missed/deferred
   - unresolved bottlenecks
5. Follow-up actions for Week 3/4 are explicitly captured.

---

## 11) Week 3/4 Handoff: Required Updates (Do Not Skip)

When ranking/list/detail APIs are implemented in Week 3/4, update the baseline implementation immediately.

### Files to update

1. `backend/app/services/performance_baseline.py`
2. `backend/app/cli.py`
3. `backend/tests/test_performance_baseline.py`
4. `docs/mvp-performance-plan.md` (if SLOs change)
5. `docs/week2-phase4-performance-baseline-implementation.md` (mark Week 3/4 handoff completed)

### Exact required changes

1. Replace API SLO placeholders from deferred to measured:
   - `ranking_list_api_p95_ms`
   - `filtered_ranking_api_p95_ms`
   - `listing_detail_api_p95_ms`
2. Add actual API benchmark execution in `run_performance_baseline`:
   - call ranking/list/detail endpoints (or dedicated benchmark client),
   - collect endpoint latency samples,
   - compute p50/p95 for each endpoint.
3. Remove API SLOs from `deferred` classification once benchmark harness exists.
4. Add dataset-size context to artifacts:
   - `records_total`
   - `records_valid`
   - throughput fields (for example rows/sec) for score/validation stages.
5. Extend summary output to include API p95 result lines and pass/fail status.
6. Add tests that assert:
   - API latency metrics are present in `aggregate`,
   - API SLOs are assessed under `met`/`missed` (not always deferred),
   - dataset-size and throughput fields are written.

### Completion signal

Week 3/4 handoff is complete only when `baseline_metrics.json` contains measured API latency stats and API SLOs are no longer unconditionally deferred.