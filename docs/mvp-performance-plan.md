# MVP Performance Plan

This document defines practical optimizations for the MVP so the system remains responsive as datasets grow and users select multiple datasets in the admin tool.

## Goals

- Keep implementation simple enough for current timeline.
- Avoid expensive redesigns before value is proven.
- Deliver acceptable speed for ranking/filtering on 10k+ listings.

## Non-Goals (MVP)

- Full distributed compute.
- Real-time stream processing.
- Complex geospatial engines.
- Multi-region/tenant sharding.

---

## 1) Key Performance Risks

1. Recomputing heavy aggregates repeatedly (comps, medians, yields).
2. Query explosion when users select multiple datasets.
3. Slow top-N retrieval due to missing indexes and over-wide payload loading.
4. Re-scoring entire datasets on small filter changes.
5. UI waiting on synchronous long-running jobs.

---

## 2) MVP Optimization Strategy

## 2.1 Compute once, reuse often

- Materialize reusable run-level artifacts:
  - comps statistics by segment
  - signal intermediates where cheap to persist
  - ranking run metadata and summary stats
- Reuse precomputed artifacts for filtering and ranking retrieval.

## 2.2 Multi-dataset selection optimization

- Represent selected datasets as explicit `job_id` set.
- Query with indexed `job_id` filters first, then apply secondary filters.
- For multi-source merge mode:
  - use canonical listing identity rules
  - dedupe before ranking computation
  - track provenance fields for diagnostics.

## 2.3 Query-path optimization

- Add/verify indexes for common filters:
  - `job_id`
  - location fields (`province`, `city`, `suburb`)
  - `property_type`
  - score sort path
- Use pagination on all ranking list responses.
- Avoid loading large JSON payload columns unless requested (detail view only).

## 2.4 Incremental recompute where possible

- On filter-only changes: do not recompute full scoring.
- Recompute scoring only when:
  - profile/weights/signals change
  - source dataset changes
  - enrichment mode changes.

## 2.5 Background execution + responsiveness

- Run heavy ingestion/scoring/validation jobs asynchronously.
- Expose job status APIs and UI polling.
- Surface freshness metadata:
  - last_ingested_at
  - last_scored_at
  - score_version/profile_version

---

## 3) MVP SLO Targets (Initial)

These are practical targets to guide implementation and tuning:

- ranking list API p95 <= 800ms (cached/precomputed path)
- filtered ranking API p95 <= 1200ms
- listing detail API p95 <= 500ms
- scoring run completion <= 10 minutes for 10k listings on dev-grade hardware
- dataset validation run <= 5 minutes for 10k listings

Adjust after first benchmark pass.

---

## 4) Caching Plan (Simple and Safe)

- Cache only deterministic, versioned artifacts:
  - ranking results keyed by `(job_set, strategy_profile, filter_hash, model_version)`
  - comps statistics keyed by `(job_id, segmentation_version)`
- Invalidate cache on:
  - dataset/job change
  - profile/weight change
  - score model version change.

---

## 5) Data Model and API Guidelines for Performance

- Keep list responses lean:
  - score, confidence, core fields, concise reason
- Fetch detailed explanation payload only in detail endpoint.
- Persist run metadata for reproducibility and quick diagnostics.
- Track selected dataset count and merged record count for observability.

---

## 6) Instrumentation and Benchmarking

For each major endpoint/job stage, capture:
- duration
- rows scanned/returned
- cache hit/miss
- error rate

Minimum benchmark matrix:
- 1 dataset (small)
- 1 dataset (10k+)
- multi-dataset selection (3-5 datasets)
- worst-case broad filters vs narrow filters

---

## 7) Execution Order (Performance Work in MVP)

1. Add indexes and lean query contracts.
2. Add async job status flow.
3. Add precomputed comps/ranking artifacts.
4. Add deterministic caching with invalidation.
5. Benchmark and tune against SLOs.

---

## 8) Exit Criteria

MVP performance work is complete when:
- SLOs are met or known gaps have explicit follow-up tasks.
- Multi-dataset selection remains responsive under expected load.
- No blocking query path is left unindexed for core filters/sorts.
- Performance dashboards/logs can identify bottlenecks quickly.
