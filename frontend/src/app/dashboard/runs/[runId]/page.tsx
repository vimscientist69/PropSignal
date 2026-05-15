"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { LiveBadge } from "@/components/dashboard/live-badge";
import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { JsonTree } from "../../components/JsonTree";
import { styles } from "../../dashboardPageStyles";
import { API_BASE, fetchJson, formatThrownApiError } from "../../lib/api";
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
        setError(formatThrownApiError(e));
      }
    };
    void load();
  }, [runId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset row selection when run route changes
    setListingId(null);
  }, [runId]);

  const exportLinks = [
    { label: "Export JSON", href: `${API_BASE}/api/v1/runs/${runId}/export?format=json` },
    {
      label: "Export JSON (full detail)",
      href: `${API_BASE}/api/v1/runs/${runId}/export?format=json&listing_detail=true`,
    },
    { label: "Export CSV", href: `${API_BASE}/api/v1/runs/${runId}/export?format=csv` },
    {
      label: "Export CSV (full detail)",
      href: `${API_BASE}/api/v1/runs/${runId}/export?format=csv&listing_detail=true`,
    },
  ];

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div className="space-y-2">
          <LiveBadge label="Run detail" />
          <h1 className={cn(styles.title, "font-mono text-base md:text-lg")}>{runId || "…"}</h1>
          <p className={styles.subTitle}>Request snapshot, persisted results, and listing drill-down.</p>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" asChild>
            <Link href="/dashboard/runs">← All runs</Link>
          </Button>
        </div>
        <div className={styles.exportLinkGrid}>
          {exportLinks.map((link) => (
            <Button key={link.href} variant="outline" size="sm" className={styles.exportBtn} asChild>
              <a href={link.href} target="_blank" rel="noopener noreferrer">
                {link.label}
              </a>
            </Button>
          ))}
        </div>
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

      {!run && !error ? (
        <p className={styles.mutedLabel}>Loading…</p>
      ) : error ? (
        <p className={styles.mutedLabel}>Fix the error above to load this run.</p>
      ) : run !== null ? (
        <>
          <SectionCard title="Snapshot" subtitle="Persisted request and result window for this run." light>
            <p className={styles.metaInline}>
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
          </SectionCard>

          <section className={styles.bottomGrid}>
            <section className={styles.resultsPanel}>
              <div className={styles.rowBetween}>
                <h2 className={styles.sectionTitle}>Results in this run</h2>
                <span className={styles.rowCountBadge}>{run.results.length} listings</span>
              </div>
              <div className={styles.runsTableWrap}>
                <table className={cn(styles.dataTable, styles.runsDataTable)}>
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
                      <tr
                        key={r.listing_id}
                        className={cn(
                          styles.tableRow,
                          listingId === r.listing_id && styles.selectedRow,
                        )}
                        onClick={() => setListingId(r.listing_id)}
                      >
                        <td className={styles.cellMono}>{r.listing_id}</td>
                        <td className={styles.cellHighlight}>{r.score.toFixed(4)}</td>
                        <td>{r.confidence.toFixed(2)}</td>
                        <td className={styles.tableActionsCol}>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className={styles.rowActionBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              setListingId(r.listing_id);
                            }}
                          >
                            Load detail
                          </Button>
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
                <p className={styles.mutedLabel}>Select a row or choose “Load detail”.</p>
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
