# Current Project Status

This file is the single reference for:
- what is completed,
- what is planned but not built,
- and what to do first on the next feature branch.

## Snapshot

- Current phase: Week 2 implementation completed (including Phase 5 validation cycle).
- Branch readiness: Week 2 outputs are production-candidate and frozen pending Week 3 scope.
- Primary next objective: begin Week 3 strategy-driven API/CLI/dashboard implementation.

## Completion Checklist

## Completed (foundation + Week 2)

- [x] Project scaffolding, dev scripts, and CI baseline
- [x] Docker Compose + PostgreSQL setup
- [x] PropFlux ingestion with normalization and partial-accept flow
- [x] Raw/normalized/rejected persistence model
- [x] Baseline scoring service (`baseline_v1`) with config-driven weights
- [x] Dataset validation service and CLI command (`validate-dataset`)
- [x] Core unit/integration test coverage for ingestion, scoring, and dataset validation
- [x] Week 2 strategy and architecture documentation package
- [x] Week 2 advanced scoring (`advanced_v2`) with micro-comps + ROI proxy
- [x] Week 2 structured reasoning payload in scored output
- [x] Week 2 evaluation gates (`promote`/`revert`/`experimental`) and CLI integration
- [x] Week 2 segment-based stability checks with relative displacement thresholds
- [x] Week 2 Phase 4 performance baseline command and artifacts
- [x] Week 2 Phase 5 validation cycle completed with final promoted profile

## Planned, not implemented yet

- [ ] Week 3 strategy-driven ranking API/CLI/dashboard functionality
- [ ] Week 4 full validation/tuning/release hardening loop
- [ ] Week 2 optional LLM enrichment prototype (gated)

## Deferred/optional

- [ ] Broad external data integrations beyond one high-impact source
- [ ] Heavy macro/geospatial modeling
- [ ] PDF export (if not required for MVP release)

## Next Feature Branch Kickoff Checklist (Week 3)

Use this immediately when starting the next branch:

1. Confirm Week 3 scope: strategy-driven API/CLI/dashboard only.
2. Keep Week 2 scoring profile as baseline:
   - `advanced_v2.weights.price_vs_comp = 0.29`
   - `advanced_v2.weights.roi_proxy = 0.21`
3. Build ranking/list/detail API endpoints and aligned CLI workflow.
4. Implement Week 3 performance handoff items from Phase 4 baseline docs.
5. Preserve Week 2 evaluation contracts while expanding strategy surfaces.
6. Run regression checks against Week 2 decision artifact before merging.

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
- Week 2 final decision (post enum/eval fix): `backend/output/evaluations/phase5_week2_validation_decision_2026-04-27_post_enum_eval_fix.md`
