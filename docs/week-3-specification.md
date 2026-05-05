
# Week 3 Detailed Specification

This document defines the Week 3 implementation scope as an execution-ready specification.
It turns the roadmap goals into concrete contracts for backend APIs, CLI behavior, persistence,
performance constraints, and test coverage.

## 1) Objective

Deliver the first production-usable strategy workflow across dashboard, API, and CLI:

- select one or more dataset sources,
- apply investor filters,
- resolve a strategy profile,
- produce ranked listings with rich diagnostics,
- access listing-level detail consistently from dashboard, API, and CLI.

Week 3 must preserve the Week 2 evaluation and scoring contracts while expanding access patterns.

## 2) Week 3 Scope

### In scope

- Strategy-aware ranking APIs.
- Dashboard strategy workflow UI (dataset selection, filters, strategy controls, ranked results, detail panel).
- Listing detail diagnostics API.
- Scoring profile discovery and resolution API.
- Query/filter pipeline that supports merged dataset-source selection.
- CLI commands that mirror API capabilities.
- Persist ranking-run metadata and retrieval-ready detail payload references.
- Performance baseline handoff update for API latency measurement.

### Out of scope (defer to Week 4)

- Major score-formula redesign.
- LLM-by-default rollout decisions.
- Large-scale tuning loops across many iterations.
- Full deployment hardening and operational playbooks.
- Broad external data-source integration beyond one controlled addition.

## 3) Product Behavior Requirements

### 3.0 Dashboard workflow requirements

Week 3 includes a functional dashboard experience, not just backend contracts.

Dashboard must provide:

- dataset handling:
  - upload/select dataset source(s),
  - source multi-select controls including `select_all` and `clear_all`,
  - current job status + validation summary panel.
- filter controls:
  - province/city/suburb,
  - budget range,
  - property type + bedrooms + bathrooms,
  - confidence threshold.
- strategy controls:
  - preset selector (`rental_income`, `resale_arbitrage`, `refurbishment_value_add`, `balanced_long_term`),
  - optional advanced weight overrides with safe-bound validation feedback,
  - reset control that restores defaults for the resolved preset for the current request.
- result surfaces:
  - ranked listing table/cards with score, deal reason, and core attributes,
  - detail panel/drawer showing full diagnostics payload for selected listing,
  - visible run metadata (`run_id`, profile version, model version, freshness).

Dashboard behavior constraints:

- all ranking submissions use the same request schema as `POST /api/v1/rankings/query`,
- dashboard input validation should mirror backend validation with user-friendly messages,
- results and detail views must be reproducible by run/listing IDs (shareable debugging path),
- no business-logic duplication in frontend; strategy/profile logic remains backend-owned.
- dashboard does not perform profile CRUD or preset alias remapping in Week 3.

### 3.1 Dataset selection behavior

- Users can choose one or more ingestion/scoring sources.
- Multi-source selection merges listings into one ranking input set.
- The system must expose freshness metadata per selected source:
  - `last_ingested_at`
  - `last_scored_at`
  - `model_version`
  - `profile_id` (resolved scoring profile identifier)

### 3.2 Filter behavior

Support these filter inputs for ranking:

- `province`, `city`, `suburb` (optional, combinable),
- budget range (`price_min`, `price_max`),
- property constraints (`property_type`, `bedrooms_min`, `bathrooms_min`),
- `confidence_min`,
- pagination (`page`, `page_size`) and/or `top_n`.

Filter validation rules:

- numeric bounds must be non-negative,
- `price_min <= price_max` when both set,
- `page >= 1`,
- `1 <= page_size <= 100` (default 20),
- `top_n` optional and capped (max 500),
- mutually compatible pagination contract:
  - if `top_n` is provided, return first `top_n` after filtering and scoring,
  - if pagination is provided, return paged results from filtered ranking set.

### 3.3 Strategy behavior

Week 3 strategy presets:

- `rental_income`
- `resale_arbitrage`
- `refurbishment_value_add`
- `balanced_long_term`

Resolution model:

- preset resolves to a profile with:
  - signal weights,
  - enabled/disabled signals,
  - profile metadata (`profile_id`).
- optional user overrides are allowed only within safe bounds:
  - weight change clamp per signal: +/-20% from preset,
  - resulting weight vector must normalize to 1.0.
- `preset_alias_mapping` is configured in `backend/config/scoring_profiles.yaml` and resolved server-side.
- override changes are request-scoped only and are not persisted as profile updates.

If override validation fails, reject request with explicit field-level reason.

## 4) API Specification

All endpoints should be thin controllers with service-layer orchestration.

### 4.1 Rank listings endpoint

`POST /api/v1/rankings/query`

Request body:

- `dataset_sources: string[]` (required, min 1),
- `filters: object` (optional but validated),
- `strategy: object` (required):
  - `preset: enum`,
  - `weight_overrides?: Record<string, number>`,
- `result_window: object`:
  - `top_n?: number`,
  - `page?: number`,
  - `page_size?: number`,
- `sort_mode: "score_desc"` (Week 3 fixed mode).

Response body:

- `run_id: string`,
- `query_fingerprint: string`,
- `resolved_profile`:
  - `profile_id`,
  - `resolved_weights`,
  - `enabled_signals`,
- `dataset_context`:
  - `selected_sources`,
  - `records_considered`,
  - freshness metadata,
- `results[]`:
  - `listing_id`,
  - `score`,
  - `deal_reason`,
  - `confidence`,
  - summary attributes (price, location, property type),
  - `detail_ref` (stable reference for detail retrieval),
- pagination metadata (`page`, `page_size`, `total_count`) or `top_n_count`.

### 4.2 Listing detail diagnostics endpoint

`GET /api/v1/rankings/{run_id}/listings/{listing_id}`

Response body:

- `listing_core`,
- `score_summary`,
- `diagnostics`:
  - signal breakdown (raw, normalized, weighted),
  - comparable cohort + f/phallback level,
  - ROI assumptions and components,
  - confidence/risk flags,
  - scoring metadata (`model_version`, `profile_id`).

### 4.3 Strategy profiles endpoint

- `GET /api/v1/scoring/profiles`
  - list available presets with labels and intent.
- `GET /api/v1/scoring/profiles/{preset}`
  - resolved default config, safe override bounds, signal map.

Week 3 write operations for profile CRUD and alias remapping are out of scope.

### 4.4 API error contract

All Week 3 API errors use consistent shape:

- `code` (stable machine code),
- `message` (human-readable),
- `field_errors[]` (optional for validation issues),
- `request_id`.

## 5) CLI Specification

CLI must stay functionally equivalent to API behavior and align with dashboard-visible behavior.

### 5.1 Run ranking query

Add command:

- `backend/app/cli.py` -> `rank-query`

Arguments:

- `--dataset-source` (repeatable),
- location and price filters,
- property filters,
- `--confidence-min`,
- `--strategy-preset`,
- `--weight-override key=value` (repeatable),
- `--top-n` or pagination flags,
- `--output-json` optional path.

Behavior:

- validates inputs with same service rules as API,
- executes ranking pipeline,
- prints concise summary to terminal,
- optionally writes full response JSON artifact.

### 5.2 Show listing detail

Add command:

- `listing-detail --run-id <id> --listing-id <id>`

Behavior:

- fetches same detail payload structure as API endpoint,
- supports compact and pretty JSON output.

### 5.3 Inspect profiles

Add commands:

- `profiles-list`
- `profile-show --preset <preset>`

Behavior:

- outputs available presets and resolved profile details.

## 6) Service-Layer Architecture

Create or extend services to keep controllers minimal:

- `ranking_query_service`:
  - validate request,
  - resolve profile,
  - fetch candidate listings via filter pipeline,
  - score/rank candidate set,
  - persist run metadata + references,
  - return transport-ready payload.
- `profile_resolution_service`:
  - map preset -> profile config from `backend/config/scoring_profiles.yaml`,
  - apply safe override validation and normalization.
- `listing_detail_service`:
  - retrieve detail payload by run/listing context.

Design constraints:

- deterministic ordering for tied scores (`listing_id` secondary sort),
- no duplicated validation logic across API and CLI,
- keep Week 2 scoring and evaluation helpers reusable.

## 7) Persistence Changes

Week 3 requires durable tracking for ranking invocations.

Add persistence model for ranking runs (name can follow existing model style), including:

- `run_id`,
- timestamp,
- selected dataset sources,
- filter payload snapshot,
- strategy preset and resolved profile snapshot,
- model metadata and resolved profile identifier (`profile_id` / `profile_row_id`),
- result window parameters,
- result count.

Optional companion table for run listing references:

- `run_id`,
- `listing_id`,
- `rank_position`,
- `score`,
- `detail_ref` or serialized detail pointer.

Storage requirements:

- enable lookup by `run_id`,
- efficient listing-detail retrieval by `(run_id, listing_id)`,
- index common filter fields used in ranking query path.

## 8) Performance Requirements (Week 3)

### 8.1 Ranking/query constraints

- ranking list endpoint p95 <= 800ms on baseline workload.
- filtered ranking endpoint p95 <= 1200ms.
- listing detail endpoint p95 <= 500ms.

### 8.2 Baseline handoff completion

Update `backend/app/services/performance_baseline.py` and tests so API SLOs are evaluated, not deferred:

- add API benchmark steps to collect latency distributions,
- write p50/p95 metrics to `baseline_metrics.json`,
- move API keys from `deferred` into `met`/`missed`,
- include dataset-size context (`records_total`, `records_valid`) and throughput rows/sec.

## 9) Observability and Artifacts

For each ranking run, produce an artifact under `backend/output/` containing:

- request snapshot,
- resolved profile snapshot,
- top results summary,
- timings (`filter_ms`, `score_ms`, `serialize_ms`),
- run metadata and profile identifiers.

Logging requirements:

- include `run_id` and `request_id` in structured logs,
- log validation failures as warning-level events with code and field context,
- avoid logging sensitive payload values beyond required diagnostics.

## 10) Dashboard Implementation Requirements

Week 3 dashboard implementation should stay strategy-tool focused and avoid unrelated UI expansion.

Required views/components:

- dataset/source selection and upload area,
- filter + strategy control panel,
- ranked results view,
- listing detail diagnostics panel,
- run status/freshness strip.

State and integration contract:

- dashboard owns only UI state and request composition,
- API responses are the source of truth for ranking outputs and detail payloads,
- all dashboard actions should map to explicit API calls (no hidden local scoring path),
- query state should be serializable (future URL/state restore support).
- dashboard may select strategy preset and submit request-scoped overrides only.
- dashboard must not expose profile CRUD or alias remapping actions.

Acceptance criteria for dashboard slice:

- user can execute a full path: select sources -> set filters -> pick strategy -> run ranking -> open detail,
- user can change strategy preset and observe ranking refresh,
- user can inspect validation/status context before ranking,
- detail panel displays signal-level diagnostics from backend payload without missing critical fields.

## 11) Testing Strategy

### 10.1 Unit tests

- profile resolution and override clamp behavior,
- filter validation edge cases,
- deterministic rank ordering and pagination correctness,
- detail payload completeness and field typing.

### 10.2 Integration tests

- API rank query happy path with one and multiple sources,
- API detail retrieval for ranked listing,
- CLI commands mirror API output shape for equivalent inputs,
- dashboard interactions exercise ranking + detail API path (smoke-level UI test).

### 10.3 Performance tests

- baseline benchmark validates SLO assessment classification for API metrics,
- ensures API metrics no longer remain in `deferred`.

### 10.4 Regression tests

- preserve Week 2 scoring evaluation behavior and contracts,
- ensure strategy-layer additions do not break existing ingestion/scoring flows.

## 12) Security and Validation Requirements

- strict schema validation at API boundary,
- whitelist strategy preset values,
- reject unknown override signal names with explicit error,
- enforce numeric bounds on all user-provided thresholds/ranges,
- sanitize and bound pagination inputs,
- avoid direct SQL string interpolation in filter pipeline construction.

## 13) Rollout Plan

### Phase A: Contract + skeleton

- define request/response schemas,
- add API/CLI stubs wired to service interfaces,
- add profile resolution foundation.

#### Phase A implementation steps (execution order)

1. Freeze request/response contracts first.
   - Create backend schema models for:
     - ranking query request (`dataset_sources`, `filters`, `strategy`, `result_window`),
     - ranking query response (metadata + `results[]` + pagination/top-n envelope),
     - listing detail response,
     - profile list/profile detail responses,
     - shared error envelope (`code`, `message`, `field_errors`, `request_id`).
   - Add strict validation rules for numeric bounds and enum constraints.
   - Add schema unit tests for valid and invalid payloads.

2. Create service interfaces with placeholder implementations.
   - Add service entrypoints:
     - `run_ranking_query(...)`,
     - `get_listing_detail(...)`,
     - `list_profiles(...)`,
     - `resolve_profile(...)`.
   - Return deterministic placeholder payloads that match contract shape (no ranking logic yet).
  - Ensure placeholder responses include `run_id` and resolved profile identifier fields.

3. Add API route skeletons and wire them to services.
   - Add route handlers for:
     - `POST /api/v1/rankings/query`,
     - `GET /api/v1/rankings/{run_id}/listings/{listing_id}`,
     - `GET /api/v1/scoring/profiles`,
     - `GET /api/v1/scoring/profiles/{preset}`.
   - Keep handlers thin (parse -> call service -> map to response).
   - Add consistent error mapping for validation and not-found paths.

4. Add CLI command skeletons mapped to the same service layer.
   - Add commands:
     - `rank-query`,
     - `listing-detail`,
     - `profiles-list`,
     - `profile-show`.
   - Parse CLI args into the same request models used by API.
   - Output contract-aligned JSON with a compact terminal summary.

5. Implement profile resolution foundation.
   - Add canonical preset registry (`rental_income`, `resale_arbitrage`, `refurbishment_value_add`, `balanced_long_term`).
  - Store preset alias mapping in `backend/config/scoring_profiles.yaml`.
   - Add resolver that returns:
     - default weights,
     - enabled signals,
    - `profile_id`.
   - Add override validator:
     - reject unknown signal keys,
     - enforce safe bounds,
     - normalize final weights.
   - Add resolver tests for pass/fail/edge cases.

6. Deliver Phase A verification gate.
   - Backend: all new schema, service, and route tests pass.
   - CLI: command smoke tests pass and output expected JSON shape.
   - Quality checks pass:
     - `./scripts/lint.sh`
     - `./scripts/test.sh`
     - `npm --prefix frontend run build` (only if files outside strict Phase A scope changed).

#### Phase A done criteria (must be true before Phase B)

- All Week 3 endpoint and command contracts are stable and documented.
- API and CLI call the same service contracts (no duplicated business rules).
- Profile discovery and resolution work end-to-end with validated overrides.
- Placeholder API/CLI flows run successfully, enabling Phase B logic implementation without contract churn.

---

### Phase B: Query + ranking implementation

Replace placeholder ranking and detail responses with a real **filter → score → rank → persist**
pipeline while keeping §4–5 request/response contracts stable (extend fields only when the spec
already allows optional metadata; avoid renaming shipped keys).

---

#### Phase B implementation steps (execution order)

1. Close §15 open decisions needed for implementation (record the outcomes in this doc or
   `docs/week-3-profile-preset-management-spec.md`).
   - Persisted listing references vs reconstruct-on-demand for `detail_ref` and detail retrieval.
   - Confirm synchronous ranking for Week 3 vs queue-backed execution (if deferred, document the
     cap and failure mode).
   - Confirm override clamp policy matches resolver behavior (proportional caps already in
     `resolve_profile`; align docs if you change semantics).

2. Resolve `dataset_sources` to a merged candidate input set.
   - Map each source string to ingestion/scoring inputs (existing Week 2 tables or equivalent).
   - Union/dedupe listings across sources into one cohort with deterministic ordering before
     filtering (document tie-break, e.g. `listing_id`).
   - Populate `dataset_context.selected_sources`, real `records_considered` (pre-window count),
     and freshness fields (`last_ingested_at`, `last_scored_at`, `model_version`, profile/version
     identifiers) per §3.1 and §4.1.

3. Implement the filter pipeline on the merged cohort.
   - Apply §3.2 filters: `province`, `city`, `suburb`, `price_min` / `price_max`, `property_type`,
     `bedrooms_min`, `bathrooms_min`, `confidence_min`.
   - Enforce the same bounds as schema validation (non-negative numerics, `price_min <= price_max`,
     `page >= 1`, `1 <= page_size <= 100`, `top_n` cap, mutual exclusivity rules for `top_n` vs
     pagination).
   - Build queries with bound parameters only (no string-concatenated SQL for user input).
   - Add unit tests for filter edge cases (empty result set, boundary values, incompatible
     window combinations).

4. Execute scoring and ranking using resolved strategy weights.
   - Call existing Week 2 / scoring evaluation paths with the **normalized** weights from
     `resolve_profile` (no second scoring implementation in API handlers or frontend).
   - Produce per-listing outputs required by §4.1 `results[]` (`listing_id`, `score`, `deal_reason`,
     `confidence`, summary map, `detail_ref`).
   - Sort by score descending with **deterministic** secondary sort on `listing_id`.
   - Apply `result_window`: either first `top_n` after full filtered ranking, or slice by
     `page` / `page_size` against the filtered ranked list (per §3.2).

5. Persist run metadata and per-run listing references.
   - Extend or use `RankingRun` (and related tables) so each run stores enough to reproduce the
     ranked set and to resolve listing detail: at minimum `run_id`, `query_fingerprint`, strategy
     snapshot, resolved profile linkage (`profile_row_id` / fingerprint per profile preset doc
     §7–9), `request_payload`, window, `result_count`, and stable references for each returned
     row (or a reproducible reconstruction key).
   - Ensure `detail_ref` returned in `results[]` matches what `get_listing_detail` will resolve.

6. Replace placeholder service bodies in `run_ranking_query` and `get_listing_detail`.
   - `run_ranking_query`: return real `results[]`, pagination/`top_n` envelopes aligned with actual
     totals, and accurate `dataset_context`.
   - `get_listing_detail`: load run by `run_id`, validate `listing_id` was part of that run’s
     result set (404 when run missing **or** listing not in run); return §4.2 payload with signal
     breakdown, cohort/comps context, ROI components, risk flags, and scoring metadata including
     `profile_id` where specified.
   - Align CLI `listing-detail` with API behavior (same 404 rules via shared service or shared
     guard).

7. Error mapping and operational clarity.
   - Add stable `code` values for new failure modes (e.g. unknown dataset source, empty cohort post-
     filter, scoring failure) using the §4.4 envelope.
   - Log structured context (`run_id`, `query_fingerprint`, source list) without leaking secrets.

8. Tests for Phase B scope.
   - Unit: deterministic ordering, pagination vs `top_n`, filter combinations, profile-weight
     application to score inputs (mocked where appropriate).
   - Integration: API rank query with one and multiple sources; detail retrieval for a listing
     returned in a rank response; CLI output shape parity for equivalent inputs (§11.2).
   - Regression: Week 2 scoring contracts unchanged for non-ranking entrypoints (§11.4).

9. Deliver Phase B verification gate.
   - `./scripts/lint.sh` and `./scripts/test.sh` pass.
   - `npm --prefix frontend run build` if any shared types or frontend contracts are touched.
   - Update §13.1 checkboxes for “Ranking pipeline” and “Run persistence and detail reproducibility”
     rows as items land; refresh companion profile doc if signal names or persistence fields shift.

#### Phase B done criteria (must be true before Phase C)

- Rank query returns **real** ranked rows derived from selected sources and filters, not
  placeholders; `dataset_context` reflects actual inputs and counts.
- Sorting and windowing behave per §3.2 with deterministic tie-break.
- Each persisted run can answer listing detail for any `listing_id` in that run’s returned page
  window, with API and CLI returning consistent 404 semantics.
- No duplicate scoring or profile logic in the dashboard or route handlers; strategy remains
  centralized in backend services.
- Phase B tests above are in place and green; known limitations (sync caps, max `top_n`) are
  documented if not fully mitigated.

#### Phase B verification notes (duplicate-logic guard + limitations)

**Centralized strategy (§567–568)** — Verified in repo:

- Week 3 HTTP handlers in `backend/app/api/routes_ranking.py` only parse requests, call
  `app.services.ranking_query` (and `resolve_profile` for GET preset), and map errors; they do not
  implement signal math, weights, or profile YAML resolution.
- Ranking math uses `app.services.ranking_signals` (advanced_v2 signal path aligned with
  `app.services.scoring`) plus `resolve_profile` weights; the CLI uses the same service entrypoints
  as the API (`run_ranking_query`, `get_listing_detail`, `list_profiles`, `resolve_profile`).
- The current dashboard (`frontend/src/app/page.tsx`) is scaffold-only (health check); it performs
  **no** ranking, preset resolution, or weight validation. Phase C UI must keep strategy and
  scoring **server-side** and call these APIs only (per §3 dashboard constraints).

**Tests and quality gate (§569–570)** — Required scripts are green in CI/local: `./scripts/lint.sh`,
`./scripts/test.sh` (includes `test_ranking_*` for filters, merge, rank/detail, CLI parity). Run
`npm --prefix frontend run build` when frontend files change.

**Known limitations (sync / caps)** — Not fully mitigated in Phase B; callers should assume:

- **Synchronous ranking:** each `POST .../rankings/query` loads the merged cohort, filters, scores
  every filtered row, sorts, slices, and persists in the **same request**; there is no job queue or
  worker offload. Very large merged sets increase latency and memory use linearly with cohort size
  before windowing.
- **Hard caps (schema §3.2):** `top_n` ≤ 500, `page_size` ≤ 100, `page` ≥ 1; requests outside these
  bounds are rejected at validation (422). These caps bound worst-case response size, not total
  scoring work (the service still scores the full filtered list before applying `top_n` or
  pagination).
- **No rate limiting** on rank query in Phase B (defer to hardening / infra as needed).

### Phase C: Dashboard + detail + profile APIs/CLI

Deliver a functional dashboard slice that executes the full Week 3 user flow against Phase B
backend services, with no frontend-owned scoring/profile business logic.

#### Phase C implementation steps (execution order)

1. Lock UX contract against §3.0 before building components.
   - Confirm required screens/surfaces:
     - dataset source selection (+ multi-select controls),
     - filter + strategy controls,
     - ranked results + detail panel,
     - profile inspection surface,
     - run metadata strip.
   - Confirm no Week 3 profile CRUD/alias remapping in UI.

2. Add dashboard state model and request composer (transport only).
   - Keep UI state serializable (future URL/state restore support).
   - Build one request-composition layer that outputs the exact
     `POST /api/v1/rankings/query` payload shape from §4.1.
   - Reuse API enums/constraints where practical (generated/shared types or
     mirrored frontend types) to reduce drift.

3. Implement dataset source selection and job/status context.
   - Provide source list/multi-select with `select_all` and `clear_all`.
   - Show job status + validation summary panel (ingestion/scoring/validation health context).
   - Map selected sources directly to `dataset_sources[]` request values accepted by backend.

4. Implement filter + strategy controls with request-scoped overrides.
   - Add controls for §3.2 filters (`province`, `city`, `suburb`, budget, property fields,
     `confidence_min`, `top_n` or pagination).
   - Add preset selector using profile discovery APIs:
     - `GET /api/v1/scoring/profiles` for list,
     - `GET /api/v1/scoring/profiles/{preset}` for resolved profile detail and safe bounds.
   - Add advanced override editor:
     - enforce bounds feedback from profile detail response,
     - reset-to-default behavior per current request,
     - never persist overrides as profile updates.

5. Wire ranking submission + result rendering.
   - Submit ranking through `POST /api/v1/rankings/query`.
   - Render ranked results list/table/cards using API response fields only:
     `listing_id`, `score`, `deal_reason`, `confidence`, summary attributes, `detail_ref`.
   - Support both window modes:
     - `top_n` mode,
     - pagination (`page`, `page_size`, `total_count`).
   - Display loading/error/empty states using §4.4 error envelope (`code`, `message`,
     `field_errors`, `request_id`).

6. Implement listing detail panel/drawer from persisted run context.
   - On row click, fetch `GET /api/v1/rankings/{run_id}/listings/{listing_id}`.
   - Render §4.2 diagnostics:
     - signal breakdown,
     - comps/fallback context,
     - ROI assumptions,
     - risk flags,
     - scoring metadata (`model_version`, `profile_id`, etc.).
   - Handle 404 gracefully when run/listing is unavailable.

7. Add visible reproducibility metadata strip in the dashboard.
   - Show `run_id`, model/profile identifiers, and freshness metadata from `dataset_context`.
   - Keep metadata copy/export-friendly for debugging and support workflows.

8. CLI and API behavior alignment pass.
   - Re-verify CLI commands (`rank-query`, `listing-detail`, `profiles-list`, `profile-show`)
     remain contract-equivalent with UI/API behavior for equivalent inputs.
   - Ensure 404 and validation/error semantics stay consistent across HTTP and CLI.

9. Deliver Phase C verification gate.
   - Frontend:
     - `npm --prefix frontend run lint`
     - `npm --prefix frontend run build`
   - Repo quality:
     - `./scripts/lint.sh`
     - `./scripts/test.sh`
   - Add/update smoke tests for ranking + detail + profile API path from dashboard surface.
   - Update §13.1 “Dashboard (Phase C)” checklist rows as each item ships.

#### Phase C done criteria (must be true before Phase D)

- User can complete end-to-end flow in dashboard:
  source selection -> filters -> strategy preset/overrides -> ranking -> detail inspection.
- Dashboard uses backend APIs as source of truth (no client-side scoring/profile logic duplication).
- Profile discovery and bound-aware override UX work via profile APIs without CRUD/remapping.
- Ranking/detail errors are surfaced with actionable feedback using standardized API envelope.
- Run metadata strip is visible and reflects backend response fields for reproducibility.
- Dashboard, API, and CLI behavior are aligned for equivalent ranking/detail/profile operations.
- Required frontend/backend quality gates and smoke tests pass.

### Phase D: Performance and hardening

- integrate API latency into performance baseline artifacts,
- optimize indexes/query plans for hot paths,
- complete required tests and docs updates.

## 13.1) Implementation delta checklist

Living checklist of **outstanding work** versus the current codebase and companion doc
`docs/week-3-profile-preset-management-spec.md`. Update checkboxes as items ship.

### API and error contract

- [x] Mount Week 3 routers on the FastAPI app (`POST /api/v1/rankings/query`,
      `GET /api/v1/rankings/{run_id}/listings/{listing_id}`,
      `GET /api/v1/scoring/profiles`, `GET /api/v1/scoring/profiles/{preset}`).
- [x] Keep handlers thin: parse → shared services → response models (same path as CLI).
- [x] Implement consistent API error envelope (`code`, `message`, `field_errors`, `request_id`)
      for validation and not-found paths.

### Ranking pipeline (Phase B core)

- [x] Resolve `dataset_sources` to ingestion/scoring inputs (merged cohort when multiple sources).
- [x] Implement filter pipeline (province/city/suburb, budget, property fields, `confidence_min`,
      pagination / `top_n` per §3.2).
- [x] Execute real rank/score using resolved strategy weights (no duplicate scoring logic in
      frontend); deterministic tie-break (`listing_id` secondary sort).
- [x] Replace placeholder `results[]`, `records_considered`, and freshness fields with real
      dataset-derived values.

### Run persistence and detail reproducibility

- [x] Persist per-run listing references (or equivalent) so `detail_ref` and detail retrieval match
      the ranked set (resolve open decision in §15: full rows vs reconstruct-on-demand).
- [ ] Return reproducibility fields on rank response as required (e.g. `profile_row_id` /
      resolved profile linkage aligned with `week-3-profile-preset-management-spec.md` §7–9).
      (`profile_row_id` is stored on `ranking_runs` and reused for detail persistence; exposing it
      on the public JSON response is still optional / follow-up.)
- [x] Implement `get_listing_detail` from stored run + listing context (signal breakdown, comps
      path, ROI assumptions, risk flags per §4.2).

### CLI parity

- [x] Confirm CLI uses the same request models and service entrypoints as HTTP API once routes
      exist (already aligned for rank-query path; re-verify after API lands).

### Performance and hardening (Phase D)

- [ ] Move ranking/list/detail API latency from `deferred` to measured in baseline artifacts
      (`backend/app/services/performance_baseline.py` + tests).
- [ ] Add or tune indexes for hot filter/ranking query paths as needed.

### Dashboard (Phase C)

- [ ] Dataset/source selection and multi-select (`select_all` / `clear_all`) wired to real
      sources or upload flow per §3.0.
- [ ] Job status + validation summary panel.
- [ ] Filter + strategy controls (preset, request-scoped overrides with bound feedback, reset).
- [ ] Ranked results surface and listing detail panel/drawer (same request schema as
      `POST /api/v1/rankings/query`; no profile CRUD in UI).
- [ ] Visible run metadata strip (`run_id`, model/profile identifiers, freshness per §3.0).

### Documentation

- [ ] Update `docs/week-3-profile-preset-management-spec.md` config sketch if signal names stay
      aligned with production `scoring_profiles.yaml` (avoid doc/code drift).
- [ ] Refresh `.cursor/rules/PROJECT_NOTE.md` (or equivalent) with API usage and migration notes
      when persistence and routes are complete.

## 14) Definition of Done (Week 3)

Week 3 is complete when all conditions hold:

- ranking APIs are available and documented.
- dashboard supports end-to-end strategy ranking workflow (source selection -> filter -> strategy -> ranked results -> detail panel).
- CLI provides equivalent ranking, profile, and detail workflows.
- strategy presets resolve deterministically with safe override support.
- dashboard supports preset selection and request-scoped override/reset without profile CRUD or alias remapping.
- ranking runs persist metadata and support reliable detail lookup.
- API SLO metrics are measured in baseline artifacts (not deferred).
- required tests pass (`lint`, backend tests, frontend type/build checks as relevant).
- docs updated:
  - this spec,
  - implementation references in project notes,
  - any changed API/CLI usage docs.

## 15) Open Decisions (Must Resolve Early)

- Final endpoint naming and route grouping under existing API layout.
- Whether run listing references are persisted fully or reconstructed on demand.
- Exact override clamp policy (absolute vs proportional caps) per signal.
- Whether ranking query execution should be synchronous now or queue-backed for larger payloads.

Resolve these before Phase B implementation to avoid rework.

### 15.1) Phase B implementation resolutions (shipped)

- **Endpoints:** keep the Phase A `/api/v1/rankings/...` and `/api/v1/scoring/profiles/...` layout.
- **Run listing references:** persist `ranking_run_listings` rows for each listing in the **returned**
  result window, storing an `explanation_snapshot` JSON for diagnostics; `listing_core` fields are
  re-read from `listings` at detail time (404 if the listing row was deleted).
- **Override clamp:** unchanged — proportional ±20% per signal in `resolve_profile`, then normalize.
- **Execution model:** synchronous in-process ranking for Week 3; queue-backed execution stays out
  of scope until explicitly revisited.
- **`dataset_sources` resolution:** each entry is either a numeric ingestion job id (`"42"` or
  `job:42`), or an exact match on `ingestion_jobs.input_path` (first row by id). Sources are merged
  with deterministic dedupe by `listings.source_hash` (first `(job_id, listing.id)` wins).
