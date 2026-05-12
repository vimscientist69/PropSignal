"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { JsonTree } from "../components/JsonTree";
import { useToast } from "../components/DashboardChrome";
import styles from "../dashboard.module.css";
import { API_BASE, fetchJson, fetchListingDetailsForRun } from "../lib/api";
import { buildExportMetadata, exportRankingCsv, exportRankingJson } from "../lib/exportRanking";
import type {
  ListingDetail,
  ProfileDetail,
  ProfileSummary,
  RankingResponse,
  RankingResult,
  SourceSummary,
} from "../lib/types";

type SortKey =
  | "score"
  | "confidence"
  | "price"
  | "city"
  | "suburb"
  | "province"
  | "property_type"
  | "deal_reason"
  | "listing_id";

const DEFAULT_COLUMNS: Record<string, boolean> = {
  score: true,
  confidence: true,
  price: true,
  city: true,
  suburb: true,
  province: true,
  property_type: true,
  deal_reason: true,
  source_site: true,
  listing_url: true,
  bedrooms: true,
  bathrooms: true,
  shortlist: true,
  actions: true,
};

const LS_COLUMNS = "propsignal:columns";

function loadColumnPrefs(): Record<string, boolean> {
  if (typeof window === "undefined") {
    return DEFAULT_COLUMNS;
  }
  try {
    const raw = window.localStorage.getItem(LS_COLUMNS);
    if (!raw) {
      return DEFAULT_COLUMNS;
    }
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return { ...DEFAULT_COLUMNS, ...parsed };
  } catch {
    return DEFAULT_COLUMNS;
  }
}

function shortlistKey(runId: string) {
  return `propsignal:shortlist:${runId}`;
}

function loadShortlist(runId: string): Set<number> {
  if (typeof window === "undefined") {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(shortlistKey(runId));
    if (!raw) {
      return new Set();
    }
    const arr = JSON.parse(raw) as number[];
    return new Set(arr);
  } catch {
    return new Set();
  }
}

function saveShortlist(runId: string, ids: Set<number>) {
  window.localStorage.setItem(shortlistKey(runId), JSON.stringify([...ids]));
}

function sortValue(row: RankingResult, key: SortKey): string | number {
  const s = row.summary;
  switch (key) {
    case "score":
      return row.score;
    case "confidence":
      return row.confidence;
    case "price":
      return Number(s.price ?? 0);
    case "city":
      return String(s.city ?? "");
    case "suburb":
      return String(s.suburb ?? "");
    case "province":
      return String(row.province ?? s.province ?? "");
    case "property_type":
      return String(s.property_type ?? "");
    case "deal_reason":
      return row.deal_reason;
    case "listing_id":
    default:
      return row.listing_id;
  }
}

async function copyText(text: string) {
  await navigator.clipboard.writeText(text);
}

export function ControlWorkbench() {
  const { pushToast } = useToast();
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>("rental_income");
  const [profileDetail, setProfileDetail] = useState<ProfileDetail | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [activeDetail, setActiveDetail] = useState<ListingDetail | null>(null);
  const [activeListingId, setActiveListingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sourcesReady, setSourcesReady] = useState<"pending" | "success" | "failed">("pending");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportDetailBusy, setExportDetailBusy] = useState(false);
  const [windowMode, setWindowMode] = useState<"top_n" | "pagination">("top_n");
  const [topN, setTopN] = useState("10");
  const [page, setPage] = useState("1");
  const [pageSize, setPageSize] = useState("20");
  const [province, setProvince] = useState("");
  const [city, setCity] = useState("");
  const [suburb, setSuburb] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [propertyType, setPropertyType] = useState("");
  const [bedroomsMin, setBedroomsMin] = useState("");
  const [bathroomsMin, setBathroomsMin] = useState("");
  const [confidenceMin, setConfidenceMin] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [columns, setColumns] = useState<Record<string, boolean>>(DEFAULT_COLUMNS);
  const [shortlist, setShortlist] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    setColumns(loadColumnPrefs());
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LS_COLUMNS, JSON.stringify(columns));
    }
  }, [columns]);

  useEffect(() => {
    if (!ranking) {
      setShortlist(new Set());
      return;
    }
    setShortlist(loadShortlist(ranking.run_id));
  }, [ranking]);

  useEffect(() => {
    const loadInitial = async () => {
      try {
        const [sourceRows, profileRows] = await Promise.all([
          fetchJson<SourceSummary[]>("/api/v1/datasets/sources"),
          fetchJson<ProfileSummary[]>("/api/v1/scoring/profiles"),
        ]);
        setSources(sourceRows);
        setProfiles(profileRows);
        setSelectedSources(sourceRows.map((row) => row.source));
        if (profileRows.length > 0) {
          setSelectedPreset(profileRows[0].preset);
        }
        setSourcesReady("success");
        setLoadError(null);
      } catch (loadError_) {
        setSourcesReady("failed");
        setLoadError((loadError_ as Error).message);
      }
    };
    void loadInitial();
  }, []);

  useEffect(() => {
    const loadPreset = async () => {
      try {
        const detail = await fetchJson<ProfileDetail>(`/api/v1/scoring/profiles/${selectedPreset}`);
        setProfileDetail(detail);
        setOverrides({});
        setError(null);
      } catch (presetError) {
        setError((presetError as Error).message);
      }
    };
    if (selectedPreset) {
      void loadPreset();
    }
  }, [selectedPreset]);

  const selectedSourceRows = useMemo(
    () => sources.filter((source) => selectedSources.includes(source.source)),
    [sources, selectedSources],
  );

  const filterPayload = useMemo(
    () => ({
      province: province || undefined,
      city: city || undefined,
      suburb: suburb || undefined,
      price_min: priceMin ? Number(priceMin) : undefined,
      price_max: priceMax ? Number(priceMax) : undefined,
      property_type: propertyType || undefined,
      bedrooms_min: bedroomsMin ? Number(bedroomsMin) : undefined,
      bathrooms_min: bathroomsMin ? Number(bathroomsMin) : undefined,
      confidence_min: confidenceMin ? Number(confidenceMin) : undefined,
    }),
    [
      province,
      city,
      suburb,
      priceMin,
      priceMax,
      propertyType,
      bedroomsMin,
      bathroomsMin,
      confidenceMin,
    ],
  );

  const sortedResults = useMemo(() => {
    if (!ranking) {
      return [];
    }
    const rows = [...ranking.results];
    rows.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const mul = sortDir === "desc" ? -1 : 1;
      if (typeof av === "number" && typeof bv === "number") {
        return av === bv ? a.listing_id - b.listing_id : av < bv ? -1 * mul : 1 * mul;
      }
      const as = String(av);
      const bs = String(bv);
      if (as === bs) {
        return a.listing_id - b.listing_id;
      }
      return as < bs ? -1 * mul : 1 * mul;
    });
    return rows;
  }, [ranking, sortKey, sortDir]);

  const setOverrideValue = (signal: string, next: string) => {
    setOverrides((current) => ({ ...current, [signal]: next }));
  };

  const resetOverrides = () => setOverrides({});

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir(key === "score" || key === "confidence" || key === "price" ? "desc" : "asc");
    }
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setDetailError(null);
    setRanking(null);
    setActiveDetail(null);
    setActiveListingId(null);
    if (selectedSources.length === 0) {
      setError("Select at least one dataset source.");
      return;
    }
    setLoading(true);
    try {
      const body = {
        dataset_sources: selectedSources,
        filters: filterPayload,
        strategy: {
          preset: selectedPreset,
          weight_overrides: Object.fromEntries(
            Object.entries(overrides)
              .filter(([, value]) => value.trim().length > 0)
              .map(([signal, value]) => [signal, Number(value)]),
          ),
        },
        result_window:
          windowMode === "top_n"
            ? { top_n: Number(topN) }
            : { page: Number(page), page_size: Number(pageSize) },
        sort_mode: "score_desc",
      };
      const response = await fetchJson<RankingResponse>("/api/v1/rankings/query", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setRanking(response);
      setLoadError(null);
      pushToast("Ranking completed.");
    } catch (submitError) {
      setError((submitError as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const onFetchDetail = async (listingId: number) => {
    if (!ranking) {
      return;
    }
    setActiveListingId(listingId);
    setDetailError(null);
    setActiveDetail(null);
    setDetailLoading(true);
    try {
      const detail = await fetchJson<ListingDetail>(
        `/api/v1/rankings/${ranking.run_id}/listings/${listingId}`,
      );
      setActiveDetail(detail);
    } catch (detailErr) {
      setDetailError((detailErr as Error).message);
    } finally {
      setDetailLoading(false);
    }
  };

  const toggleShortlist = (listingId: number) => {
    if (!ranking) {
      return;
    }
    setShortlist((prev) => {
      const next = new Set(prev);
      if (next.has(listingId)) {
        next.delete(listingId);
      } else {
        next.add(listingId);
      }
      saveShortlist(ranking.run_id, next);
      return next;
    });
  };

  const exportWindow = (fmt: "csv" | "json") => {
    if (!ranking) {
      return;
    }
    const meta = buildExportMetadata(ranking, {
      strategy_preset: selectedPreset,
      filters: filterPayload,
    });
    if (fmt === "json") {
      exportRankingJson(ranking, sortedResults, meta);
    } else {
      exportRankingCsv(ranking, sortedResults, meta);
    }
    pushToast(`Exported current window (${fmt.toUpperCase()}).`);
  };

  const exportWindowWithDetail = async (fmt: "csv" | "json") => {
    if (!ranking) {
      return;
    }
    const ids = sortedResults.map((r) => r.listing_id);
    setExportDetailBusy(true);
    try {
      pushToast(`Fetching full detail for ${ids.length} listing(s)…`);
      const details = await fetchListingDetailsForRun(ranking.run_id, ids);
      const meta = buildExportMetadata(ranking, {
        strategy_preset: selectedPreset,
        filters: filterPayload,
        listing_detail_included: true,
      });
      if (fmt === "json") {
        exportRankingJson(ranking, sortedResults, meta, { detailsByListingId: details });
      } else {
        exportRankingCsv(ranking, sortedResults, meta, { detailsByListingId: details });
      }
      pushToast(`Exported current window with full detail (${fmt.toUpperCase()}).`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExportDetailBusy(false);
    }
  };

  const exportShortlistOnly = (fmt: "csv" | "json") => {
    if (!ranking) {
      return;
    }
    const rows = sortedResults.filter((r) => shortlist.has(r.listing_id));
    if (rows.length === 0) {
      pushToast("Shortlist is empty — star rows first.");
      return;
    }
    const meta = buildExportMetadata(ranking, {
      strategy_preset: selectedPreset,
      filters: { ...filterPayload, export_scope: "shortlist" },
    });
    if (fmt === "json") {
      exportRankingJson(ranking, rows, meta);
    } else {
      exportRankingCsv(ranking, rows, meta);
    }
    pushToast(`Exported shortlist (${fmt.toUpperCase()}).`);
  };

  const exportShortlistWithDetail = async (fmt: "csv" | "json") => {
    if (!ranking) {
      return;
    }
    const rows = sortedResults.filter((r) => shortlist.has(r.listing_id));
    if (rows.length === 0) {
      pushToast("Shortlist is empty — star rows first.");
      return;
    }
    const ids = rows.map((r) => r.listing_id);
    setExportDetailBusy(true);
    try {
      pushToast(`Fetching full detail for ${ids.length} shortlist listing(s)…`);
      const details = await fetchListingDetailsForRun(ranking.run_id, ids);
      const meta = buildExportMetadata(ranking, {
        strategy_preset: selectedPreset,
        filters: { ...filterPayload, export_scope: "shortlist" },
        listing_detail_included: true,
      });
      if (fmt === "json") {
        exportRankingJson(ranking, rows, meta, { detailsByListingId: details });
      } else {
        exportRankingCsv(ranking, rows, meta, { detailsByListingId: details });
      }
      pushToast(`Exported shortlist with full detail (${fmt.toUpperCase()}).`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExportDetailBusy(false);
    }
  };

  const exportServerRun = async (fmt: "csv" | "json", listingDetail = false) => {
    if (!ranking) {
      return;
    }
    try {
      const q = new URLSearchParams({ format: fmt });
      if (listingDetail) {
        q.set("listing_detail", "true");
      }
      const res = await fetch(`${API_BASE}/api/v1/runs/${ranking.run_id}/export?${q.toString()}`);
      if (!res.ok) {
        throw new Error(`Export failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${ranking.run_id}${listingDetail ? "-full-detail" : ""}.${fmt}`;
      a.rel = "noopener";
      a.click();
      URL.revokeObjectURL(url);
      pushToast(
        `Downloaded full run export (${fmt.toUpperCase()}${listingDetail ? ", with listing detail" : ""}).`,
      );
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const listingUrlForDetail = activeDetail?.listing_core.listing_url;
  const listingUrlStr =
    typeof listingUrlForDetail === "string" && listingUrlForDetail.length > 0
      ? listingUrlForDetail
      : null;

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div>
          <p className={styles.envBadge}>Live ranking environment</p>
          <h1 className={styles.title}>Control Panel</h1>
          <p className={styles.subTitle}>
            Configure sources, filters, and strategy — then inspect ranked listings and exports.
          </p>
        </div>
        <div className={styles.topStats}>
          <div className={styles.statTile}>
            <span>Sources</span>
            <strong>{selectedSources.length}</strong>
          </div>
          <div className={styles.statTile}>
            <span>Records</span>
            <strong>{ranking?.dataset_context.records_considered ?? "—"}</strong>
          </div>
        </div>
      </header>

      {loadError || error ? (
        <div role="alert" className={styles.errorBanner}>
          {loadError ? (
            <p>
              <strong>Cannot load dashboard data.</strong> {loadError}{" "}
              <span className={styles.mutedLabel}>
                (API base: <kbd>{API_BASE}</kbd>)
              </span>
            </p>
          ) : null}
          {error ? (
            <p>
              <strong>Action failed.</strong> {error}
            </p>
          ) : null}
        </div>
      ) : null}

      <section className={styles.mainGrid}>
        <form onSubmit={onSubmit} className={styles.controlPanel}>
          <div className={styles.rowBetween}>
            <h2 className={styles.sectionTitle}>Ranking workbench</h2>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.ghostButton}
                onClick={() => setSelectedSources(sources.map((s) => s.source))}
              >
                Select all sources
              </button>
              <button type="button" className={styles.ghostButton} onClick={() => setSelectedSources([])}>
                Clear sources
              </button>
            </div>
          </div>
          <p className={styles.sectionHint}>
            Grouped cards: sources, validation snapshot, filters, strategy, and result window.
          </p>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Sources</h3>
            <div className={styles.sourceList}>
              {sourcesReady === "pending" && sources.length === 0 ? (
                <p className={styles.mutedLabel}>Loading sources from the API…</p>
              ) : sourcesReady === "failed" ? (
                <p className={styles.error}>
                  Sources could not be loaded (see the alert above). This is usually a stopped backend,
                  wrong <code>NEXT_PUBLIC_API_BASE_URL</code>, or a browser network/CORS block.
                </p>
              ) : sources.length === 0 ? (
                <p className={styles.mutedLabel}>
                  No ingestion jobs found. Ingest data first, then refresh this page.
                </p>
              ) : (
                sources.map((source) => (
                  <label key={source.source} className={styles.sourceItem}>
                    <input
                      type="checkbox"
                      checked={selectedSources.includes(source.source)}
                      onChange={(event) =>
                        setSelectedSources((current) =>
                          event.target.checked
                            ? [...current, source.source]
                            : current.filter((item) => item !== source.source),
                        )
                      }
                    />
                    <span>{source.source}</span>
                    <small>
                      {source.status} · {source.records_valid}/{source.records_total} valid
                    </small>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Selected source health</h3>
            <div className={styles.statusGrid}>
              {selectedSourceRows.length === 0 ? (
                <p className={styles.mutedLabel}>Select sources to see validation context.</p>
              ) : (
                selectedSourceRows.map((row) => (
                  <article key={`status-${row.source}`} className={styles.statusCell}>
                    <strong>{row.source}</strong>
                    <p>Status: {row.status}</p>
                    <p>Validation: {row.validation_status ?? "n/a"}</p>
                  </article>
                ))
              )}
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Filters</h3>
            <div className={styles.grid}>
              <input placeholder="Province" value={province} onChange={(e) => setProvince(e.target.value)} />
              <input placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
              <input placeholder="Suburb" value={suburb} onChange={(e) => setSuburb(e.target.value)} />
              <input placeholder="Price min" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
              <input placeholder="Price max" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
              <input
                placeholder="Property type"
                value={propertyType}
                onChange={(e) => setPropertyType(e.target.value)}
              />
              <input
                placeholder="Bedrooms min"
                value={bedroomsMin}
                onChange={(e) => setBedroomsMin(e.target.value)}
              />
              <input
                placeholder="Bathrooms min"
                value={bathroomsMin}
                onChange={(e) => setBathroomsMin(e.target.value)}
              />
              <input
                placeholder="Confidence min"
                value={confidenceMin}
                onChange={(e) => setConfidenceMin(e.target.value)}
              />
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Strategy profile</h3>
            <select value={selectedPreset} onChange={(e) => setSelectedPreset(e.target.value)}>
              {profiles.map((profile) => (
                <option key={profile.preset} value={profile.preset}>
                  {profile.label}
                </option>
              ))}
            </select>
            <div className={styles.overrideGrid}>
              {profileDetail?.enabled_signals.map((signal) => {
                const bounds = profileDetail.safe_override_bounds[signal];
                return (
                  <label key={signal} className={styles.overrideItem}>
                    <span>
                      {signal} [{bounds.min.toFixed(3)}, {bounds.max.toFixed(3)}]
                    </span>
                    <input
                      value={overrides[signal] ?? ""}
                      onChange={(e) => setOverrideValue(signal, e.target.value)}
                      placeholder={String(profileDetail.default_weights[signal] ?? "")}
                    />
                  </label>
                );
              })}
            </div>
            <button type="button" className={styles.ghostButton} onClick={resetOverrides}>
              Reset overrides to preset
            </button>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Result window</h3>
            <div className={styles.inline}>
              <label className={styles.radio}>
                <input
                  type="radio"
                  checked={windowMode === "top_n"}
                  onChange={() => setWindowMode("top_n")}
                />
                Top N
              </label>
              <label className={styles.radio}>
                <input
                  type="radio"
                  checked={windowMode === "pagination"}
                  onChange={() => setWindowMode("pagination")}
                />
                Pagination
              </label>
            </div>
            {windowMode === "top_n" ? (
              <input value={topN} onChange={(e) => setTopN(e.target.value)} placeholder="Top N" />
            ) : (
              <div className={styles.inline}>
                <input value={page} onChange={(e) => setPage(e.target.value)} placeholder="Page" />
                <input value={pageSize} onChange={(e) => setPageSize(e.target.value)} placeholder="Page size" />
              </div>
            )}
          </div>

          <div className={styles.stickyActions}>
            <button type="submit" className={styles.primaryButton} disabled={loading}>
              {loading ? "Running…" : "Run ranking"}
            </button>
          </div>
        </form>

        <section className={styles.sidePanel}>
          <h2 className={styles.sectionTitle}>Run metadata</h2>
          <p className={styles.sectionHint}>Reproducibility: run id, profile, and dataset freshness.</p>
          {ranking ? (
            <div className={styles.metaGrid}>
              <p>
                <span className={styles.mutedLabel}>run_id</span>
                <br />
                <code>{ranking.run_id}</code>{" "}
                <button
                  type="button"
                  className={styles.iconBtn}
                  onClick={() => void copyText(ranking.run_id).then(() => pushToast("Copied run id"))}
                >
                  Copy
                </button>
              </p>
              <p>
                profile_id: <strong>{ranking.resolved_profile.profile_id}</strong>
              </p>
              <p>profile_version: {ranking.resolved_profile.profile_version}</p>
              <p>model_version: {ranking.dataset_context.model_version ?? "n/a"}</p>
              <p>last_ingested_at: {ranking.dataset_context.last_ingested_at ?? "n/a"}</p>
              <p>last_scored_at: {ranking.dataset_context.last_scored_at ?? "n/a"}</p>
              <p className={styles.sectionHint}>
                Summary rows match the results table. “Full detail” adds the same payload as the Detail action
                (listing_core, score_summary, diagnostics) per listing.
              </p>
              <p className={styles.blockTitle}>Summary</p>
              <div className={styles.exportGrid}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => exportWindow("csv")}
                >
                  Export window CSV
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => exportWindow("json")}
                >
                  Export window JSON
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => exportShortlistOnly("csv")}
                >
                  Export shortlist CSV
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => exportShortlistOnly("json")}
                >
                  Export shortlist JSON
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("csv", false)}
                >
                  Download full run (server CSV)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("json", false)}
                >
                  Download full run (server JSON)
                </button>
              </div>
              <p className={styles.blockTitle}>With full listing detail</p>
              <div className={styles.exportGrid}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportWindowWithDetail("csv")}
                >
                  Export window CSV (full detail)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportWindowWithDetail("json")}
                >
                  Export window JSON (full detail)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportShortlistWithDetail("csv")}
                >
                  Export shortlist CSV (full detail)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportShortlistWithDetail("json")}
                >
                  Export shortlist JSON (full detail)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("csv", true)}
                >
                  Download full run — server CSV (full detail)
                </button>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("json", true)}
                >
                  Download full run — server JSON (full detail)
                </button>
              </div>
            </div>
          ) : (
            <p className={styles.mutedLabel}>Run ranking to populate metadata and export actions.</p>
          )}
        </section>
      </section>

      <section className={styles.bottomGrid}>
        <section className={styles.resultsPanel}>
          <div className={styles.rowBetween}>
            <h2 className={styles.sectionTitle}>Ranked results</h2>
            <span className={styles.mutedLabel}>{ranking?.results.length ?? 0} rows</span>
          </div>
          {!ranking ? (
            <p className={styles.mutedLabel}>Run ranking to populate the results table.</p>
          ) : ranking.results.length === 0 ? (
            <p className={styles.mutedLabel}>No rows matched filters — widen filters or sources.</p>
          ) : (
            <>
              <div className={styles.columnToggles}>
                <span>Show columns:</span>
                {Object.keys(DEFAULT_COLUMNS).map((key) => (
                  <label key={key}>
                    <input
                      type="checkbox"
                      checked={columns[key] !== false}
                      onChange={(e) => setColumns((c) => ({ ...c, [key]: e.target.checked }))}
                    />
                    {key.replace("_", " ")}
                  </label>
                ))}
              </div>
              <div className={styles.dataTableWrap}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>
                        <button type="button" className={styles.sortBtn} onClick={() => toggleSort("listing_id")}>
                          ID{sortKey === "listing_id" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                        </button>
                      </th>
                      {columns.score ? (
                        <th>
                          <button type="button" className={styles.sortBtn} onClick={() => toggleSort("score")}>
                            Score{sortKey === "score" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.confidence ? (
                        <th>
                          <button
                            type="button"
                            className={styles.sortBtn}
                            onClick={() => toggleSort("confidence")}
                          >
                            Conf{sortKey === "confidence" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.price ? (
                        <th>
                          <button type="button" className={styles.sortBtn} onClick={() => toggleSort("price")}>
                            Price{sortKey === "price" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.city ? (
                        <th>
                          <button type="button" className={styles.sortBtn} onClick={() => toggleSort("city")}>
                            City{sortKey === "city" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.suburb ? (
                        <th>
                          <button type="button" className={styles.sortBtn} onClick={() => toggleSort("suburb")}>
                            Suburb{sortKey === "suburb" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.province ? (
                        <th>
                          <button type="button" className={styles.sortBtn} onClick={() => toggleSort("province")}>
                            Prov{sortKey === "province" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.property_type ? (
                        <th>
                          <button
                            type="button"
                            className={styles.sortBtn}
                            onClick={() => toggleSort("property_type")}
                          >
                            Type{sortKey === "property_type" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.bedrooms ? <th>Beds</th> : null}
                      {columns.bathrooms ? <th>Baths</th> : null}
                      {columns.deal_reason ? (
                        <th>
                          <button
                            type="button"
                            className={styles.sortBtn}
                            onClick={() => toggleSort("deal_reason")}
                          >
                            Deal reason{sortKey === "deal_reason" ? (sortDir === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      ) : null}
                      {columns.source_site ? <th>Source</th> : null}
                      {columns.listing_url ? <th>Listing URL</th> : null}
                      {columns.shortlist ? <th>★</th> : null}
                      {columns.actions ? <th>Actions</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedResults.map((result) => (
                      <tr
                        key={result.listing_id}
                        className={activeListingId === result.listing_id ? styles.selectedRow : undefined}
                      >
                        <td>{result.listing_id}</td>
                        {columns.score ? <td>{result.score.toFixed(4)}</td> : null}
                        {columns.confidence ? <td>{result.confidence.toFixed(2)}</td> : null}
                        {columns.price ? <td>{String(result.summary.price ?? "—")}</td> : null}
                        {columns.city ? <td>{String(result.summary.city ?? "—")}</td> : null}
                        {columns.suburb ? <td>{String(result.summary.suburb ?? "—")}</td> : null}
                        {columns.province ? <td>{String(result.province ?? "—")}</td> : null}
                        {columns.property_type ? <td>{String(result.summary.property_type ?? "—")}</td> : null}
                        {columns.bedrooms ? <td>{result.bedrooms ?? "—"}</td> : null}
                        {columns.bathrooms ? <td>{result.bathrooms ?? "—"}</td> : null}
                        {columns.deal_reason ? <td>{result.deal_reason}</td> : null}
                        {columns.source_site ? <td>{result.source_site ?? "—"}</td> : null}
                        {columns.listing_url ? (
                          <td>
                            {result.listing_url ? (
                              <span className={styles.chip}>Available</span>
                            ) : (
                              <span className={`${styles.chip} ${styles.chipWarn}`}>Unavailable</span>
                            )}
                          </td>
                        ) : null}
                        {columns.shortlist ? (
                          <td>
                            <button
                              type="button"
                              className={styles.iconBtn}
                              aria-pressed={shortlist.has(result.listing_id)}
                              onClick={() => toggleShortlist(result.listing_id)}
                            >
                              {shortlist.has(result.listing_id) ? "★" : "☆"}
                            </button>
                          </td>
                        ) : null}
                        {columns.actions ? (
                          <td>
                            <div className={styles.rowActions}>
                              <button
                                type="button"
                                className={styles.iconBtn}
                                onClick={() => void onFetchDetail(result.listing_id)}
                              >
                                Detail
                              </button>
                              {result.listing_url ? (
                                <a
                                  className={styles.iconBtn}
                                  href={result.listing_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Open
                                </a>
                              ) : null}
                              <button
                                type="button"
                                className={styles.iconBtn}
                                disabled={!result.listing_url}
                                onClick={() =>
                                  result.listing_url
                                    ? void copyText(result.listing_url).then(() =>
                                        pushToast("Copied listing URL"),
                                      )
                                    : undefined
                                }
                              >
                                Copy URL
                              </button>
                              <button
                                type="button"
                                className={styles.iconBtn}
                                onClick={() =>
                                  void copyText(String(result.listing_id)).then(() =>
                                    pushToast("Copied listing id"),
                                  )
                                }
                              >
                                Copy id
                              </button>
                            </div>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        <section className={styles.detailPanel}>
          <h2 className={styles.sectionTitle}>Listing detail</h2>
          {activeListingId === null ? (
            <p className={styles.mutedLabel}>Select a row and open detail to inspect the full API payload.</p>
          ) : null}
          {detailLoading ? (
            <div className={styles.skeleton} style={{ width: "100%" }} aria-hidden />
          ) : null}
          {detailError ? <p className={styles.error}>{detailError}</p> : null}
          {activeDetail ? (
            <>
              <div className={styles.urlRow}>
                <span className={styles.mutedLabel}>listing_url:</span>
                {listingUrlStr ? (
                  <>
                    <a href={listingUrlStr} target="_blank" rel="noopener noreferrer">
                      Open listing
                    </a>
                    <button
                      type="button"
                      className={styles.iconBtn}
                      onClick={() => void copyText(listingUrlStr).then(() => pushToast("Copied listing URL"))}
                    >
                      Copy URL
                    </button>
                  </>
                ) : (
                  <span className={styles.chipWarn}>Unavailable</span>
                )}
              </div>
              <div className={styles.detailSections}>
                <div className={styles.detailBlock}>
                  <h4>listing_core</h4>
                  <JsonTree data={activeDetail.listing_core} />
                </div>
                <div className={styles.detailBlock}>
                  <h4>score_summary</h4>
                  <JsonTree data={activeDetail.score_summary} />
                </div>
                <div className={styles.detailBlock}>
                  <h4>diagnostics</h4>
                  <JsonTree data={activeDetail.diagnostics} />
                </div>
              </div>
            </>
          ) : null}
        </section>
      </section>
    </main>
  );
}
