"use client";

import { useEffect, useState } from "react";

import styles from "../dashboard.module.css";
import { API_BASE, fetchJson, formatThrownApiError, sourcesQuery } from "../lib/api";
import type { SourceSummary } from "../lib/types";
import { JsonTree } from "../components/JsonTree";

export default function SourcesPage() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<SourceSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SourceSummary | null>(null);

  useEffect(() => {
    const load = async () => {
      setError(null);
      try {
        const data = await fetchJson<SourceSummary[]>(sourcesQuery(status || undefined, q || undefined));
        setRows(data);
      } catch (e) {
        setError(formatThrownApiError(e));
      }
    };
    void load();
  }, [status, q]);

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div>
          <p className={styles.envBadge}>Dataset sources</p>
          <h1 className={styles.title}>Source Library</h1>
          <p className={styles.subTitle}>Inspect ingestion jobs, validation summaries, and freshness.</p>
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
        <div className={styles.rowBetween}>
          <h2 className={styles.sectionTitle}>Filters</h2>
        </div>
        <div className={styles.inline}>
          <input placeholder="Status equals…" value={status} onChange={(e) => setStatus(e.target.value)} />
          <input placeholder="Search path or source token" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </section>

      <section className={styles.bottomGrid}>
        <section className={styles.resultsPanel}>
          <h2 className={styles.sectionTitle}>Sources</h2>
          {error ? (
            <p className={styles.mutedLabel}>Fix the error above, or adjust filters.</p>
          ) : rows.length === 0 ? (
            <p className={styles.mutedLabel}>No sources match filters.</p>
          ) : (
            <div className={styles.dataTableWrap}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Job</th>
                    <th>Path</th>
                    <th>Status</th>
                    <th>Valid</th>
                    <th>Invalid</th>
                    <th>Finished</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.source}
                      className={selected?.source === r.source ? styles.selectedRow : undefined}
                    >
                      <td>
                        <button type="button" className={styles.iconBtn} onClick={() => setSelected(r)}>
                          {r.source}
                        </button>
                      </td>
                      <td>{r.job_id}</td>
                      <td>{r.input_path}</td>
                      <td>
                        <span className={styles.chip}>{r.status}</span>
                      </td>
                      <td>{r.records_valid}</td>
                      <td>{r.records_invalid}</td>
                      <td>{r.finished_at ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <section className={styles.detailPanel}>
          <h2 className={styles.sectionTitle}>Source detail</h2>
          {!selected ? (
            <p className={styles.mutedLabel}>Select a row to inspect validation summary.</p>
          ) : (
            <>
              <p className={styles.mutedLabel}>
                Validation status: <strong>{selected.validation_status ?? "n/a"}</strong>
              </p>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.iconBtn}
                  onClick={() => void navigator.clipboard.writeText(selected.source)}
                >
                  Copy source token
                </button>
              </div>
              <div className={styles.detailBlock}>
                <h4>validation_summary</h4>
                <JsonTree data={selected.validation_summary ?? {}} />
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}
