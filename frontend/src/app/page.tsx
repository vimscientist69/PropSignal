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
      <main className={styles.main}>
        <h1>PropSignal Dashboard</h1>
        <p>Run end-to-end ranking against backend APIs with reproducible run context.</p>
        <form onSubmit={onSubmit} className={styles.form}>
          <section className={styles.card}>
            <div className={styles.rowBetween}>
              <h2>Dataset Sources</h2>
              <div className={styles.actions}>
                <button type="button" onClick={() => setSelectedSources(sources.map((s) => s.source))}>
                  select_all
                </button>
                <button type="button" onClick={() => setSelectedSources([])}>
                  clear_all
                </button>
              </div>
            </div>
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
                  <span>
                    {source.source} ({source.status}, valid {source.records_valid}/{source.records_total})
                  </span>
                </label>
              ))}
            </div>
            <div className={styles.statusGrid}>
              {selectedSourceRows.map((row) => (
                <div key={`status-${row.source}`} className={styles.statusCell}>
                  <strong>{row.source}</strong>
                  <p>job_status: {row.status}</p>
                  <p>validation: {row.validation_status ?? "n/a"}</p>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.card}>
            <h2>Filters</h2>
            <div className={styles.grid}>
              <input placeholder="province" value={province} onChange={(e) => setProvince(e.target.value)} />
              <input placeholder="city" value={city} onChange={(e) => setCity(e.target.value)} />
              <input placeholder="suburb" value={suburb} onChange={(e) => setSuburb(e.target.value)} />
              <input placeholder="price_min" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} />
              <input placeholder="price_max" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} />
              <input
                placeholder="property_type"
                value={propertyType}
                onChange={(e) => setPropertyType(e.target.value)}
              />
              <input
                placeholder="bedrooms_min"
                value={bedroomsMin}
                onChange={(e) => setBedroomsMin(e.target.value)}
              />
              <input
                placeholder="bathrooms_min"
                value={bathroomsMin}
                onChange={(e) => setBathroomsMin(e.target.value)}
              />
              <input
                placeholder="confidence_min"
                value={confidenceMin}
                onChange={(e) => setConfidenceMin(e.target.value)}
              />
            </div>
          </section>

          <section className={styles.card}>
            <h2>Strategy</h2>
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
            <button type="button" onClick={resetOverrides}>
              reset_to_default
            </button>
          </section>

          <section className={styles.card}>
            <h2>Result Window</h2>
            <div className={styles.inline}>
              <label>
                <input
                  type="radio"
                  checked={windowMode === "top_n"}
                  onChange={() => setWindowMode("top_n")}
                />
                top_n
              </label>
              <label>
                <input
                  type="radio"
                  checked={windowMode === "pagination"}
                  onChange={() => setWindowMode("pagination")}
                />
                pagination
              </label>
            </div>
            {windowMode === "top_n" ? (
              <input value={topN} onChange={(e) => setTopN(e.target.value)} placeholder="top_n" />
            ) : (
              <div className={styles.inline}>
                <input value={page} onChange={(e) => setPage(e.target.value)} placeholder="page" />
                <input value={pageSize} onChange={(e) => setPageSize(e.target.value)} placeholder="page_size" />
              </div>
            )}
          </section>

          <button type="submit" disabled={loading}>
            {loading ? "Running..." : "Run Ranking"}
          </button>
        </form>

        {error ? <p className={styles.error}>{error}</p> : null}

        {ranking ? (
          <>
            <section className={styles.card}>
              <h2>Run Metadata</h2>
              <p>run_id: {ranking.run_id}</p>
              <p>profile_id: {ranking.resolved_profile.profile_id}</p>
              <p>profile_version: {ranking.resolved_profile.profile_version}</p>
              <p>model_version: {ranking.dataset_context.model_version ?? "n/a"}</p>
              <p>last_ingested_at: {ranking.dataset_context.last_ingested_at ?? "n/a"}</p>
              <p>last_scored_at: {ranking.dataset_context.last_scored_at ?? "n/a"}</p>
            </section>

            <section className={styles.card}>
              <h2>Ranked Results</h2>
              {ranking.results.length === 0 ? <p>No results.</p> : null}
              <div className={styles.results}>
                {ranking.results.map((result) => (
                  <button
                    key={result.listing_id}
                    type="button"
                    className={styles.resultRow}
                    onClick={() => void onFetchDetail(result.listing_id)}
                  >
                    <span>#{result.listing_id}</span>
                    <span>score {result.score.toFixed(4)}</span>
                    <span>confidence {result.confidence.toFixed(2)}</span>
                    <span>{result.deal_reason}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className={styles.card}>
              <h2>Listing Detail</h2>
              {activeListingId === null ? <p>Select a ranked listing.</p> : null}
              {activeListingId !== null && !activeDetail ? <p>Loading listing #{activeListingId}...</p> : null}
              {activeDetail ? (
                <pre className={styles.detailJson}>{JSON.stringify(activeDetail, null, 2)}</pre>
              ) : null}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
