# CLI Usage

PropSignal is CLI-first before Week 3. Commands are implemented in `backend/app/cli.py`.

## Run Commands

- Local:
  - `./scripts/cli-local.sh --help`
- Docker:
  - `./scripts/cli-docker.sh --help`

## Command Reference

- `ingest <path>`
  - Runs partial-accept ingestion.
  - Persists raw records, normalized canonical listings, and rejected records.
  - Prints job summary: status, total/valid/invalid counts.
- `score <job-id>`
  - Runs scoring stage placeholder and marks job as scored.
- `validate-dataset <job-id>`
  - Computes dataset-level quality checks and threshold gates.
  - Persists validation summary and writes `output/job_<id>_validation.json`.
- `analyze <job-id>`
  - Runs analytics stage placeholder and marks job as analyzed.
- `export <job-id> --format json|csv`
  - Writes job export placeholder output in `output/`.

## Example Sequence

1. `./scripts/migrate.sh`
2. `./scripts/cli-local.sh ingest tests/fixtures/propflux/mixed_valid_invalid.json`
3. `./scripts/cli-local.sh score 1`
4. `./scripts/cli-local.sh validate-dataset 1`
5. `./scripts/cli-local.sh analyze 1`
6. `./scripts/cli-local.sh export 1 --format json`

## Ingestion Outcomes

- `completed`: all records valid and processed.
- `completed_with_errors`: some records rejected but valid records were processed.
- `failed`: payload-level failure (for example, non-array JSON root).
