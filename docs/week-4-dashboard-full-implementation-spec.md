# Week 4 Dashboard Full Implementation Specification

This document defines the complete dashboard implementation required before release hardening.
It addresses:
- UI cleanliness and visual quality,
- end-to-end UX and usability gaps,
- complete behavior for all dashboard tabs,
- and richer ranked-listing consumption (URL access, exports, fuller details).

Use this as the execution spec for dashboard completion work before Week 4.

---

## 1) Objective

Deliver a production-usable dashboard that is:
- visually coherent and professional,
- fast to operate for repeated ranking workflows,
- complete across navigation tabs (not placeholder labels),
- and useful for real decision-making with export and deep listing inspection.

The dashboard must remain API-driven and contract-aligned with backend/CLI.

---

## 2) Current Gaps To Close

Based on current behavior and UI state, the main gaps are:
- navigation tabs are mostly placeholders (`Source Library`, `Runs`, `Diagnostics`),
- visual hierarchy is weak (dense forms, low contrast sections, unclear action priority),
- ranked results are not actionable enough (limited columns, no direct listing URL handling),
- listing detail is too shallow for investor workflows,
- no effective export and no "saved latest ranking" workflow,
- missing interaction quality patterns (empty states, skeletons, success feedback, keyboard support).

---

## 3) Product Principles For Dashboard Completion

- **Decision speed:** user reaches "shortlist or export top candidates" in under 2 minutes.
- **Progressive disclosure:** list view stays concise; detail surfaces deep context on demand.
- **Traceability:** every ranking run is reproducible (`run_id`, profile metadata, source context).
- **Consistency:** shared interaction patterns across tabs (filters, tables, status chips, actions).
- **Accessibility:** keyboard and screen-reader support, clear focus states, adequate color contrast.

---

## 4) Information Architecture (Tabs + Required Surfaces)

Week 4 dashboard must include these first-class tabs:

### 4.1 Control Panel (Ranking Workbench)

Purpose:
- configure sources + filters + strategy,
- execute ranking,
- inspect results and open detail.

Required surfaces:
- source selector with quick multi-select controls,
- filter form with sensible grouping and validation hints,
- strategy preset card with override editor and "reset to preset",
- result window controls (`top_n` / pagination),
- results table with sortable display columns (client-sort on returned rows only),
- detail panel/drawer with full listing and diagnostics,
- run metadata strip with copy affordances.

### 4.2 Source Library

Purpose:
- manage and inspect available dataset sources/jobs used for ranking.

Required surfaces:
- source list table (job id, input path, status, valid/invalid counts, timestamps),
- search and status filter,
- source-level quick actions:
  - copy source token,
  - include in Control Panel selection,
  - inspect validation summary,
- source details panel:
  - ingest summary,
  - validation summary,
  - rejection reason breakdown,
  - freshness metadata.

### 4.3 Runs

Purpose:
- browse historical ranking runs and reuse prior run context.

Required surfaces:
- run history table:
  - `run_id`, created time, profile id, source count, records considered, result count,
  - latency summary if available,
- run-level actions:
  - view run results,
  - export run,
  - copy run id,
  - open compare mode (select baseline/candidate run),
- run details page/panel:
  - request snapshot (filters, strategy, result window),
  - results list from run context,
  - run diagnostics and profile linkage (`profile_row_id`).

### 4.4 Diagnostics

Purpose:
- expose health, quality, and performance signals for operators.

Required surfaces:
- API/status snapshot (service health + recent error count),
- performance indicators:
  - ranking/list/detail latency summaries,
  - recent SLO met/missed counts,
- quality indicators:
  - latest dataset validation summaries,
  - key scoring sanity/evaluation signals,
- clear links out to corresponding run/source records.

### 4.5 Global Utility Surfaces

Required globally:
- command/search palette (`Cmd/Ctrl+K`) for quick nav and actions,
- global toast system for success/error/info,
- unsaved-state guard where relevant (overrides/filters edits),
- consistent loading skeletons and empty-state call-to-actions.

---

## 5) UI Cleanliness And Visual Aesthetics Requirements

### 5.1 Visual System

- Establish design tokens in frontend for:
  - spacing scale,
  - semantic colors (bg/surface/text/border/success/warn/error/accent),
  - radius/elevation,
  - typography scale and weights.
- Replace ad-hoc color usage with tokenized theme primitives.
- Improve contrast for body text and input labels to pass accessibility checks.

### 5.2 Layout And Density

- Increase whitespace between major sections to reduce visual crowding.
- Use consistent section headers with short helper text.
- Split dense form blocks into grouped cards:
  - Sources,
  - Filters,
  - Strategy,
  - Result Window.
- Keep primary action ("Run ranking") visually dominant and sticky in long forms.

### 5.3 Component Consistency

- Standardize buttons into variants (`primary`, `secondary`, `ghost`, `danger`).
- Standardize status chips (`analyzed`, `completed_with_errors`, `failed`, etc.).
- Standardize table styling (headers, row hover, selected row, empty row state).
- Standardize input behavior:
  - inline validation messages,
  - numeric field formatting,
  - clear/reset affordances.

### 5.4 Motion And Feedback

- Add subtle transition states for panel open/close and selection changes.
- Use skeleton loaders rather than blank content during fetch.
- Show explicit completion feedback after ranking and exports.

---

## 6) UX Requirements (End-to-End)

### 6.1 Primary workflow

Target flow:
1. User picks sources.
2. Applies filters and strategy.
3. Runs ranking.
4. Scans top results quickly.
5. Opens details for shortlisting.
6. Exports selected/all results.
7. Optionally reopens run from history.

Requirements:
- no dead-end states,
- no hidden critical actions,
- clear error recovery paths (invalid filters, no results, failed detail fetch).

### 6.2 Interaction quality

- Keyboard navigable forms and tables.
- Focus management after async actions (run completion, detail open).
- Persist user preferences:
  - last tab,
  - last result window mode,
  - visible columns.
- Preserve ranking context when moving between results and details.

### 6.3 Error and empty states

Must include actionable copy for:
- no sources available,
- no ranked results,
- detail unavailable for selected listing,
- API/network failure,
- export failure.

---

## 7) Ranked Listings Utility Upgrades (Critical)

This section is mandatory; current behavior is insufficient.

### 7.1 Results table improvements

Add columns (configurable visibility):
- score,
- confidence,
- price,
- city/suburb/province,
- property type,
- bedrooms/bathrooms,
- `deal_reason`,
- listing source,
- `listing_url` presence/status,
- quick actions.

Quick row actions:
- Open detail,
- Open original listing URL in new tab,
- Copy listing URL,
- Copy listing identifier,
- Add to shortlist (local UI state for this run).

### 7.2 Export capabilities

Provide export actions at run and selection level:
- Export current result window to CSV.
- Export all rows for current run to CSV/JSON.
- Export shortlist only.
- Include export metadata header:
  - `run_id`,
  - generated timestamp,
  - strategy preset/profile id,
  - source set,
  - applied filters.

### 7.3 Listing URL support

Requirements:
- show canonical `listing_url` if available,
- gracefully handle missing URL (`Unavailable` state),
- external links open safely (`noopener`, `noreferrer`),
- expose copy URL action everywhere detail is shown.

### 7.4 Full listing detail requirements

Listing detail must render **every field** the listing detail API returns for that listing. The authoritative set is the backend contract (response schema), not a fixed checklist in this document: as the contract grows, the UI must show new fields without requiring a spec rewrite.

- Organize presentation (grouping, ordering, labels) for scannability, but do not omit any key present in the listing detail response.
- For `null`, empty string, or empty collection values, render an explicit empty state (`—`, `N/A`, or equivalent) instead of silently dropping the field.
- Nested or verbose structures (e.g. raw ingest payload, large maps) may use progressive disclosure (collapsed by default) as long as the full tree remains reachable in the same view.
- If the product needs a value the API does not expose, extend the backend contract; the UI must not invent or infer data not present in the response.

---

## 8) Backend/API Contract Additions Needed For Dashboard Completion

### 8.1 Ranking response enrichment

Add optional typed summary fields in `results[]` (instead of opaque `summary` map only):
- `listing_url`,
- `bedrooms`,
- `bathrooms`,
- `province`,
- `source_site` (if available),
- any additional fields needed for table-first decisioning.

### 8.2 Listing detail enrichment

Extend listing detail contract to include fuller `listing_core` shape:
- include all stable, non-sensitive fields already available in normalized listing storage where possible.

### 8.3 Runs and diagnostics APIs

Add endpoints for tab support:
- `GET /api/v1/runs` (paged run summaries),
- `GET /api/v1/runs/{run_id}` (run metadata + request snapshot),
- `GET /api/v1/runs/{run_id}/export` (CSV/JSON export),
- `GET /api/v1/diagnostics/summary` (health + quality/performance aggregates),
- extend source summary endpoint as needed for Source Library filtering and detail.

Keep handlers thin and reuse service layer contracts.

---

## 9) Frontend Implementation Plan

### Phase 1: Foundation and design system
- introduce tokens and shared primitives (cards, buttons, chips, table, form fields),
- refactor current Control Panel layout to use primitives,
- add consistent states (loading/empty/error/success).

### Phase 2: Complete tab architecture
- convert placeholder nav items into routed tab views,
- implement Source Library and Runs with real backend data,
- implement Diagnostics overview tab.

### Phase 3: Listing utility and exports
- expand results table and row actions,
- implement shortlist interactions,
- implement export UX and download flows,
- integrate listing URL actions.

### Phase 4: Detail depth and polish
- deliver richer detail panel structure,
- add raw payload drill-down,
- finalize keyboard/accessibility QA and responsive behavior.

---

## 10) Testing and Verification Requirements

### 10.1 Frontend tests
- component tests for key primitives and table actions,
- integration tests for primary ranking flow and tab navigation,
- interaction tests for exports, URL actions, and shortlist behavior.

### 10.2 API tests
- contract tests for new runs/diagnostics/export endpoints,
- validation and error envelope tests for new query params,
- export content tests (columns + metadata headers).

### 10.3 Smoke/E2E checks
- end-to-end flow:
  source select -> rank -> detail -> export -> reopen from runs tab.
- verify no regressions in existing Week 3 ranking and detail contracts.

Quality gates before merge:
- `./scripts/lint.sh`
- `./scripts/test.sh`
- `npm --prefix frontend run build`

---

## 11) Definition of Done (Dashboard Full Implementation)

Done when all are true:
- all dashboard tabs are functional and API-backed (no placeholder nav pages),
- Control Panel is visually clean and interaction-consistent,
- ranked listings are actionable (URL open/copy, shortlist, export),
- listing detail includes substantially richer context than minimal core,
- run history and diagnostics are usable for operator workflows,
- accessibility and keyboard interaction baseline is satisfied,
- required lint/test/build gates pass,
- docs are updated with final API and UX behavior.

---

## 12) Explicit Out-of-Scope For This Spec

- automated model tuning loops,
- major scoring formula redesign,
- enterprise auth/permissions model,
- multi-tenant dashboard partitioning.

These remain separate roadmap tracks.
