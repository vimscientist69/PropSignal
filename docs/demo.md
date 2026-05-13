# Local Demo Walkthrough

Use this when walking through PropSignal in an interview or portfolio review. Everything runs locally—no hosted URL required.

**Time:** ~10 minutes after prerequisites are installed.

## Prerequisites

- Completed [`setup-checklist.md`](setup-checklist.md) through migrations
- Postgres running (Docker Compose or local)
- Env files copied from `*.example`

## One-command seed (CLI path)

From repo root:

```bash
chmod +x scripts/demo-local.sh   # first time only
./scripts/demo-local.sh
```

This migrates, ingests the committed test fixture, scores job `1`, validates the dataset, and executes a ranking run via CLI.

For a predictable `job_id=1`, reset first:

```bash
./scripts/reset-db-local.sh --yes
./scripts/demo-local.sh
```

## Start the UI

If not using Docker Compose for backend/frontend:

Terminal 1:

```bash
./scripts/run-backend.sh
```

Terminal 2:

```bash
./scripts/run-frontend.sh
```

Open [Control Panel](http://localhost:3000/dashboard/control) (`/` redirects there).

## Suggested live narrative (~5 min)

1. **Control Panel** — sources include `job:1`; run ranking; show results table, run metadata, and error UX if API is down.
2. **Listing detail** — open one row; walk through `listing_core`, `score_summary`, `diagnostics` trees.
3. **Export** — download window CSV or JSON (summary or full detail).
4. **Runs** — show persisted run; run a second rank with a different preset or `top_n`; click **Compare runs** for metadata and score/rank deltas.
5. **Source Library** — ingestion status filter and validation summary for `job:1`.
6. **Diagnostics** — API health and inventory counts.

## CLI parity (optional, 2 min)

```bash
./scripts/cli-local.sh profiles-list
./scripts/cli-local.sh profile-show --preset rental_income --pretty
./scripts/cli-local.sh rank-query --dataset-source job:1 --strategy-preset balanced_long_term --top-n 3
./scripts/cli-local.sh listing-detail --run-id <run_id_from_output> --listing-id <id> --pretty
```

## Fixture data

Demo ingest uses:

`backend/tests/fixtures/propflux/valid_listings.json`

Additional fixtures for edge-case testing live under `backend/tests/fixtures/propflux/`. They are small so CI stays fast; the dashboard still demonstrates ranking → detail → export → compare.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| Cannot reach API banner | Backend down or wrong `NEXT_PUBLIC_API_BASE_URL` | Start backend; check `frontend/.env.local` |
| No sources in Control Panel | Ingest not run or API error | Re-run `./scripts/demo-local.sh` |
| `job_id` not 1 | Older data in DB | `./scripts/reset-db-local.sh --yes` then demo script |
| Ranking returns empty results | Job not scored | `./scripts/cli-local.sh score 1` |

## What not to claim in a demo

- Scores are heuristic MVP outputs, not calibrated investment advice.
- `profile_version` in API responses is a placeholder; reproducibility uses `profile_row_id` and profile backup payloads.
- No authentication layer—single-operator local tool by design.
