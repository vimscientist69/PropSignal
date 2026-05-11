"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonTree } from "../components/JsonTree";
import styles from "../dashboard.module.css";
import { fetchJson } from "../lib/api";
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
        setError((e as Error).message);
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

      {error ? <p className={styles.error}>{error}</p> : null}

      {!data ? (
        <p className={styles.mutedLabel}>Loading…</p>
      ) : (
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
      )}
    </main>
  );
}
