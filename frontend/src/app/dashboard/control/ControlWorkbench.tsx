"use client";

import { Play } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LiveBadge } from "@/components/dashboard/live-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { JsonTree } from "../components/JsonTree";
import { useToast } from "../components/DashboardChrome";
import { checkboxClass, styles } from "./controlWorkbenchStyles";
import { API_BASE, fetchJson, fetchListingDetailsForRun, formatThrownApiError } from "../lib/api";
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
  const errorBannerRef = useRef<HTMLDivElement>(null);
  const scrollToRankingErrorRef = useRef(false);

  const reportRankingError = useCallback(
    (message: string) => {
      setError(message);
      scrollToRankingErrorRef.current = true;
      pushToast("Ranking failed — full details are in the alert at the top of the page.", "error");
    },
    [pushToast],
  );

  useEffect(() => {
    setColumns(loadColumnPrefs());
  }, []);

  useEffect(() => {
    if (!scrollToRankingErrorRef.current || !error) {
      return;
    }
    scrollToRankingErrorRef.current = false;
    errorBannerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [error]);

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
        setLoadError(formatThrownApiError(loadError_));
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
        setError(formatThrownApiError(presetError));
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
      reportRankingError("Select at least one dataset source.");
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
      reportRankingError(formatThrownApiError(submitError));
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
      setDetailError(formatThrownApiError(detailErr));
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
      setError(formatThrownApiError(e));
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
      setError(formatThrownApiError(e));
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
      setError(formatThrownApiError(e));
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
        <div className="space-y-2">
          <LiveBadge />
          <div className="space-y-1">
            <h1 className={styles.title}>Dashboard Control Center</h1>
            <p className={styles.subTitle}>
              Configure sources, filters, and strategy — then inspect ranked listings and exports.
            </p>
          </div>
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
        <div ref={errorBannerRef} role="alert" className={styles.errorBanner}>
          {loadError ? (
            <div>
              <p className={styles.errorBannerTitle}>Cannot load dashboard data</p>
              <pre className={styles.errorMultiline}>{loadError}</pre>
              <p className={styles.mutedLabel} style={{ marginTop: "0.5rem", marginBottom: 0 }}>
                API base: <kbd>{API_BASE}</kbd>
              </p>
            </div>
          ) : null}
          {error ? (
            <div>
              <p className={styles.errorBannerTitle}>Request failed</p>
              <pre className={styles.errorMultiline}>{error}</pre>
            </div>
          ) : null}
        </div>
      ) : null}

      <section className={styles.mainGrid}>
        <form onSubmit={onSubmit} className={cn(styles.controlPanel, "flex flex-col")}>
          <div className="space-y-3 border-b border-slate-800/80 px-4 pb-3 pt-4">
          <div className={styles.rowBetween}>
            <h2 className={styles.sectionTitle}>Main Control Panel</h2>
            <div className={styles.actions}>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSelectedSources(sources.map((s) => s.source))}
              >
                Select all
                </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setSelectedSources([])}>
                Clear
                </Button>
            </div>
          </div>
          <p className={styles.sectionHint}>
            Configure sources, filters, and strategy — then run ranking.
          </p>
          <div className="mb-1 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-500">
              <span>Telemetry — {loading ? "Running" : ranking ? "Complete" : "Idle"}</span>
              {loading ? <span className="font-mono text-indigo-400">processing</span> : null}
            </div>
            <div className="h-2 overflow-hidden rounded-full border border-slate-800/70 bg-slate-900">
              <div
                className={cn(
                  "h-full rounded-full bg-gradient-to-r from-indigo-500 via-sky-400 to-emerald-400 transition-all duration-500",
                  loading ? "w-2/3 animate-pulse" : ranking ? "w-full" : "w-0",
                )}
              />
            </div>
          </div>
          </div>
          <div className="space-y-4 px-4 py-4">
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
                      className={cn(checkboxClass, "shrink-0")}
                      checked={selectedSources.includes(source.source)}
                      onChange={(event) =>
                        setSelectedSources((current) =>
                          event.target.checked
                            ? [...current, source.source]
                            : current.filter((item) => item !== source.source),
                        )
                      }
                    />
                    <div className={styles.sourceItemBody}>
                      <span className={styles.sourceItemTitle} title={source.source}>
                        {source.source}
                      </span>
                      <span
                        className={styles.sourceItemMeta}
                        title={`${source.status} · ${source.records_valid}/${source.records_total} valid`}
                      >
                        {source.status} · {source.records_valid}/{source.records_total} valid
                      </span>
                    </div>
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
              <Input placeholder="Province" value={province} onChange={(e) => setProvince(e.target.value)} />
              <Input placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
              <Input placeholder="Suburb" value={suburb} onChange={(e) => setSuburb(e.target.value)} />
              <Input placeholder="Price min" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
              <Input placeholder="Price max" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
              <Input
                placeholder="Property type"
                value={propertyType}
                onChange={(e) => setPropertyType(e.target.value)}
              />
              <Input
                placeholder="Bedrooms min"
                value={bedroomsMin}
                onChange={(e) => setBedroomsMin(e.target.value)}
              />
              <Input
                placeholder="Bathrooms min"
                value={bathroomsMin}
                onChange={(e) => setBathroomsMin(e.target.value)}
              />
              <Input
                placeholder="Confidence min"
                value={confidenceMin}
                onChange={(e) => setConfidenceMin(e.target.value)}
              />
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Strategy profile</h3>
            <Select value={selectedPreset} onChange={(e) => setSelectedPreset(e.target.value)}>
              {profiles.map((profile) => (
                <option key={profile.preset} value={profile.preset}>
                  {profile.label}
                </option>
              ))}
            </Select>
            <div className={styles.overrideGrid}>
              {profileDetail?.enabled_signals.map((signal) => {
                const bounds = profileDetail.safe_override_bounds[signal];
                return (
                  <label key={signal} className={styles.overrideItem}>
                    <span>
                      {signal} [{bounds.min.toFixed(3)}, {bounds.max.toFixed(3)}]
                    </span>
                    <Input
                      value={overrides[signal] ?? ""}
                      onChange={(e) => setOverrideValue(signal, e.target.value)}
                      placeholder={String(profileDetail.default_weights[signal] ?? "")}
                    />
                  </label>
                );
              })}
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={resetOverrides}>
              Reset overrides to preset
                </Button>
          </div>

          <div className={styles.card}>
            <h3 className={styles.blockTitle}>Result window</h3>
            <div className={styles.inline}>
              <label className={styles.radio}>
                <input
                  type="radio"
                  className="accent-indigo-500"
                  checked={windowMode === "top_n"}
                  onChange={() => setWindowMode("top_n")}
                />
                Top N
              </label>
              <label className={styles.radio}>
                <input
                  type="radio"
                  className="accent-indigo-500"
                  checked={windowMode === "pagination"}
                  onChange={() => setWindowMode("pagination")}
                />
                Pagination
              </label>
            </div>
            {windowMode === "top_n" ? (
              <Input value={topN} onChange={(e) => setTopN(e.target.value)} placeholder="Top N" />
            ) : (
              <div className={styles.inline}>
                <Input value={page} onChange={(e) => setPage(e.target.value)} placeholder="Page" />
                <Input value={pageSize} onChange={(e) => setPageSize(e.target.value)} placeholder="Page size" />
              </div>
            )}
          </div>

          <div className={styles.stickyActions}>
            <Button type="submit" variant="primary" disabled={loading} className="w-full sm:w-auto">
              <Play className="h-3.5 w-3.5" aria-hidden />
              {loading ? "Running…" : "Run ranking"}
                </Button>
          </div>
          </div>
        </form>

        <section className={styles.sidePanel}>
          <div className={styles.sidePanelHeader}>
            <h2 className={styles.sectionTitle}>Run metadata</h2>
            <p className={styles.sectionHint}>
              Reproducibility: run id, profile, and dataset freshness.
            </p>
          </div>
          {ranking ? (
            <div className={styles.sidePanelContent}>
            <div className={styles.metaGrid}>
              <div className={styles.metaField}>
                <span className={styles.mutedLabel}>run_id</span>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <code>{ranking.run_id}</code>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-[10px]"
                    onClick={() => void copyText(ranking.run_id).then(() => pushToast("Copied run id"))}
                  >
                    Copy
                  </Button>
                </div>
              </div>
              <div className={styles.metaField}>
                <span className={styles.mutedLabel}>profile_id</span>
                <p className={styles.metaFieldValue} title={ranking.resolved_profile.profile_id}>
                  {ranking.resolved_profile.profile_id}
                </p>
              </div>
              <div className={styles.metaField}>
                <span className={styles.mutedLabel}>profile_version</span>
                <p className={cn(styles.metaFieldValue, "font-normal")}>
                  {ranking.resolved_profile.profile_version}
                </p>
              </div>
              <div className={styles.metaField}>
                <span className={styles.mutedLabel}>model_version</span>
                <p className={cn(styles.metaFieldValue, "font-normal")}>
                  {ranking.dataset_context.model_version ?? "n/a"}
                </p>
              </div>
              <div className={cn(styles.metaField, "md:col-span-2")}>
                <span className={styles.mutedLabel}>last_ingested_at</span>
                <p className="mt-1 break-all font-mono text-[11px]">
                  {ranking.dataset_context.last_ingested_at ?? "n/a"}
                </p>
              </div>
              <div className={cn(styles.metaField, "md:col-span-2")}>
                <span className={styles.mutedLabel}>last_scored_at</span>
                <p className={cn(styles.metaFieldValue, "font-normal")}>
                  {ranking.dataset_context.last_scored_at ?? "n/a"}
                </p>
              </div>
              <div className={styles.exportSection}>
              <p className={styles.sectionHint}>
                Summary rows match the results table. Full-detail exports include listing_core,
                score_summary, and diagnostics.
              </p>
              <div className={styles.exportGroup}>
              <p className={styles.blockTitle}>Summary exports</p>
              <div className={styles.exportStack}>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => exportWindow("csv")}
                >
                  Export window CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => exportWindow("json")}
                >
                  Export window JSON
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => exportShortlistOnly("csv")}
                >
                  Export shortlist CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => exportShortlistOnly("json")}
                >
                  Export shortlist JSON
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("csv", false)}
                >
                  Download full run (server CSV)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("json", false)}
                >
                  Download full run (server JSON)
                </Button>
              </div>
              </div>
              <div className={styles.exportGroup}>
              <p className={styles.blockTitle}>With full listing detail</p>
              <div className={styles.exportStack}>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportWindowWithDetail("csv")}
                >
                  Export window CSV (full detail)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportWindowWithDetail("json")}
                >
                  Export window JSON (full detail)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportShortlistWithDetail("csv")}
                >
                  Export shortlist CSV (full detail)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportShortlistWithDetail("json")}
                >
                  Export shortlist JSON (full detail)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("csv", true)}
                >
                  Download full run — server CSV (full detail)
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className={styles.exportBtn}
                  disabled={exportDetailBusy}
                  onClick={() => void exportServerRun("json", true)}
                >
                  Download full run — server JSON (full detail)
                </Button>
              </div>
              </div>
              </div>
            </div>
            </div>
          ) : (
            <p className={cn(styles.mutedLabel, "mt-4")}>
              Run ranking to populate metadata and export actions.
            </p>
          )}
        </section>
      </section>

      <section className={styles.bottomGrid}>
        <section className={styles.resultsPanel}>
          <div className={styles.rowBetween}>
            <h2 className={styles.sectionTitle}>Latest listings</h2>
            <span className="inline-flex items-center rounded-full border border-slate-800/80 bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
              {ranking?.results.length ?? 0} rows
            </span>
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
                      className={checkboxClass}
                      checked={columns[key] !== false}
                      onChange={(e) => setColumns((c) => ({ ...c, [key]: e.target.checked }))}
                    />
                    {key.replace("_", " ")}
                  </label>
                ))}
              </div>
              <div className={styles.dataTableWrap}>
                <table className={cn(styles.dataTable, styles.listingsDataTable)}>
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
                      {columns.actions ? <th className={styles.tableActionsCol}>Actions</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedResults.map((result) => (
                      <tr
                        key={result.listing_id}
                        className={cn(
                          styles.tableRow,
                          activeListingId === result.listing_id && styles.selectedRow,
                        )}
                      >
                        <td className="font-mono text-[11px] text-slate-400">{result.listing_id}</td>
                        {columns.score ? (
                          <td className="font-mono text-[11px] text-slate-300">{result.score.toFixed(4)}</td>
                        ) : null}
                        {columns.confidence ? <td>{result.confidence.toFixed(2)}</td> : null}
                        {columns.price ? (
                          <td className="font-semibold text-indigo-400">
                            {String(result.summary.price ?? "—")}
                          </td>
                        ) : null}
                        {columns.city ? <td>{String(result.summary.city ?? "—")}</td> : null}
                        {columns.suburb ? <td>{String(result.summary.suburb ?? "—")}</td> : null}
                        {columns.province ? <td>{String(result.province ?? "—")}</td> : null}
                        {columns.property_type ? <td>{String(result.summary.property_type ?? "—")}</td> : null}
                        {columns.bedrooms ? <td>{result.bedrooms ?? "—"}</td> : null}
                        {columns.bathrooms ? <td>{result.bathrooms ?? "—"}</td> : null}
                        {columns.deal_reason ? (
                          <td className={styles.tableCellWrap} title={result.deal_reason}>
                            <span className="line-clamp-2">{result.deal_reason}</span>
                          </td>
                        ) : null}
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
                            <Button
                              type="button"
                              variant="ghost"
                              size="iconSm"
                              aria-pressed={shortlist.has(result.listing_id)}
                              onClick={() => toggleShortlist(result.listing_id)}
                            >
                              {shortlist.has(result.listing_id) ? "★" : "☆"}
                            </Button>
                          </td>
                        ) : null}
                        {columns.actions ? (
                          <td className={styles.tableActionsCol}>
                            <div className={styles.rowActions}>
                              <Button
                                type="button"
                                variant="outline"
                                className={styles.rowActionBtn}
                                onClick={() => void onFetchDetail(result.listing_id)}
                              >
                                Detail
                              </Button>
                              {result.listing_url ? (
                                <Button variant="outline" className={styles.rowActionBtn} asChild>
                                  <a href={result.listing_url} target="_blank" rel="noopener noreferrer">
                                    Open
                                  </a>
                                </Button>
                              ) : null}
                              <Button
                                type="button"
                                variant="outline"
                                className={styles.rowActionBtn}
                                disabled={!result.listing_url}
                                onClick={() =>
                                  result.listing_url
                                    ? void copyText(result.listing_url).then(() =>
                                        pushToast("Copied listing URL"),
                                      )
                                    : undefined
                                }
                              >
                                URL
                              </Button>
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
          {detailError ? (
            <div className={styles.error}>
              <pre className={styles.errorMultiline}>{detailError}</pre>
            </div>
          ) : null}
          {activeDetail ? (
            <>
              <div className={styles.urlRow}>
                <span className={styles.mutedLabel}>listing_url:</span>
                {listingUrlStr ? (
                  <>
                    <a href={listingUrlStr} target="_blank" rel="noopener noreferrer">
                      Open listing
                    </a>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void copyText(listingUrlStr).then(() => pushToast("Copied listing URL"))}
                    >
                      Copy URL
                    </Button>
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
