# Dashboard Guide

The PropSignal dashboard is a Next.js operator console at `/dashboard/*`. It drives the same ranking and persistence APIs as the CLI—no duplicate scoring logic in the browser.

**Access:** [http://localhost:3000/dashboard/control](http://localhost:3000/dashboard/control) when the frontend and backend are running. The browser calls the API at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

---

## Global shell

### What

Shared chrome wraps every tab: left navigation, command palette (⌘/Ctrl + K), and toast notifications.

### Why

Operators switch contexts often (rank → inspect source → compare runs). A consistent shell reduces navigation cost and surfaces feedback without blocking the main workflow.

### How

- **Navigation** — Control Panel, Source Library, Runs, Diagnostics.
- **Command palette** — fuzzy jump to any tab; Escape closes.
- **Toasts** — short success/info messages (e.g. export complete, copied id). Errors from ranking also use an error-styled toast that points to the sticky alert banner at the top of the Control Panel.
- **API errors** — failed requests show a banner with the backend message, field errors, and request id when the API returns the standard error envelope.

---

## Control Panel (`/dashboard/control`)

### What

The **ranking workbench**: select dataset sources, set filters and strategy, run ranking, sort and shortlist results, open listing detail, and export.

### Why

This is the primary decision surface. An analyst configures *what* to score, executes a run, and triages the returned window into exports or a shortlist—without leaving one screen.

### How

**1. Dataset sources**  
Multi-select ingestion jobs (shown as `job:{id}` tokens). Use *Select all* / *Clear all*. At least one source is required to rank.

**2. Filters**  
Optional constraints: province, city, suburb, price range, property type, min bedrooms/bathrooms, min confidence. Empty fields are omitted from the API request.

**3. Strategy**  
- **Preset** — rental income, resale arbitrage, refurbishment value-add, or balanced long-term (loaded from `backend/config/scoring_profiles.yaml`).  
- **Weight overrides** — per-signal numeric overrides within safe bounds shown when a preset is selected. *Reset overrides* restores preset defaults.

**4. Result window**  
- **Top N** — return the highest-scoring N listings.  
- **Pagination** — page + page size for larger windows.

**5. Run ranking**  
Posts to `POST /api/v1/rankings/query`. On success you get a `run_id`, metadata strip, and results table. On failure, a top alert banner shows the full API error; the page scrolls to it and a toast directs you there.

**6. Results table**  
Client-side sort on returned columns (score, confidence, price, etc.). Toggle visible columns; preferences persist in `localStorage` (`propsignal:columns`). Star rows to build a **shortlist** per run (`propsignal:shortlist:{run_id}`).

**7. Listing detail**  
Select a row to load `GET /api/v1/rankings/{run_id}/listings/{listing_id}` in the side panel: `listing_core`, `score_summary`, and `diagnostics` (signal breakdown, comps, ROI assumptions, risk flags).

**8. Exports**  
- **Summary** — current window or shortlist as CSV/JSON (client-generated).  
- **Full detail** — same exports with embedded listing detail payloads.  
- **Server** — download full persisted run via `GET /api/v1/runs/{run_id}/export` (optional `listing_detail=true`).

**Run metadata strip** shows `run_id`, profile id/version, model version, dataset freshness, and record counts for reproducibility.

---

## Source Library (`/dashboard/sources`)

### What

A catalog of **ingestion jobs** available as ranking inputs, with validation context.

### Why

Before ranking, you need confidence that datasets are fresh and valid. Source Library answers: *which jobs exist, what path they came from, and how validation went*—without reading the database or CLI output.

### How

- Data from `GET /api/v1/datasets/sources`.
- **Status filter** — dropdown matching ingestion job status (`created`, `processing`, `completed`, etc.).
- **Search** — case-insensitive match on input path or source token (`job:{id}`).
- **Table** — source token, job id, path, status, valid/invalid counts, finished time.
- **Detail panel** — click a row to view `validation_status` and `validation_summary` as an expandable JSON tree. Copy the source token for use elsewhere.

To add a new source, ingest data via CLI (`ingest <path>`), then refresh this tab.

---

## Runs (`/dashboard/runs`)

### What

Historical **ranking runs** with navigation to detail, exports, and **compare mode**.

### Why

Ranking is iterative. Runs tab lets you reopen past decisions, download exports, and measure what changed between two strategies or filter sets.

### How

- **Run history table** — `GET /api/v1/runs?page=1&page_size=50`: run id, created time, preset, profile, source count, records considered, result count.
- **Per-row actions** — View (detail page), Copy id, Export JSON, Export JSON with full listing detail.
- **Compare mode**  
  - Pick **Baseline** and **Candidate** runs.  
  - Click **Compare runs** — loads both run details and shows a diff:
    - Summary counts: shared listings, changed rows, baseline-only, candidate-only.
    - Metadata diffs (preset, profile, fingerprint, counts).
    - Request snapshot and result window diffs (flattened field paths).
    - Listing-level score, rank, and deal-reason changes within each run’s persisted result set.
  - **Open baseline** / **Open candidate** — jump to run detail routes.

Compare scope is the **saved result window** of each run, not the full universe of listings considered.

---

## Run detail (`/dashboard/runs/[runId]`)

### What

A frozen view of one ranking run: request snapshot, result window, persisted results, and per-listing drill-down.

### Why

Audit and debugging require seeing exactly what was requested and what the server stored—not re-executing the query.

### How

- `GET /api/v1/runs/{run_id}` on load.
- **Snapshot** — `request_snapshot` and `result_window` as JSON trees (filters, strategy, sources, window mode).
- **Results table** — listing id, score, confidence; *Load detail* opens the same listing detail panel as Control Panel.
- **Header exports** — JSON, JSON (full detail), CSV, CSV (full detail) via server export endpoints.

Changing the URL `runId` clears the selected listing to avoid stale detail.

---

## Diagnostics (`/dashboard/diagnostics`)

### What

Operator **health snapshot**: API status, inventory counts, ingestion status mix, recent validations.

### Why

Quick sanity check before a ranking session: is the API up, are there listings, are jobs failing validation?

### How

- `GET /api/v1/diagnostics/summary`
- Displays API status chip, total ranking runs, total listings, ingestion jobs by status (JSON tree), and latest dataset validation summaries.
- Link to Runs for follow-up.

---

## Browser persistence

| Key | Purpose |
|-----|---------|
| `propsignal:columns` | Control Panel table column visibility |
| `propsignal:shortlist:{run_id}` | Starred listing ids for a given run |

These are device-local; they are not synced to the server.

---

## Related docs

- Configuration and term definitions: [`configuration.md`](configuration.md)
- Manual QA checklist: [`dashboard-frontend-test-spec.md`](dashboard-frontend-test-spec.md)
- Week 4 implementation spec (historical): [`week-4-dashboard-full-implementation-spec.md`](week-4-dashboard-full-implementation-spec.md)
