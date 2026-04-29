# Week 3 Profile Preset Management Specification

## 1) Purpose

Define how strategy profiles are represented, resolved, evaluated, promoted, and referenced across backend, CLI, dashboard, and persistence for Week 3.

This spec intentionally uses **profile identifiers only** (no profile versioning) to keep implementation simple and operationally clear.

## 2) Scope

### In scope (Week 3)

- Config-backed profile definitions.
- Preset alias mapping to profile identifiers.
- Server-side profile resolution shared by API and CLI.
- Dashboard and CLI behavior for preset selection and overrides.
- Run-time profile reference persistence.
- Manual evaluation and manual promotion workflow.

### Out of scope (defer)

- Automated profile promotion.
- Profile lifecycle/permissions model.
- Multi-tenant profile ownership boundaries.

## 3) Canonical Configuration Model

Profiles are source-controlled and stored in a dedicated config file:

- `backend/config/scoring_profiles.yaml`

The dedicated file must contain:

- `profiles`: profile definitions keyed by `profile_id`
- `preset_alias_mapping`: maps preset name to `profile_id`
- optional profile metadata (label, intent, enabled flags)

`preset_alias_mapping` is configured in the same dedicated scoring profiles config file, not spread across unrelated config files.

## 4) Profile Identity Rules

Week 3 uses `profile_id` only.

- A preset resolves to exactly one `profile_id`.
- No `profile_version` field is required in API contracts for Week 3.
- Rollback/fallback is performed by remapping preset alias to another `profile_id`.

This favors fast operator-driven iteration with minimal contract complexity.

## 5) Resolution and Override Rules

Profile resolution is backend-owned in a single resolver service.

- Input: `preset` + optional `weight_overrides`
- Resolver steps:
  - map preset -> `profile_id` via `preset_alias_mapping`
  - load profile definition from config
  - validate override keys against known signals
  - clamp override deltas to safe bounds (existing Week 3 policy)
  - normalize resulting weights to `1.0`
- Output includes:
  - `profile_id`
  - resolved weights
  - enabled signals

No scoring logic is duplicated in dashboard or CLI.

## 6) API, CLI, Dashboard Contract

### API

- Ranking query accepts `strategy.preset` and optional `strategy.weight_overrides`.
- Ranking response includes resolved `profile_id` and resolved profile payload details.

### CLI

- Primary profile selection is `--strategy-preset`.
- Optional `--weight-override key=value` for request-scoped tuning.
- Output includes resolved `profile_id`.

### Dashboard

- Main strategy panel includes preset selector.
- Advanced panel supports request-scoped override controls.
- Reset restores active preset defaults for current request.
- Dashboard displays resolved `profile_id` returned by backend.

## 7) Persistence and Backup Strategy

Historical runs must remain reproducible even if config evolves.

Each ranking run stores a database reference field `profile_row_id`.

Recommended Week 3 behavior:

1. On each run, resolve profile from config.
2. Check if an equivalent profile record already exists in DB.
3. If it does not exist, insert profile backup record.
4. Persist `profile_row_id` on run record.

This gives historical stability with deduplicated profile backup rows.

## 8) Evaluation and Promotion Workflow

Promotion is manual and operator-driven (not automatic).

Evaluation loop:

1. Run profile evaluation using fixed datasets and baseline metrics.
2. Compare candidate profile against baseline thresholds.
3. Operator/developer reviews evaluation output.
4. If accepted, operator updates config (`profiles` and/or `preset_alias_mapping`).
5. Re-run checks and commit config change.

The system may provide evaluation artifacts, but does not auto-promote profiles.

## 9) Recommended Data Shapes

### Config sketch

```yaml
profiles:
  rental_income_default:
    label: "Rental Income Default"
    intent: "Yield-first screening"
    enabled_signals:
      - rental_yield
      - vacancy_risk
      - maintenance_burden
    weights:
      rental_yield: 0.45
      vacancy_risk: 0.25
      maintenance_burden: 0.30

preset_alias_mapping:
  rental_income: rental_income_default
  resale_arbitrage: resale_arbitrage_default
  refurbishment_value_add: refurbishment_value_add_default
  balanced_long_term: balanced_long_term_default
```

### Run metadata sketch

```json
{
  "run_id": "uuid",
  "strategy_preset": "rental_income",
  "resolved_profile_id": "rental_income_default",
  "profile_row_id": 42
}
```

## 10) Acceptance Criteria

- Preset resolution is deterministic and backend-owned.
- `preset_alias_mapping` is centralized in dedicated scoring profiles config.
- API/CLI/dashboard show resolved `profile_id` for each run.
- Historical runs reference profile backup record (`profile_row_id`) and remain traceable.
- Promotion requires explicit manual config update after evaluation review.
- No `profile_version` field is required for Week 3 profile management.