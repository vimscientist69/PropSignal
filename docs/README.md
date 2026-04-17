# Documentation Index

This directory is organized so you can quickly find:
- roadmap and scope,
- current project status,
- execution details for each phase,
- and quality/review guidance.

## Source of Truth Map

- Master roadmap and execution plan:
  - `/.cursor/rules/PROJECT_NOTE.md`
- Current status and immediate next-branch checklist:
  - `docs/current-project-status.md`
- Week 2 scoring concept walkthrough:
  - `docs/week2-advanced-scoring-explained.md`
- Consolidated Week 2 implementation playbook (explanation + code map + order):
  - `docs/week2-implementation-playbook.md`
- Week 2 scoring/reasoning interface contract:
  - `docs/week2-interface-contract.md`
- Evaluation protocol (manual/automated/LLM-assisted review):
  - `docs/evaluation-review-protocol.md`
- Principal audit findings and must-fix list:
  - `docs/project-note-principal-audit.md`
- MVP performance plan for larger datasets and multi-dataset selection:
  - `docs/mvp-performance-plan.md`
- Immediate next branch implementation order:
  - `docs/next-phase-execution-plan.md`

## Implementation Detail Docs

- Baseline scoring implementation details:
  - `docs/baseline-scoring-week1.md`
- Data contract:
  - `docs/data-contract-propflux.md`
- Architecture (pre-Week 1 baseline context):
  - `docs/architecture-pre-week1.md`
- CLI usage:
  - `docs/cli-usage.md`
- Setup checklist:
  - `docs/setup-checklist.md`
- Configuration guide:
  - `docs/configuration.md`

## Maintenance Rules

- Keep `PROJECT_NOTE.md` focused on roadmap and decisions.
- Keep execution checklists in `current-project-status.md`.
- Add new deep-dive docs in `docs/` and link them from both:
  - this index,
  - and `PROJECT_NOTE.md` where relevant.
- Avoid duplicating long sections across multiple docs; link instead.
