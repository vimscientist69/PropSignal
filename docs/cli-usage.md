# CLI Usage

Commands live in `backend/app/cli.py` and share services with the HTTP API where noted.

## How to run

| Mode | Command |
|------|---------|
| Local (venv) | `./scripts/cli-local.sh --help` |
| Docker | `./scripts/cli-docker.sh --help` |

Run from **repository root** so paths and env files resolve correctly.

---

## Data pipeline

### `ingest <path>`

- Partial-accept ingestion of a PropFlux JSON **array**.
- Persists `ingestion_jobs`, `raw_listings`, `listings`, and `rejected_listings`.
- Prints `job_id`, status, and valid/invalid counts.

### `score <job-id>`

- Runs `advanced_v2` batch scoring into `score_results` for the job’s listings.

### `validate-dataset <job-id>`

- Dataset-level quality gates; persists validation row and writes `backend/output/job_<id>_validation.json`.

### `analyze <job-id>`

- Analytics stage for the ingestion job (marks job analyzed).

### `export <job-id> --format json|csv`

- Exports scored job results to `output/`.

### `inspect-rejections <job-id>`

- Summarizes rejection reasons for a job (`--top-fields`, `--sample-values`).

---

## Ranking (Week 3+ / API parity)

### `rank-query`

Executes the same ranking path as `POST /api/v1/rankings/query`.

```bash
./scripts/cli-local.sh rank-query \
  --dataset-source job:1 \
  --strategy-preset rental_income \
  --top-n 10
```

Common options: `--province`, `--city`, `--suburb`, `--price-min`, `--price-max`, `--property-type`, `--bedrooms-min`, `--bathrooms-min`, `--confidence-min`, `--page`, `--page-size`, `--weight-override signal=0.25`, `--output-json path.json`.

### `listing-detail`

```bash
./scripts/cli-local.sh listing-detail --run-id <run_id> --listing-id <id> --pretty
```

### `profiles-list` / `profile-show`

```bash
./scripts/cli-local.sh profiles-list
./scripts/cli-local.sh profile-show --preset rental_income --pretty
```

---

## Evaluation and performance

### `evaluate-scoring`

Runs scoring evaluation gates (promote/revert/experimental) per `config/scoring.yaml` thresholds.

### `benchmark-baseline`

Writes performance baseline artifacts under `backend/output/` (includes API latency measurements where configured).

---

## Example: full local sequence

```bash
./scripts/migrate.sh
./scripts/cli-local.sh ingest backend/tests/fixtures/propflux/mixed_valid_invalid.json
./scripts/cli-local.sh score 1
./scripts/cli-local.sh validate-dataset 1
./scripts/cli-local.sh rank-query --dataset-source job:1 --strategy-preset rental_income --top-n 5
```

Or use the bundled demo script: [`demo.md`](demo.md) → `./scripts/demo-local.sh`.

---

## Ingestion job statuses

| Status | Meaning |
|--------|---------|
| `created` | Job created, not started |
| `processing` | Pipeline running |
| `completed` | All records valid |
| `completed_with_errors` | Partial accept |
| `analyzed` | Analytics stage done |
| `failed` | Fatal failure |
