"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { JsonTree } from "../../components/JsonTree";
import styles from "../../dashboard.module.css";
import { API_BASE, fetchJson } from "../../lib/api";
import type { RunDetailResponse } from "../../lib/types";

import { RunListingDetail } from "./RunListingDetail";

export default function RunDetailPage() {
  const params = useParams();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const [run, setRun] = useState<RunDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listingId, setListingId] = useState<number | null>(null);

  useEffect(() => {
    if (!runId) {
      return;
    }
    const load = async () => {
      setError(null);
      try {
        const res = await fetchJson<RunDetailResponse>(`/api/v1/runs/${runId}`);
        setRun(res);
      } catch (e) {
        setError((e as Error).message);
      }
    };
    void load();
  }, [runId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset row selection when run route changes
    setListingId(null);
  }, [runId]);

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div>
          <p className={styles.envBadge}>Run detail</p>
          <h1 className={styles.title}>{runId || "…"}</h1>
          <p className={styles.subTitle}>Request snapshot, persisted results, and listing drill-down.</p>
        </div>
        <div className={styles.exportGrid} style={{ maxWidth: "520px" }}>
          <a
            className={styles.secondaryButton}
            href={`${API_BASE}/api/v1/runs/${runId}/export?format=json`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Export JSON
          </a>
          <a
            className={styles.secondaryButton}
            href={`${API_BASE}/api/v1/runs/${runId}/export?format=json&listing_detail=true`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Export JSON (full detail)
          </a>
          <a
            className={styles.secondaryButton}
            href={`${API_BASE}/api/v1/runs/${runId}/export?format=csv`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Export CSV
          </a>
          <a
            className={styles.secondaryButton}
            href={`${API_BASE}/api/v1/runs/${runId}/export?format=csv&listing_detail=true`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Export CSV (full detail)
          </a>
        </div>
      </header>

      {error ? (
        <div role="alert" className={styles.errorBanner}>
          <strong>Request failed.</strong> {error}{" "}
          <span style={{ fontWeight: 400, opacity: 0.9 }}>
            (API: <kbd>{API_BASE}</kbd>)
          </span>
        </div>
      ) : null}

      {!run && !error ? (
        <p className={styles.mutedLabel}>Loading…</p>
      ) : error ? (
        <p className={styles.mutedLabel}>Fix the error above to load this run.</p>
      ) : run !== null ? (
        <>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Snapshot</h2>
            <p className={styles.metaGrid}>
              Created {run.created_at} · fingerprint <code>{run.query_fingerprint}</code>
            </p>
            <div className={styles.detailBlock}>
              <h4>request_snapshot</h4>
              <JsonTree data={run.request_snapshot} />
            </div>
            <div className={styles.detailBlock}>
              <h4>result_window</h4>
              <JsonTree data={run.result_window} />
            </div>
          </section>

          <section className={styles.bottomGrid}>
            <section className={styles.resultsPanel}>
              <h2 className={styles.sectionTitle}>Results in this run</h2>
              <div className={styles.dataTableWrap}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Score</th>
                      <th>Conf</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.results.map((r) => (
                      <tr key={r.listing_id} className={listingId === r.listing_id ? styles.selectedRow : undefined}>
                        <td>{r.listing_id}</td>
                        <td>{r.score.toFixed(4)}</td>
                        <td>{r.confidence.toFixed(2)}</td>
                        <td>
                          <button type="button" className={styles.iconBtn} onClick={() => setListingId(r.listing_id)}>
                            Load detail
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <section className={styles.detailPanel}>
              <h2 className={styles.sectionTitle}>Listing detail</h2>
              {listingId === null ? (
                <p className={styles.mutedLabel}>Choose “Load detail” for a row.</p>
              ) : (
                <RunListingDetail key={`${runId}-${listingId}`} runId={runId} listingId={listingId} />
              )}
            </section>
          </section>
        </>
      ) : null}
    </main>
  );
}
