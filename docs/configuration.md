# Configuration Guide

This document covers **environment variables**, **config files**, **Docker defaults**, and a **glossary** of terms used across CLI, API, and dashboard. Each glossary entry follows **what** (definition), **why** (purpose), and **how** (where you set or observe it).

For dashboard workflows, see [`dashboard.md`](dashboard.md).  
For CLI commands, see [`cli-usage.md`](cli-usage.md).

---

## Environment files

| File | Purpose |
|------|---------|
| `.env` | Shared values for root-level scripts (`PS_*`) |
| `backend/.env` | API service: database, CORS, API prefix |
| `frontend/.env.local` | Browser-visible API base URL |

Create local copies from the `*.example` templates. **Do not commit** real `.env` files or secrets.

---

## Environment variables

### Root (`.env`)

| Variable | What | Why | How |
|----------|------|-----|-----|
| `PS_ENVIRONMENT` | Label for local script context (`development`, etc.) | Distinguishes dev vs other script behavior | Set in `.env`; consumed by helper scripts |
| `PS_LOG_LEVEL` | Log verbosity for scripts | Controls noise during local automation | Set in `.env` (e.g. `INFO`) |

### Backend (`backend/.env`)

| Variable | What | Why | How |
|----------|------|-----|-----|
| `APP_NAME` | Human-readable API title | Shown in OpenAPI docs | Default `PropSignal API` |
| `ENVIRONMENT` | Runtime environment label | Logging and behavior guards | `development` locally |
| `API_PREFIX` | URL prefix for all routes | Versioned API surface | Default `/api/v1` → routes like `/api/v1/health` |
| `FRONTEND_URL` | Allowed browser origin for CORS | Dashboard can call API from another port | Match frontend URL, e.g. `http://localhost:3000` |
| `DATABASE_URL` | SQLAlchemy connection string | Runtime DB access | Postgres URL; compose default uses user/db `propsignal` |
| `ALEMBIC_DATABASE_URL` | Migration connection string | Alembic may need same or elevated URL | Usually identical to `DATABASE_URL` locally |

### Frontend (`frontend/.env.local`)

| Variable | What | Why | How |
|----------|------|-----|-----|
| `NEXT_PUBLIC_API_BASE_URL` | Backend origin for `fetch` | Browser builds full API URLs | `http://localhost:8000` locally; must be reachable from the browser and allowed by CORS |

---

## Config files (repository)

### `config/scoring.yaml`

| Section | What | Why | How |
|---------|------|-----|-----|
| `weights` | Baseline v1 signal weights | Legacy/simple scoring path | Edit weights; keep sum ≈ 1.0 |
| `rules` | Thresholds (stale days, min confidence, outlier z-score) | Gates low-quality scores | Tune per market |
| `flags` | Feature toggles (liquidity, advanced v2, explanations) | Enable/disable signal families without code changes | Boolean flags |
| `advanced_v2` | Week 2 engine: weights, comps cohort rules, ROI heuristics | Primary scoring model for ranking (`model_version: advanced_v2`) | Adjust weights and `comps` / `roi` blocks; re-run evaluation before promote |
| `evaluation_thresholds` | Dataset quality, sanity, stability, promote gates | Automated promote/revert decisions | Used by evaluation CLI and tests |

### `backend/config/scoring_profiles.yaml`

| Section | What | Why | How |
|---------|------|-----|-----|
| `profiles` | Named strategy definitions (`profile_id`, weights, enabled signals) | Backend resolves presets to concrete scoring mixes | Add/edit profiles; map presets below |
| `preset_alias_mapping` | Maps dashboard/CLI preset enum → `profile_id` | Operators pick friendly preset names | Change mapping to switch default strategy without renaming API fields |

Strategy presets exposed to API/dashboard: `rental_income`, `resale_arbitrage`, `refurbishment_value_add`, `balanced_long_term`.

---

## Docker Compose defaults

| Service | Host port | Notes |
|---------|-----------|-------|
| Postgres 16 | `5432` | user/password/database: `propsignal` |
| Backend API | `8000` | Health: `/api/v1/health` |
| Frontend | `3000` | Dashboard at `/dashboard/control` |

Apply migrations after first start: `./scripts/migrate-docker.sh`.  
Ranking runs require migration `20260511_0009` (`ranking_runs.records_considered`) in Postgres-backed environments.

---

## API routes (dashboard-relevant)

| Route | What | How |
|-------|------|-----|
| `GET /api/v1/datasets/sources` | List ingestion jobs as ranking sources | Optional `status`, `q` query params |
| `GET /api/v1/scoring/profiles` | List strategy presets | Dashboard strategy dropdown |
| `GET /api/v1/scoring/profiles/{preset}` | Resolved profile + override bounds | Control Panel override editor |
| `POST /api/v1/rankings/query` | Execute ranking run | Body: sources, filters, strategy, result_window |
| `GET /api/v1/rankings/{run_id}/listings/{listing_id}` | Listing detail for a run | Diagnostics trees in UI |
| `GET /api/v1/runs` | Paged run summaries | `page`, `page_size` |
| `GET /api/v1/runs/{run_id}` | Full run detail + persisted results | Run detail page |
| `GET /api/v1/runs/{run_id}/export` | CSV or JSON export | `format`, optional `listing_detail=true` |
| `GET /api/v1/diagnostics/summary` | Operator health snapshot | Diagnostics tab |

---

## Glossary

### Data ingestion

#### PropFlux JSON contract

- **What** — A JSON **array** of listing objects with required fields (`listing_id`, `price`, etc.) documented in [`data-contract-propflux.md`](data-contract-propflux.md).
- **Why** — Single ingestion shape keeps validation, dedup, and scoring predictable.
- **How** — `ingest <path>` via CLI; only array roots accepted; invalid rows go to `rejected_listings`.

#### Ingestion job (`ingestion_jobs`)

- **What** — One ingest execution: input path, status, record counts, timestamps.
- **Why** — Tracks lifecycle and links listings/scores to a dataset batch.
- **How** — Created on `ingest`; statuses below; referenced in dashboard as `job:{id}`.

#### Ingestion job status

| Status | What | Why |
|--------|------|-----|
| `created` | Job row exists, work not started | Initial state |
| `processing` | Ingest/score pipeline running | Operator visibility |
| `completed` | All records valid | Clean ingest |
| `completed_with_errors` | Partial accept; some rejects | Common real-world outcome |
| `analyzed` | Downstream analytics stage completed | Pipeline progression |
| `failed` | Fatal payload or processing failure | Needs operator action |

**How** — Filter Source Library by status; diagnostics shows counts by status.

#### Dataset source / source token

- **What** — Ranking input identifier, format `job:{ingestion_job_id}`.
- **Why** — Ranking query selects which ingested datasets to merge and score.
- **How** — Pass in `dataset_sources` array on rank request; multi-select in Control Panel.

#### Validation status (`pass` / `warn` / `fail`)

- **What** — Dataset-level quality outcome from `validate-dataset`.
- **Why** — Warns before trusting a job for scoring/ranking.
- **How** — Shown in Source Library detail; summaries in Diagnostics.

---

### Listings and deduplication

#### Canonical listing (`listings`)

- **What** — Normalized listing row deduplicated across ingests.
- **Why** — Stable `listing_id` for scores and ranking results.
- **How** — Dedup key: `source_site + listing_id`, else `source_hash` from normalized payload; re-ingest updates existing row.

#### Raw / rejected listings

- **What** — `raw_listings` stores immutable ingest snapshots; `rejected_listings` stores invalid rows + reasons.
- **Why** — Audit trail and debugging bad vendor data.
- **How** — Populated automatically during ingest; inspect via DB or export tooling.

---

### Scoring

#### Model version (`model_version`)

- **What** — Identifier for the scoring engine generation (e.g. `advanced_v2`, baseline `baseline_v1`).
- **Why** — Explains which algorithm produced stored scores and ranking explanations.
- **How** — Set in scoring service; appears in listing `score_summary` and run `dataset_context`.

#### Scoring signal

- **What** — A measurable input to the score (e.g. `price_vs_comp`, `roi_proxy`, `confidence`, `time_on_market`).
- **Why** — Decomposes “deal quality” into tunable components.
- **How** — Enabled per profile in `scoring_profiles.yaml`; weights in profile or `scoring.yaml` (`advanced_v2.weights`).

#### Score result (`score_results`)

- **What** — Persisted score, confidence, deal_reason, and explanation JSON for a listing within a job.
- **Why** — Batch scoring decouples ingest from interactive ranking.
- **How** — Created by `score <job-id>` CLI or equivalent service path.

---

### Strategy and profiles

#### Strategy preset

- **What** — API enum selecting an investment intent (`rental_income`, `resale_arbitrage`, …).
- **Why** — Operators choose intent without editing YAML.
- **How** — Dashboard strategy dropdown; maps to `profile_id` via `preset_alias_mapping`.

#### Profile (`profile_id`)

- **What** — Concrete weight/signal configuration (e.g. `rental_income_default`).
- **Why** — Reproducible strategy; persisted on each ranking run.
- **How** — Defined under `profiles` in `scoring_profiles.yaml`; returned in ranking response as `resolved_profile.profile_id`.

#### Profile version (`profile_version`)

- **What** — Version label for a profile definition (currently placeholder `v1` in API responses).
- **Why** — Future-proofing for config revisions and audit trails.
- **How** — Returned on profile detail and runs; durable reproducibility today uses `profile_row_id` + backup payload.

#### Weight override

- **What** — Per-request adjustment to a signal weight within safe bounds.
- **Why** — Tune a preset for a single run without editing YAML.
- **How** — `strategy.weight_overrides` in rank request; Control Panel override inputs.

#### Enabled signals

- **What** — List of signals active for a profile.
- **Why** — Profiles can omit signals irrelevant to the strategy.
- **How** — `enabled_signals` in profile YAML; shown in resolved profile on rank response.

---

### Ranking runs

#### Ranking run (`ranking_runs`)

- **What** — Persisted execution: request payload, result window, link to profile backup, listing ordinals/scores.
- **Why** — Reopen, export, and compare past decisions.
- **How** — Created by `POST /api/v1/rankings/query`; listed in Runs tab.

#### Run ID (`run_id`)

- **What** — Opaque string uniquely identifying one ranking run.
- **Why** — Stable key for detail, export, and listing detail routes.
- **How** — Shown in Control Panel after rank; copy from UI or Runs table.

#### Query fingerprint (`query_fingerprint`)

- **What** — Hash of normalized rank request inputs.
- **Why** — Detect duplicate requests; support caching/analysis.
- **How** — Returned on rank response; shown on run detail snapshot.

#### Profile row ID (`profile_row_id`)

- **What** — Foreign key to `scoring_profile_backups` storing the exact resolved profile JSON used for the run.
- **Why** — Strong reproducibility even if YAML changes later.
- **How** — On run detail and compare metadata diffs.

#### Records considered

- **What** — Count of listings matching filters **before** result window slicing.
- **Why** — Distinguishes “searched universe” from “returned rows”.
- **How** — `dataset_context.records_considered` on rank response; Runs table column.

#### Result window

- **What** — How many rows to return: `top_n` **or** `page` + `page_size` (mutually exclusive).
- **Why** — Controls payload size and UI focus (top deals vs paged browse).
- **How** — Control Panel radio + inputs; stored in `result_window` on run.

#### Result count

- **What** — Number of listings persisted in the run’s results set.
- **Why** — May be less than `top_n` if fewer listings match filters.
- **How** — Runs table; compare diff operates on this persisted set.

#### Detail ref (`detail_ref`)

- **What** — Stable string `{run_id}:listing-{listing_id}` for detail retrieval.
- **Why** — Links table rows to diagnostics endpoint.
- **How** — Present on each `results[]` item; used internally by dashboard detail loader.

---

### Listing detail and explainability

#### Listing core

- **What** — Normalized listing fields for display (price, location, beds, url, etc.).
- **Why** — Investor context alongside the score.
- **How** — `listing_core` in listing detail response; JSON tree in UI.

#### Score summary

- **What** — Score, confidence, deal_reason, model/profile identifiers for one listing in a run.
- **Why** — Quick read of outcome without full signal tree.
- **How** — `score_summary` block in listing detail.

#### Diagnostics

- **What** — Signal breakdown (raw, normalized, weighted), comps context, ROI assumptions, risk flags.
- **Why** — Explain *why* a listing ranked where it did.
- **How** — `diagnostics` in listing detail; see [`reasoning-explainability-payload.md`](reasoning-explainability-payload.md).

#### Deal reason

- **What** — Short human-readable scoring headline for a listing.
- **Why** — Scan table without opening detail.
- **How** — Column in results; compared in run diff when it changes.

---

### Exports

#### Summary export

- **What** — Rank results metadata + table rows without embedded listing detail trees.
- **Why** — Smaller files for spreadsheets and quick sharing.
- **How** — Client export buttons or `GET .../export?format=csv|json`.

#### Full detail export

- **What** — Export rows plus `listing_detail` payload per listing (same as detail endpoint).
- **Why** — Offline analysis with full explainability.
- **How** — `listing_detail=true` on server export; “full detail” buttons in Control Panel and run detail.

---

### Errors (API)

#### Error envelope

- **What** — JSON body: `code`, `message`, `field_errors[]`, `request_id`.
- **Why** — Consistent operator and UI handling of validation failures.
- **How** — Dashboard `fetchJson` surfaces `message` + field reasons in alert banners.

---

## CLI runtime notes

- Entrypoint: `backend/app/cli.py`
- Local: `./scripts/cli-local.sh`
- Docker: `./scripts/cli-docker.sh`
- Ingestion enforces PropFlux array contract with partial-accept processing.

## Database layout (ingestion → ranking)

| Table | Role |
|-------|------|
| `ingestion_jobs` | Ingest lifecycle and counters |
| `raw_listings` | Immutable raw snapshots |
| `listings` | Canonical normalized listings |
| `rejected_listings` | Invalid rows + diagnostics |
| `score_results` | Batch scores per job/listing |
| `scoring_profile_backups` | Frozen profile JSON per fingerprint |
| `ranking_runs` | Run metadata and request snapshot |
| `ranking_run_listings` | Ordinal, score, explanation snapshot per result row |

---

## Related documents

- [`dashboard.md`](dashboard.md) — Tab-by-tab operator guide
- [`data-contract-propflux.md`](data-contract-propflux.md) — Ingestion field definitions
- [`reasoning-explainability-payload.md`](reasoning-explainability-payload.md) — Diagnostics field reference
- [`week-3-profile-preset-management-spec.md`](week-3-profile-preset-management-spec.md) — Profile resolution rules
