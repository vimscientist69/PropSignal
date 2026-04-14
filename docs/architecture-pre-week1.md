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
2. PropFlux schema validation enforces required and optional field constraints.
3. Valid records are normalized and stored in `listings` with original payload snapshots.
4. Job metadata is tracked in `ingestion_jobs`.
5. `score`, `analyze`, and `export` commands update job state and emit outputs.

## Persistence Model

- `ingestion_jobs`: orchestration and state transitions
- `listings`: validated PropFlux listing records + metadata
- `score_results`: score/confidence/deal reasoning per listing

## Week 1 Boundary

- In scope: ingestion validation, normalization, persistence, and CLI workflow reliability.
- Out of scope: full interactive dashboard feature development (scheduled for Week 3).
