# Dashboard Frontend — Full Testing Specification

This document defines how to verify the PropSignal Next.js dashboard (`/dashboard/*`) end-to-end: navigation, API wiring, state, exports, and error handling. Use it for manual QA, acceptance testing, or as a blueprint for Playwright/Cypress automation.

---

## 1. Purpose and scope

**In scope**

- All routed dashboard surfaces under `frontend/src/app/dashboard/`.
- Root redirect from `/` to `/dashboard/control`.
- Browser-only behavior: `localStorage`, clipboard, file downloads, keyboard shortcuts.
- Integration with backend APIs documented in `docs/configuration.md` (base URL `NEXT_PUBLIC_API_BASE_URL`, default `http://localhost:8000`).

**Out of scope (unless explicitly added later)**

- Backend scoring correctness (covered by backend tests).
- Non-dashboard Next.js routes.
- AuthN/AuthZ (dashboard is open in current product).

---

## 2. Preconditions

| Requirement | Notes |
|-------------|--------|
| Backend running | API reachable at the same origin the dashboard uses (`NEXT_PUBLIC_API_BASE_URL`). |
| Database seeded | At least one ingestion job with valid listings so ranking returns rows (e.g. dev seed or compose stack). |
| Browser | Chromium-based + one of Firefox/Safari for cross-browser smoke. |
| Clipboard | HTTPS or `localhost` for `navigator.clipboard` (some actions copy to clipboard). |
| Downloads | Browser allowed to download multiple files during export tests. |

**Artifacts to collect during a test pass**

- Screenshots or short screen recording for first-time regression baselines.
- Downloaded export files (JSON/CSV) for optional diff against schema expectations.

---

## 3. Global application shell

### 3.1 Root redirect

| ID | Step | Expected |
|----|------|----------|
| GR-01 | Navigate to `/` | Redirect (307/308 or client redirect) to `/dashboard/control`. |
| GR-02 | Open `/dashboard/control` directly | Page loads without redirect loop. |

### 3.2 Layout and navigation

| ID | Step | Expected |
|----|------|----------|
| GN-01 | Observe left sidebar on any `/dashboard/*` route | Brand “PropSignal”, subtitle, four nav links: Control Panel, Source Library, Runs, Diagnostics. |
| GN-02 | Click each nav link | URL matches: `/dashboard/control`, `/dashboard/sources`, `/dashboard/runs`, `/dashboard/diagnostics`. Main content swaps; no full reload flash (client navigation). |
| GN-03 | Visit `/dashboard/runs/some-run-id` | “Runs” nav item appears active (path prefix match). |
| GN-04 | Resize viewport below ~1120px (if testing responsive) | Sidebar stacks / layout does not clip critical actions (per `dashboard.module.css` breakpoints). |

### 3.3 Command palette (⌘/Ctrl + K)

continue here

| ID | Step | Expected |
|----|------|----------|
| CP-01 | Press **Ctrl+K** (Windows/Linux) or **⌘+K** (macOS) | Modal opens; focus in filter input; `aria-modal="true"` on dialog container. |
| CP-02 | Type `run` | List filters to matching nav entries (label or href substring, case-insensitive). |
| CP-03 | Click a palette link | Navigates to route; palette closes. |
| CP-04 | Press **Escape** | Palette closes without navigation. |
| CP-05 | Click **Close** | Palette closes. |
| CP-06 | Open palette, click overlay backdrop (if clickable) or verify only inner palette receives clicks | No accidental navigation; palette behavior consistent. |

### 3.4 Toasts

| ID | Step | Expected |
|----|------|----------|
| TO-01 | After a successful **Run ranking** on Control Panel | Toast appears (role `status`), readable text, auto-dismiss ~4s. |
| TO-02 | Trigger multiple toasts in sequence | New toast replaces or stacks per implementation; no crash; final state returns to empty. |

---

## 4. Control Panel (`/dashboard/control`)

### 4.1 Initial load and data dependencies

| ID | Step | Expected |
|----|------|----------|
| CP-L01 | Load page with backend up | `GET /api/v1/datasets/sources` and `GET /api/v1/scoring/profiles` succeed; sources checkboxes populated; profile dropdown populated. |
| CP-L02 | Load page with backend down / wrong URL | Sticky **alert banner** immediately under the page header (`role="alert"`) with a clear message and the configured API base (`NEXT_PUBLIC_API_BASE_URL`). Control Panel **Sources** card must not claim “no ingestion jobs” until a successful sources fetch returned an empty list. App does not white-screen. |
| CP-L03 | After profiles load, first preset selected | `GET /api/v1/scoring/profiles/{preset}` runs; override grid shows enabled signals and bounds. |

### 4.2 Sources card

| ID | Step | Expected |
|----|------|----------|
| CS-01 | **Select all sources** | Every source checkbox checked. |
| CS-02 | **Clear sources** | No sources selected. |
| CS-03 | **Run ranking** with zero sources | Inline error: select at least one dataset source (client validation). |
| CS-04 | Toggle individual sources | Selection state matches checkbox; “Selected source health” section lists only selected rows. |

### 4.3 Filters card

| ID | Step | Expected |
|----|------|----------|
| FI-01 | Leave filters empty; run ranking | Request body omits empty filter keys (or sends undefined-only fields per client implementation); results return. |
| FI-02 | Set province / city / suburb / price min/max / property type / bedrooms / bathrooms / confidence min | Values appear in `POST /api/v1/rankings/query` payload (verify in Network tab); results reflect filter when data supports it. |
| FI-03 | Invalid numeric fields (non-numeric) | `Number(...)` may yield NaN — note behavior; ideally no silent crash (document actual behavior during test). |

### 4.4 Strategy profile card

| ID | Step | Expected |
|----|------|----------|
| ST-01 | Change preset in dropdown | New `GET /api/v1/scoring/profiles/{preset}`; override inputs reset; signals list updates. |
| ST-02 | Enter weight override within bounds | Included in `strategy.weight_overrides` on submit. |
| ST-03 | Enter override outside bounds | Backend `400` with error envelope; UI shows message. |
| ST-04 | **Reset overrides to preset** | Override fields cleared. |

### 4.5 Result window card

| ID | Step | Expected |
|----|------|----------|
| RW-01 | **Top N** mode | `result_window: { top_n: N }` in request. |
| RW-02 | **Pagination** mode | `result_window: { page, page_size }` in request. |
| RW-03 | Submit with Top N = large number | Capped by backend validation or accepted per API contract. |

### 4.6 Run ranking action

| ID | Step | Expected |
|----|------|----------|
| RK-01 | Click **Run ranking** | Button shows loading (“Running…”); `POST /api/v1/rankings/query` fires. |
| RK-02 | Successful response | Results table populated; run metadata panel shows `run_id`, profile ids, model/freshness fields; toast success. |
| RK-03 | New run clears prior detail selection | Detail panel cleared until user opens detail again (verify UX). |
| RK-04 | Backend error (e.g. unknown source) | Error banner; no partial ranking state or clearly documented partial state. |

### 4.7 Run metadata and copy

| ID | Step | Expected |
|----|------|----------|
| RM-01 | **Copy** next to `run_id` | Clipboard contains exact `run_id`; toast confirms. |
| RM-02 | Export section visible only when `ranking` non-null | Before first run: placeholder copy; after run: export grids. |

### 4.8 Exports — summary (six buttons)

For each export, verify: file downloads, filename pattern, and payload shape (open in editor).

| ID | Action | Expected file / API |
|----|--------|----------------------|
| EX-S01 | Export window CSV | Client-generated CSV; metadata line `# export_metadata: {...}`; data rows match current sorted table rows. |
| EX-S02 | Export window JSON | JSON with `export_metadata` and `results` array; rows match ranking result items (summary fields). |
| EX-S03 | Export shortlist CSV | If shortlist empty: toast instructs user to star rows; no file or empty file per implementation. |
| EX-S04 | Export shortlist JSON | Same as CSV scope; only shortlisted `listing_id`s. |
| EX-S05 | Download full run (server CSV) | `GET /api/v1/runs/{run_id}/export?format=csv`; attachment; includes all persisted run rows. |
| EX-S06 | Download full run (server JSON) | `GET ...?format=json`; `export_metadata` + `results`. |

### 4.9 Exports — full listing detail (six buttons)

**Definition:** Full detail = same composite as the Detail panel / API: `listing_core`, `score_summary`, `diagnostics` per listing.

| ID | Action | Expected |
|----|--------|----------|
| EX-D01 | Export window JSON (full detail) | Parallel `GET /api/v1/rankings/{run_id}/listings/{id}` for each row; final JSON each result has `listing_detail` object with three keys. |
| EX-D02 | Export window CSV (full detail) | Column `listing_detail_json` present; value is escaped JSON string. |
| EX-D03 | Export shortlist JSON (full detail) | Only shortlist ids fetched; `listing_detail` on each. |
| EX-D04 | Export shortlist CSV (full detail) | Same as EX-D02 for shortlist rows only. |
| EX-D05 | Download full run — server JSON (full detail) | `GET ...?format=json&listing_detail=true`; each result includes `listing_detail`. |
| EX-D06 | Download full run — server CSV (full detail) | `GET ...?format=csv&listing_detail=true`; flattened CSV includes serialized nested fields. |
| EX-D07 | While any full-detail client export runs | All export buttons disabled (`exportDetailBusy`); toast indicates fetching N listings. |
| EX-D08 | Full-detail export with one listing failing | Error surface (banner); no silent partial file unless product decision says otherwise. |

**Metadata:** When detail included, `export_metadata.listing_detail_included` is `true` where implemented.

**Filenames:** Client exports use `-full-detail` suffix before extension when detail embedded; server Content-Disposition uses `*-full-detail.*` for detail exports.

### 4.10 Results table

| ID | Step | Expected |
|----|------|----------|
| TB-01 | Column **ID** always visible | Sortable via header control. |
| TB-02 | Sortable headers | Score, confidence, price, city, suburb, province, property type, deal reason — toggling reverses order; indicator shows direction. |
| TB-03 | Column visibility toggles | Toggling hides/shows columns; preference persisted under `localStorage` key `propsignal:columns`. Reload page: preference restored. |
| TB-04 | Row highlight | Selected row for active detail has distinct background (`selectedRow`). |
| TB-05 | **Listing URL** column | “Available” chip if `listing_url` present; “Unavailable” otherwise. |

### 4.11 Row actions

| ID | Step | Expected |
|----|------|----------|
| RA-01 | **Detail** | `GET /api/v1/rankings/{run_id}/listings/{listing_id}`; right panel shows three `JsonTree` sections; skeleton while loading. |
| RA-02 | **Open** (listing URL) | Opens new tab; `rel` includes `noopener noreferrer`. |
| RA-03 | **Copy URL** | Disabled when no URL; otherwise clipboard + toast. |
| RA-04 | **Copy id** | Clipboard contains stringified listing id; toast. |
| RA-05 | Detail request 404 / network error | `detailError` shown; user can retry. |

### 4.12 Shortlist (per run)

| ID | Step | Expected |
|----|------|----------|
| SH-01 | Toggle star on a row | Icon/state toggles; `localStorage` key `propsignal:shortlist:{run_id}` updated JSON array. |
| SH-02 | Reload page after shortlisting | Shortlist state restored for same `run_id`. |
| SH-03 | New ranking run | Shortlist resets for new `run_id` (new storage key); verify no bleed from previous run. |

### 4.13 Listing detail panel

| ID | Step | Expected |
|----|------|----------|
| LD-01 | No row selected | Placeholder copy. |
| LD-02 | **listing_url** strip | If URL present: link + Copy URL; else “Unavailable” chip. |
| LD-03 | **JsonTree** sections | `listing_core`, `score_summary`, `diagnostics` render; nested objects collapsible (`+` / `−`); `normalized_payload` path defaults to collapsed behavior per component rules. |
| LD-04 | Null / empty primitives | Display `—` or equivalent per `JsonTree` empty rules. |

### 4.14 Cross-cutting Control Panel

| ID | Step | Expected |
|----|------|----------|
| XP-01 | Navigate away and back | Ranking state is lost (in-memory only) unless reproduced via Runs — document as expected unless persistence is added. |
| XP-02 | Keyboard focus | Tab through form controls, buttons, table; visible focus ring (`:focus-visible` styles). |

---

## 5. Source Library (`/dashboard/sources`)

| ID | Step | Expected |
|----|------|----------|
| SL-01 | Initial load | `GET /api/v1/datasets/sources` (no query). Table lists sources. |
| SL-02 | **Status** filter | `GET ...?status={value}`; only matching rows. |
| SL-03 | **Search** filter | `GET ...?q={value}`; filters by input path or source token (case-insensitive per backend). |
| SL-04 | Empty filter result | “No sources match filters.” |
| SL-05 | Click row / source button | Row highlights; detail panel shows validation status + `validation_summary` as `JsonTree`. |
| SL-06 | **Copy source token** | Clipboard contains `source` field value. |

---

## 6. Runs (`/dashboard/runs`)

| ID | Step | Expected |
|----|------|----------|
| RN-01 | Initial load | `GET /api/v1/runs?page=1&page_size=50`; table populated when runs exist. |
| RN-02 | No runs | Message to run ranking from Control Panel first. |
| RN-03 | **Compare mode** selects | Baseline and candidate dropdowns populated; links “Open baseline” / “Open candidate” navigate to `/dashboard/runs/{run_id}` when values exist. |
| RN-04 | **View** link | Opens run detail route. |
| RN-05 | **Copy id** | Clipboard contains `run_id`. |
| RN-06 | **Export JSON** link | Opens/downloads `GET /api/v1/runs/{run_id}/export?format=json`. |
| RN-07 | **JSON + detail** link | Same with `listing_detail=true`. |

---

## 7. Run detail (`/dashboard/runs/[runId]`)

| ID | Step | Expected |
|----|------|----------|
| RD-01 | Load with valid `run_id` | `GET /api/v1/runs/{run_id}`; snapshot sections show `request_snapshot` and `result_window` as `JsonTree`. |
| RD-02 | Invalid `run_id` | Error message from API. |
| RD-03 | Header export links | Four links: JSON, JSON (full detail), CSV, CSV (full detail) — correct query strings. |
| RD-04 | Results table **Load detail** | Sets listing id; `RunListingDetail` fetches ranking listing detail; trees render. |
| RD-05 | Navigate between runs (different `run_id`) | Row selection clears (`listing_id` reset effect); no stale detail from previous run. |

---

## 8. Diagnostics (`/dashboard/diagnostics`)

| ID | Step | Expected |
|----|------|----------|
| DG-01 | Initial load | `GET /api/v1/diagnostics/summary`; API status chip; totals; `JsonTree` for ingestion job counts and latest validations. |
| DG-02 | Link to Runs | Navigates to `/dashboard/runs`. |
| DG-03 | API failure | Error banner. |

---

## 9. `localStorage` contract (manual inspection)

| Key | Written by | Verify |
|-----|------------|--------|
| `propsignal:columns` | Control Panel column toggles | JSON object of boolean flags; survives reload. |
| `propsignal:shortlist:{run_id}` | Control Panel shortlist | JSON array of numeric listing ids; correct per run. |

---

## 10. Security and external links

| ID | Step | Expected |
|----|------|----------|
| SEC-01 | Listing URL opened from Control Panel | `target="_blank"` and `rel="noopener noreferrer"` on anchor. |
| SEC-02 | Runs export links | Same for `_blank` export links from dashboard pages. |

---

## 11. Automation mapping (optional)

Suggested Playwright (or Cypress) suites:

1. **smoke.spec.ts** — GR-01, GN-02, CP-01, CP-04, CP-L01, RK-02.
2. **control-exports.spec.ts** — EX-S01–S06, EX-D01–D06 (assert download event or intercept network).
3. **control-table.spec.ts** — TB-02, TB-03, SH-01, RA-01.
4. **nav-palette.spec.ts** — GN-02, CP-02–CP-03.
5. **runs-detail.spec.ts** — RD-01, RD-04, RD-05.

Use `page.request` or route interception to run against a fixed backend or testcontainer.

---

## 12. Exit criteria for a “full pass”

- [ ] All sections **3–8** executed with no blocking defects.
- [ ] At least one **full-detail** JSON export manually inspected: every row has `listing_detail` with `listing_core`, `score_summary`, `diagnostics`.
- [ ] **Clipboard** actions verified on supported origin.
- [ ] **404 / API error** paths show user-readable messages on Control Panel, Sources, Runs, Diagnostics, and Run detail.
- [ ] **Cross-browser smoke** (Chromium + one other) on Control Panel ranking + one export.

---

## 13. Maintenance

When adding dashboard features, extend this document with new **IDs**, API references, and `localStorage` keys. Keep alignment with `docs/week-4-dashboard-full-implementation-spec.md` and `docs/configuration.md`.
