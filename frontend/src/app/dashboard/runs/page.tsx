"use client";

import Link from "next/link";
import { Copy, ExternalLink } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { LiveBadge } from "@/components/dashboard/live-badge";
import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { RunCompareDiff } from "../components/RunCompareDiff";
import { useToast } from "../components/DashboardChrome";
import { styles } from "../dashboardPageStyles";
import { compareRunDetails, type RunCompareResult } from "../lib/compareRuns";
import { API_BASE, fetchJson, formatThrownApiError } from "../lib/api";
import type { RunDetailResponse, RunSummaryItem, RunsListResponse } from "../lib/types";

const exportBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function RunsPage() {
  const { pushToast } = useToast();
  const [data, setData] = useState<RunsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [baseline, setBaseline] = useState("");
  const [candidate, setCandidate] = useState("");
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [compareResult, setCompareResult] = useState<RunCompareResult | null>(null);

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

  const runCompare = useCallback(async () => {
    if (!baseline || !candidate) {
      return;
    }
    setCompareLoading(true);
    setCompareError(null);
    setCompareResult(null);
    try {
      const [baselineRun, candidateRun] =
        baseline === candidate
          ? await fetchJson<RunDetailResponse>(`/api/v1/runs/${baseline}`).then((run) => [run, run] as const)
          : await Promise.all([
              fetchJson<RunDetailResponse>(`/api/v1/runs/${baseline}`),
              fetchJson<RunDetailResponse>(`/api/v1/runs/${candidate}`),
            ]);
      setCompareResult(compareRunDetails(baselineRun, candidateRun));
    } catch (e) {
      setCompareError(formatThrownApiError(e));
    } finally {
      setCompareLoading(false);
    }
  }, [baseline, candidate]);

  const items = data?.items ?? [];

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div className="space-y-2">
          <LiveBadge label="Run history" />
          <h1 className={styles.title}>Runs</h1>
          <p className={styles.subTitle}>Browse persisted ranking runs and reopen exports or detail context.</p>
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

      <SectionCard
        title="Compare mode"
        subtitle="Pick a baseline and candidate run, then compare metadata, request config, and listing score/rank deltas."
        light
      >
        <div className={styles.comparePicker}>
          <div className={styles.comparePickerField}>
            <Label htmlFor="compare-baseline" className={styles.filterLabel}>
              Baseline
            </Label>
            <Select
              id="compare-baseline"
              value={baseline}
              onChange={(e) => {
                setBaseline(e.target.value);
                setCompareResult(null);
                setCompareError(null);
              }}
              disabled={items.length === 0}
            >
              {items.map((r: RunSummaryItem) => (
                <option key={`b-${r.run_id}`} value={r.run_id}>
                  {r.run_id}
                </option>
              ))}
            </Select>
          </div>
          <div className={styles.comparePickerField}>
            <Label htmlFor="compare-candidate" className={styles.filterLabel}>
              Candidate
            </Label>
            <Select
              id="compare-candidate"
              value={candidate}
              onChange={(e) => {
                setCandidate(e.target.value);
                setCompareResult(null);
                setCompareError(null);
              }}
              disabled={items.length === 0}
            >
              {items.map((r: RunSummaryItem) => (
                <option key={`c-${r.run_id}`} value={r.run_id}>
                  {r.run_id}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <p className={styles.metaInline}>
          Selected: <code>{baseline || "—"}</code> vs <code>{candidate || "—"}</code>
        </p>
        <div className={styles.actions}>
          <Button
            type="button"
            variant="primary"
            disabled={!baseline || !candidate || compareLoading || items.length === 0}
            onClick={() => void runCompare()}
          >
            {compareLoading ? "Comparing…" : "Compare runs"}
          </Button>
          {baseline ? (
            <Button variant="outline" size="sm" asChild>
              <Link href={`/dashboard/runs/${baseline}`}>Open baseline</Link>
            </Button>
          ) : null}
          {candidate ? (
            <Button variant="outline" size="sm" asChild>
              <Link href={`/dashboard/runs/${candidate}`}>Open candidate</Link>
            </Button>
          ) : null}
        </div>

        {compareError ? (
          <div className={cn(styles.error, "mt-3")}>
            <pre className={styles.errorMultiline}>{compareError}</pre>
          </div>
        ) : null}

        {compareResult ? (
          <div className="mt-4 border-t border-slate-800/80 pt-4">
            <RunCompareDiff result={compareResult} />
          </div>
        ) : null}
      </SectionCard>

      <section className={styles.resultsPanel}>
        <div className={styles.rowBetween}>
          <h2 className={styles.sectionTitle}>Run history</h2>
          {data && data.items.length > 0 ? (
            <span className={styles.rowCountBadge}>{data.items.length} runs</span>
          ) : null}
        </div>
        {!error && data && data.items.length > 0 ? (
          <p className={styles.sectionHint}>Scroll horizontally for row actions.</p>
        ) : null}
        {!data && !error ? (
          <p className={styles.mutedLabel}>Loading…</p>
        ) : error ? (
          <p className={styles.mutedLabel}>Fix the error above to load run history.</p>
        ) : data !== null && data.items.length === 0 ? (
          <p className={styles.mutedLabel}>No runs yet — execute a ranking from the Control Panel.</p>
        ) : data !== null ? (
          <div className={styles.runsTableWrap}>
            <table className={cn(styles.dataTable, styles.runsDataTable)}>
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
                  <tr key={r.run_id} className={styles.tableRow}>
                    <td>
                      <Link href={`/dashboard/runs/${r.run_id}`} className={styles.runIdCell}>
                        {r.run_id}
                      </Link>
                    </td>
                    <td className={styles.cellMono}>{r.created_at}</td>
                    <td>{r.strategy_preset}</td>
                    <td className={styles.cellMono}>{r.profile_id}</td>
                    <td className={styles.cellHighlight}>{r.source_count}</td>
                    <td>{r.records_considered}</td>
                    <td className={styles.cellHighlight}>{r.result_count}</td>
                    <td className={styles.tableActionsCol}>
                      <div className={styles.rowActions}>
                        <Button variant="outline" size="sm" className={styles.rowActionBtn} asChild>
                          <Link href={`/dashboard/runs/${r.run_id}`}>View</Link>
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className={styles.rowActionBtn}
                          onClick={() => {
                            void navigator.clipboard.writeText(r.run_id);
                            pushToast("Run id copied");
                          }}
                        >
                          <Copy className="h-3 w-3" aria-hidden />
                          Copy
                        </Button>
                        <Button variant="ghost" size="sm" className={styles.rowActionBtn} asChild>
                          <a
                            href={`${exportBase}/api/v1/runs/${r.run_id}/export?format=json`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="h-3 w-3" aria-hidden />
                            JSON
                          </a>
                        </Button>
                        <Button variant="ghost" size="sm" className={styles.rowActionBtn} asChild>
                          <a
                            href={`${exportBase}/api/v1/runs/${r.run_id}/export?format=json&listing_detail=true`}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Detail
                          </a>
                        </Button>
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
