
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

### Phase B: Query + ranking implementation

- implement filtered candidate retrieval and rank execution,
- persist run metadata and references,
- return summary payload.

### Phase C: Dashboard + detail + profile APIs/CLI

- implement dashboard workflow UI and wire it to ranking/detail/profile APIs,
- implement detail retrieval and profile inspection surfaces,
- align CLI with API contract and dashboard behavior.

### Phase D: Performance and hardening

- integrate API latency into performance baseline artifacts,
- optimize indexes/query plans for hot paths,
- complete required tests and docs updates.

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
