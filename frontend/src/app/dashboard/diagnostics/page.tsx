"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonTree } from "../components/JsonTree";
import styles from "../dashboard.module.css";
import { API_BASE, fetchJson, formatThrownApiError } from "../lib/api";
import type { DiagnosticsSummary } from "../lib/types";

export default function DiagnosticsPage() {
  const [data, setData] = useState<DiagnosticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setError(null);
      try {
        const res = await fetchJson<DiagnosticsSummary>("/api/v1/diagnostics/summary");
        setData(res);
      } catch (e) {
        setError(formatThrownApiError(e));
      }
    };
    void load();
  }, []);

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div>
          <p className={styles.envBadge}>Operators</p>
          <h1 className={styles.title}>Diagnostics</h1>
          <p className={styles.subTitle}>API snapshot, ingestion mix, and latest validation summaries.</p>
        </div>
        <Link className={styles.secondaryButton} href="/dashboard/runs">
          Open runs
        </Link>
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

      {!data && !error ? (
        <p className={styles.mutedLabel}>Loading…</p>
      ) : error ? (
        <p className={styles.mutedLabel}>Fix the error above to load diagnostics.</p>
      ) : data !== null ? (
        <>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>API status</h2>
            <p>
              Status: <span className={styles.chip}>{data.api_status}</span>
            </p>
            <p className={styles.mutedLabel}>
              Total ranking runs: <strong>{data.total_ranking_runs}</strong> · listings:{" "}
              <strong>{data.total_listings}</strong>
            </p>
          </section>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Ingestion jobs by status</h2>
            <JsonTree data={data.ingestion_jobs_by_status} />
          </section>
          <section className={styles.card}>
            <h2 className={styles.sectionTitle}>Latest dataset validations</h2>
            <JsonTree data={data.latest_dataset_validations} />
          </section>
        </>
      ) : null}
    </main>
  );
}
