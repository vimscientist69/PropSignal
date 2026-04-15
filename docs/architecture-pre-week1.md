# Pre-Week-1 Architecture

## Objective

Establish a CLI-first ingestion and scoring foundation with robust persistence and repeatable local
environment parity through Docker Compose.

## Runtime Components

- `frontend` (placeholder): minimal status UI exposed on `localhost:3000`
- `backend` (FastAPI + CLI): API and command execution surface on `localhost:8000`
- `postgres`: primary store for ingestion jobs, listings, and score outputs

## Data Flow

1. CLI `ingest <path>` reads a JSON file.
2. Every record is persisted first to `raw_listings`.
3. PropFlux schema validation runs per record.
4. Valid records are normalized and upserted into canonical `listings`.
5. Invalid records are stored in `rejected_listings` with deterministic error metadata.
6. Job lifecycle and counters are tracked in `ingestion_jobs`.
7. `score`, `analyze`, and `export` commands update job state and emit outputs.

## Persistence Model

- `ingestion_jobs`: orchestration state, started/finished timestamps, and total/valid/invalid counters
- `raw_listings`: immutable source payload landing table, indexed by `job_id` and record index
- `listings`: canonical normalized listing records with dedup constraints
- `rejected_listings`: invalid record payloads with error codes and detailed validation traces
- `score_results`: score/confidence/deal reasoning per listing

## Dedup and Idempotency

- Canonical listing upserts use `(source_site, listing_id)` when present.
- If `listing_id` is missing, ingestion falls back to normalized `source_hash`.
- Re-ingestion updates existing canonical rows instead of inserting duplicates.

## Week 1 Boundary

- In scope: ingestion validation, normalization, persistence, and CLI workflow reliability.
- Out of scope: full interactive dashboard feature development (scheduled for Week 3).
