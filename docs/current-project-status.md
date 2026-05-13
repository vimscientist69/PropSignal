# Current Project Status

Single reference for what is **built**, what is **deferred**, and what matters for **portfolio vs production** use.

Last aligned with the codebase: dashboard tabs, ranking API, runs/diagnostics/export, and compare diff are implemented.

---

## Portfolio-ready (built)

- [x] Monorepo scaffolding, scripts, Docker Compose, PostgreSQL, CI
- [x] PropFlux ingestion (partial accept), dedup, raw/normalized/rejected persistence
- [x] Baseline (`baseline_v1`) and advanced (`advanced_v2`) scoring with explainability payloads
- [x] Dataset validation CLI and persisted validation summaries
- [x] Strategy profiles (`scoring_profiles.yaml`) and preset resolution
- [x] Ranking API: query, listing detail, profiles
- [x] Persisted ranking runs, run list/detail, CSV/JSON export (optional full listing detail)
- [x] Diagnostics summary API
- [x] Dataset sources API with status/search filters
- [x] CLI parity: `rank-query`, `listing-detail`, `profiles-list`, `profile-show`, evaluation/benchmark commands
- [x] Dashboard: Control Panel, Source Library, Runs (compare diff), Run detail, Diagnostics
- [x] Operator docs: README, `demo.md`, `dashboard.md`, `configuration.md` glossary
- [x] Backend test suite (~90 pytest cases); frontend lint/typecheck/build + unit tests

---

## Deferred (documented, not required for portfolio)

- [ ] LLM-derived scoring signals (gated in roadmap)
- [ ] PDF export
- [ ] Authentication / multi-tenant dashboard
- [ ] Automated profile promotion in production
- [ ] Cross-source entity resolution beyond dedup keys
- [ ] Production deployment, observability, and SLO runbooks
- [ ] Large real-dataset validation report pack (Week 4 hardening loop)

---

## Known implementation notes

| Topic | State |
|-------|--------|
| `profile_version` | Placeholder `v1` in API; use `profile_row_id` + backup for reproducibility |
| Home route `/` | Redirects to `/dashboard/control` (no marketing landing page) |
| Demo data | `scripts/demo-local.sh` uses `backend/tests/fixtures/propflux/valid_listings.json` |
| Scoring tuning | Ongoing manual iteration on weights/presets—not a code completion item |

---

## Verify after clone

```bash
./scripts/setup.sh
./scripts/lint.sh
./scripts/test.sh
./scripts/demo-local.sh    # optional: requires Postgres
```

See [`setup-checklist.md`](setup-checklist.md) and [`demo.md`](demo.md).

---

## Related documents

- Portfolio README: [`../README.md`](../README.md)
- Master roadmap: [`../.cursor/rules/PROJECT_NOTE.md`](../.cursor/rules/PROJECT_NOTE.md)
- Principal audit (production investor bar): [`project-note-principal-audit.md`](project-note-principal-audit.md)
