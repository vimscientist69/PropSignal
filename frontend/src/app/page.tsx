"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import styles from "./page.module.css";

type ErrorField = {
  field: string;
  reason: string;
};

type ErrorResponse = {
  code: string;
  message: string;
  field_errors: ErrorField[];
  request_id: string;
};

type SourceSummary = {
  source: string;
  job_id: number;
  input_path: string;
  status: string;
  records_total: number;
  records_valid: number;
  records_invalid: number;
  started_at: string | null;
  finished_at: string | null;
  validation_status: string | null;
  validation_summary: Record<string, unknown> | null;
};

type ProfileSummary = {
  preset: string;
  label: string;
  description: string;
};

type ProfileDetail = {
  preset: string;
  profile_id: string;
  profile_version: string;
  default_weights: Record<string, number>;
  enabled_signals: string[];
  safe_override_bounds: Record<string, { min: number; max: number }>;
};

type RankingResult = {
  listing_id: number;
  score: number;
  deal_reason: string;
  confidence: number;
  summary: Record<string, unknown>;
  detail_ref: string;
};

type RankingResponse = {
  run_id: string;
  resolved_profile: {
    profile_id: string;
    profile_version: string;
  };
  dataset_context: {
    selected_sources: string[];
    records_considered: number;
    last_ingested_at: string | null;
    last_scored_at: string | null;
    model_version: string | null;
    profile_version: string | null;
  };
  results: RankingResult[];
  pagination?: {
    mode: "pagination";
    page: number;
    page_size: number;
    total_count: number;
  };
  top_n?: {
    mode: "top_n";
    top_n_requested: number;
    top_n_returned: number;
  };
};

type ListingDetail = {
  listing_core: Record<string, unknown>;
  score_summary: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let payload: ErrorResponse | null = null;
    try {
      payload = (await response.json()) as ErrorResponse;
    } catch {
      payload = null;
    }
    const message = payload?.message ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export default function Home() {
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
  const [loading, setLoading] = useState(false);
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
      } catch (loadError) {
        setError((loadError as Error).message);
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

  const setOverrideValue = (signal: string, next: string) => {
    setOverrides((current) => ({ ...current, [signal]: next }));
  };

  const resetOverrides = () => setOverrides({});

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
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
        filters: {
          province: province || undefined,
          city: city || undefined,
          suburb: suburb || undefined,
          price_min: priceMin ? Number(priceMin) : undefined,
          price_max: priceMax ? Number(priceMax) : undefined,
          property_type: propertyType || undefined,
          bedrooms_min: bedroomsMin ? Number(bedroomsMin) : undefined,
          bathrooms_min: bathroomsMin ? Number(bathroomsMin) : undefined,
          confidence_min: confidenceMin ? Number(confidenceMin) : undefined,
        },
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
    try {
      const detail = await fetchJson<ListingDetail>(
        `/api/v1/rankings/${ranking.run_id}/listings/${listingId}`,
      );
      setActiveDetail(detail);
    } catch (detailError) {
      setError((detailError as Error).message);
    }
  };

  return (
    <div className={styles.page}>
      <aside className={styles.sidebarShell}>
        <div className={styles.brand}>PropSignal</div>
        <p className={styles.brandSub}>Scoring Control Center</p>
        <nav className={styles.navStack}>
          <span className={styles.navActive}>Control Panel</span>
          <span className={styles.navItem}>Source Library</span>
          <span className={styles.navItem}>Runs</span>
          <span className={styles.navItem}>Diagnostics</span>
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.topHeader}>
          <div>
            <p className={styles.envBadge}>Live ranking environment</p>
            <h1 className={styles.title}>Dashboard Control Center</h1>
            <p className={styles.subTitle}>
              Configure targets, tune scoring strategy, and inspect high-confidence opportunities.
            </p>
          </div>
          <div className={styles.topStats}>
            <div className={styles.statTile}>
              <span>Sources</span>
              <strong>{selectedSources.length}</strong>
            </div>
            <div className={styles.statTile}>
              <span>Records</span>
              <strong>{ranking?.dataset_context.records_considered ?? "--"}</strong>
            </div>
          </div>
        </header>

        <section className={styles.mainGrid}>
          <form onSubmit={onSubmit} className={styles.controlPanel}>
            <div className={styles.rowBetween}>
              <h2 className={styles.sectionTitle}>Main Control Panel</h2>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.ghostButton}
                  onClick={() => setSelectedSources(sources.map((s) => s.source))}
                >
                  select all
                </button>
                <button type="button" className={styles.ghostButton} onClick={() => setSelectedSources([])}>
                  clear all
                </button>
              </div>
            </div>
            <p className={styles.sectionHint}>Choose source datasets, filtering constraints, and strategy.</p>

            <div className={styles.sourceList}>
              {sources.map((source) => (
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
              ))}
            </div>

            <div className={styles.statusGrid}>
              {selectedSourceRows.map((row) => (
                <article key={`status-${row.source}`} className={styles.statusCell}>
                  <strong>{row.source}</strong>
                  <p>Status: {row.status}</p>
                  <p>Validation: {row.validation_status ?? "n/a"}</p>
                </article>
              ))}
            </div>

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

            <h3 className={styles.blockTitle}>Strategy Profile</h3>
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
              Reset overrides
            </button>

            <h3 className={styles.blockTitle}>Result Window</h3>
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
            <button type="submit" className={styles.primaryButton} disabled={loading}>
              {loading ? "Running..." : "Run ranking"}
            </button>
          </form>

          <section className={styles.sidePanel}>
            <h2 className={styles.sectionTitle}>Run Context</h2>
            <p className={styles.sectionHint}>Snapshot of the latest ranking execution metadata.</p>
            {ranking ? (
              <div className={styles.metaGrid}>
                <p>run_id: {ranking.run_id}</p>
                <p>profile_id: {ranking.resolved_profile.profile_id}</p>
                <p>profile_version: {ranking.resolved_profile.profile_version}</p>
                <p>model_version: {ranking.dataset_context.model_version ?? "n/a"}</p>
                <p>last_ingested_at: {ranking.dataset_context.last_ingested_at ?? "n/a"}</p>
                <p>last_scored_at: {ranking.dataset_context.last_scored_at ?? "n/a"}</p>
              </div>
            ) : (
              <p className={styles.mutedLabel}>Run ranking to populate context details.</p>
            )}
          </section>
        </section>

        {error ? <p className={styles.error}>{error}</p> : null}

        <section className={styles.bottomGrid}>
          <section className={styles.resultsPanel}>
            <div className={styles.rowBetween}>
              <h2 className={styles.sectionTitle}>Latest Ranked Listings</h2>
              <span className={styles.mutedLabel}>{ranking?.results.length ?? 0} rows</span>
            </div>
            {!ranking ? (
              <p className={styles.mutedLabel}>Run ranking to display results.</p>
            ) : ranking.results.length === 0 ? (
              <p className={styles.mutedLabel}>No results found.</p>
            ) : (
              <div className={styles.results}>
                {ranking.results.map((result) => (
                  <button
                    key={result.listing_id}
                    type="button"
                    className={styles.resultRow}
                    onClick={() => void onFetchDetail(result.listing_id)}
                  >
                    <span>#{result.listing_id}</span>
                    <span>{result.score.toFixed(4)}</span>
                    <span>{result.confidence.toFixed(2)}</span>
                    <span>{result.deal_reason}</span>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className={styles.detailPanel}>
            <h2 className={styles.sectionTitle}>Listing Detail</h2>
            {activeListingId === null ? (
              <p className={styles.mutedLabel}>Select a ranked listing to inspect diagnostics.</p>
            ) : null}
            {activeListingId !== null && !activeDetail ? (
              <p className={styles.mutedLabel}>Loading listing #{activeListingId}...</p>
            ) : null}
            {activeDetail ? <pre className={styles.detailJson}>{JSON.stringify(activeDetail, null, 2)}</pre> : null}
          </section>
        </section>
      </main>
    </div>
  );
}
