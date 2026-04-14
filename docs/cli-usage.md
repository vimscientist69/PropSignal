# CLI Usage

PropSignal is CLI-first before Week 3. Commands are implemented in `backend/app/cli.py`.

## Run Commands

- Local:
  - `./scripts/cli-local.sh --help`
- Docker:
  - `./scripts/cli-docker.sh --help`

## Command Reference

- `ingest <path>`
  - Validates PropFlux payload and stores ingestion job + listings in Postgres.
- `score <job-id>`
  - Runs scoring stage placeholder and marks job as scored.
- `analyze <job-id>`
  - Runs analytics stage placeholder and marks job as analyzed.
- `export <job-id> --format json|csv`
  - Writes job export placeholder output in `output/`.

## Example Sequence

1. `./scripts/migrate.sh`
2. `./scripts/cli-local.sh ingest backend/tests/fixtures/propflux/valid_listings.json`
3. `./scripts/cli-local.sh score 1`
4. `./scripts/cli-local.sh analyze 1`
5. `./scripts/cli-local.sh export 1 --format json`
