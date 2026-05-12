"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import styles from "../dashboard.module.css";
import { API_BASE, fetchJson, formatThrownApiError } from "../lib/api";
import type { RunSummaryItem, RunsListResponse } from "../lib/types";

export default function RunsPage() {
  const [data, setData] = useState<RunsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [baseline, setBaseline] = useState("");
  const [candidate, setCandidate] = useState("");

  useEffect(() => {
    const load = async () => {
      setError(null);
      try {
        const res = await fetchJson<RunsListResponse>("/api/v1/runs?page=1&page_size=50");
        setData(res);
        if (res.items.length > 0) {
          setBaseline((prev) => prev || res.items[0].run_id);
        }
        if (res.items.length > 1) {
          setCandidate((prev) => prev || res.items[1].run_id);
        }
      } catch (e) {
        setError(formatThrownApiError(e));
      }
    };
    void load();
  }, []);

  const items = data?.items ?? [];

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div>
          <p className={styles.envBadge}>History</p>
          <h1 className={styles.title}>Runs</h1>
          <p className={styles.subTitle}>Browse persisted ranking runs and reopen exports or detail context.</p>
        </div>
      </header>

      {error ? (
        <div role="alert" className={styles.errorBanner}>
          <p className={styles.errorBannerTitle}>Request failed</p>
          <pre className={styles.errorMultiline}>{error}</pre>
          <p className={styles.mutedLabel} style={{ marginTop: "0.45rem", marginBottom: 0 }}>
            API: <kbd>{API_BASE}</kbd>
          </p>
        </div>
      ) : null}

      <section className={styles.card}>
        <h2 className={styles.sectionTitle}>Compare mode</h2>
        <p className={styles.sectionHint}>
          Select a baseline and candidate run for side-by-side review (diff tooling comes later).
        </p>
        <div className={styles.inline}>
          <label className={styles.radio}>
            Baseline
            <select value={baseline} onChange={(e) => setBaseline(e.target.value)}>
              {items.map((r: RunSummaryItem) => (
                <option key={`b-${r.run_id}`} value={r.run_id}>
                  {r.run_id}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.radio}>
            Candidate
            <select value={candidate} onChange={(e) => setCandidate(e.target.value)}>
              {items.map((r: RunSummaryItem) => (
                <option key={`c-${r.run_id}`} value={r.run_id}>
                  {r.run_id}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className={styles.mutedLabel}>
          Selected: <code>{baseline || "—"}</code> vs <code>{candidate || "—"}</code>
        </p>
        <div className={styles.actions}>
          {baseline ? (
            <Link className={styles.secondaryButton} href={`/dashboard/runs/${baseline}`}>
              Open baseline
            </Link>
          ) : null}
          {candidate ? (
            <Link className={styles.secondaryButton} href={`/dashboard/runs/${candidate}`}>
              Open candidate
            </Link>
          ) : null}
        </div>
      </section>

      <section className={styles.resultsPanel}>
        <h2 className={styles.sectionTitle}>Run history</h2>
        {!data && !error ? (
          <p className={styles.mutedLabel}>Loading…</p>
        ) : error ? (
          <p className={styles.mutedLabel}>Fix the error above to load run history.</p>
        ) : data !== null && data.items.length === 0 ? (
          <p className={styles.mutedLabel}>No runs yet — execute a ranking from the Control Panel.</p>
        ) : data !== null ? (
          <div className={styles.dataTableWrap}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>run_id</th>
                  <th>Created</th>
                  <th>Preset</th>
                  <th>Profile</th>
                  <th>Sources</th>
                  <th>Considered</th>
                  <th>Results</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.run_id}>
                    <td>
                      <code>{r.run_id}</code>
                    </td>
                    <td>{r.created_at}</td>
                    <td>{r.strategy_preset}</td>
                    <td>{r.profile_id}</td>
                    <td>{r.source_count}</td>
                    <td>{r.records_considered}</td>
                    <td>{r.result_count}</td>
                    <td>
                      <div className={styles.rowActions}>
                        <Link className={styles.iconBtn} href={`/dashboard/runs/${r.run_id}`}>
                          View
                        </Link>
                        <button
                          type="button"
                          className={styles.iconBtn}
                          onClick={() => void navigator.clipboard.writeText(r.run_id)}
                        >
                          Copy id
                        </button>
                        <a
                          className={styles.iconBtn}
                          href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/runs/${r.run_id}/export?format=json`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Export JSON
                        </a>
                        <a
                          className={styles.iconBtn}
                          href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/runs/${r.run_id}/export?format=json&listing_detail=true`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          JSON + detail
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
