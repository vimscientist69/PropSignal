# Current Project Status

This file is the single reference for:
- what is completed,
- what is planned but not built,
- and what to do first on the next feature branch.

## Snapshot

- Current phase: transition from Week 1 completion to Week 2 implementation.
- Branch readiness: documentation and planning are in place for next-phase execution.
- Primary next objective: implement Week 2 advanced scoring and explanation payloads.

## Completion Checklist

## Completed (foundation)

- [x] Project scaffolding, dev scripts, and CI baseline
- [x] Docker Compose + PostgreSQL setup
- [x] PropFlux ingestion with normalization and partial-accept flow
- [x] Raw/normalized/rejected persistence model
- [x] Baseline scoring service (`baseline_v1`) with config-driven weights
- [x] Dataset validation service and CLI command (`validate-dataset`)
- [x] Core unit/integration test coverage for ingestion, scoring, and dataset validation
- [x] Week 2 strategy and architecture documentation package

## Planned, not implemented yet

- [ ] Week 2 advanced scoring (`advanced_v2`) with micro-comps
- [ ] Week 2 ROI proxy (yield + transaction costs)
- [ ] Week 2 structured reasoning payload in scored output
- [ ] Week 2 analytics quality/stability checks
- [ ] Week 2 optional LLM enrichment prototype (gated)
- [ ] Week 3 strategy-driven ranking API/CLI/dashboard functionality
- [ ] Week 4 full validation/tuning/release hardening loop

## Deferred/optional

- [ ] Broad external data integrations beyond one high-impact source
- [ ] Heavy macro/geospatial modeling
- [ ] PDF export (if not required for MVP release)

## Next Feature Branch Kickoff Checklist

Use this immediately when starting the next branch:

1. Confirm scope: Week 2 must-ship only (do not mix Week 3 UI/API overhaul work).
2. Define `advanced_v2` signal contract and output schema.
3. Implement micro-comps computation with safe fallbacks and confidence penalties.
4. Implement ROI proxy signals with deterministic defaults first.
5. Add structured reasoning payload persistence + tests.
6. Add evaluation gates from `docs/evaluation-review-protocol.md`.
7. Run manual sample review and log results.
8. Merge only if promotion thresholds pass.

## Branch Scope Guardrail (Important)

- Keep branch goal narrow: `advanced_v2` scoring + reasoning + evaluation checks.
- Do not include dashboard strategy tooling in the same branch.
- Keep LLM integration behind feature flag and deterministic fallback.

## Related Documents

- Master roadmap: `/.cursor/rules/PROJECT_NOTE.md`
- Week 2 explanation: `docs/week2-advanced-scoring-explained.md`
- Evaluation protocol: `docs/evaluation-review-protocol.md`
- Principal audit: `docs/project-note-principal-audit.md`
- MVP performance plan: `docs/mvp-performance-plan.md`
