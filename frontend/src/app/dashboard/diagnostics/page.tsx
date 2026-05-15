"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

import { LiveBadge } from "@/components/dashboard/live-badge";
import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { JsonTree } from "../components/JsonTree";
import { styles } from "../dashboardPageStyles";
import { API_BASE, fetchJson, formatThrownApiError } from "../lib/api";
import type { DiagnosticsSummary } from "../lib/types";

function isHealthyStatus(status: string): boolean {
  const normalized = status.toLowerCase();
  return normalized === "ok" || normalized === "healthy" || normalized === "up";
}

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
        <div className="space-y-2">
          <LiveBadge label="Operators" />
          <h1 className={styles.title}>Diagnostics</h1>
          <p className={styles.subTitle}>API snapshot, ingestion mix, and latest validation summaries.</p>
        </div>
        <Button variant="outline" size="sm" className="gap-1.5 shrink-0" asChild>
          <Link href="/dashboard/runs">
            Open runs
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </Button>
      </header>

      {error ? (
        <div role="alert" className={styles.errorBanner}>
          <p className={styles.errorBannerTitle}>Request failed</p>
          <pre className={styles.errorMultiline}>{error}</pre>
          <p className={cn(styles.mutedLabel, "mt-2")}>
            API: <kbd className="font-mono text-[11px] text-slate-400">{API_BASE}</kbd>
          </p>
        </div>
      ) : null}

      {!data && !error ? (
        <p className={styles.mutedLabel}>Loading…</p>
      ) : error ? (
        <p className={styles.mutedLabel}>Fix the error above to load diagnostics.</p>
      ) : data !== null ? (
        <div className="space-y-4 md:space-y-6">
          <SectionCard title="API status" subtitle="Live snapshot from the diagnostics summary endpoint.">
            <div className={styles.compareSummary}>
              <div className={styles.statTile}>
                <span>API status</span>
                <strong>
                  <span
                    className={cn(
                      styles.chip,
                      isHealthyStatus(data.api_status) &&
                        "border-emerald-500/40 bg-emerald-500/20 text-emerald-300 shadow-[0_0_8px_rgba(74,222,128,0.25)]",
                    )}
                  >
                    {data.api_status}
                  </span>
                </strong>
              </div>
              <div className={styles.statTile}>
                <span>Ranking runs</span>
                <strong className={styles.cellHighlight}>{data.total_ranking_runs}</strong>
              </div>
              <div className={styles.statTile}>
                <span>Listings</span>
                <strong className={styles.cellHighlight}>{data.total_listings}</strong>
              </div>
            </div>
          </SectionCard>

          <section className="grid min-w-0 gap-4 lg:grid-cols-2">
            <SectionCard
              title="Ingestion jobs by status"
              subtitle="Counts grouped by ingestion job state."
              light
            >
              <div className={styles.detailBlock}>
                <JsonTree data={data.ingestion_jobs_by_status} />
              </div>
            </SectionCard>

            <SectionCard
              title="Latest dataset validations"
              subtitle="Most recent validation summaries per dataset source."
              light
            >
              <div className={cn(styles.detailBlock, "custom-scroll max-h-[min(48vh,440px)] overflow-auto")}>
                <JsonTree data={data.latest_dataset_validations} />
              </div>
            </SectionCard>
          </section>
        </div>
      ) : null}
    </main>
  );
}
