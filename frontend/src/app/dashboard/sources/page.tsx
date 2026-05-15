"use client";

import { Copy } from "lucide-react";
import { useEffect, useState } from "react";

import { LiveBadge } from "@/components/dashboard/live-badge";
import { SectionCard } from "@/components/dashboard/section-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";

import { useToast } from "../components/DashboardChrome";
import { JsonTree } from "../components/JsonTree";
import { styles } from "../dashboardPageStyles";
import { API_BASE, fetchJson, formatThrownApiError, sourcesQuery } from "../lib/api";
import type { SourceSummary } from "../lib/types";

export default function SourcesPage() {
  const { pushToast } = useToast();
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
        setSelected((prev) => {
          if (!prev) return prev;
          return data.find((r) => r.source === prev.source) ?? null;
        });
      } catch (e) {
        setError(formatThrownApiError(e));
      }
    };
    void load();
  }, [status, q]);

  return (
    <main className={styles.main}>
      <header className={styles.topHeader}>
        <div className="space-y-2">
          <LiveBadge label="Dataset sources" />
          <h1 className={styles.title}>Source Library</h1>
          <p className={styles.subTitle}>Inspect ingestion jobs, validation summaries, and freshness.</p>
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
        title="Filters"
        subtitle="Narrow by job status or search path and source token."
        light
      >
        <div className={styles.filterBar}>
          <div className={styles.filterField}>
            <Label htmlFor="source-status-filter" className={styles.filterLabel}>
              Status
            </Label>
            <Select
              id="source-status-filter"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              aria-label="Filter by ingestion job status"
            >
              <option value="">All statuses</option>
              <option value="created">Created</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="completed_with_errors">Completed with errors</option>
              <option value="analyzed">Analyzed</option>
              <option value="failed">Failed</option>
            </Select>
          </div>
          <div className={styles.filterFieldGrow}>
            <Label htmlFor="source-search" className={styles.filterLabel}>
              Search
            </Label>
            <Input
              id="source-search"
              type="search"
              placeholder="Path or source token…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Search input path or source token"
            />
          </div>
        </div>
      </SectionCard>

      <section className={styles.bottomGrid}>
        <section className={styles.resultsPanel}>
          <div className={styles.rowBetween}>
            <h2 className={styles.sectionTitle}>Sources</h2>
            {!error && rows.length > 0 ? (
              <span className={styles.rowCountBadge}>{rows.length} rows</span>
            ) : null}
          </div>
          {!error && rows.length > 0 ? (
            <p className={styles.sectionHint}>Scroll horizontally to view full paths.</p>
          ) : null}
          {error ? (
            <p className={styles.mutedLabel}>Fix the error above, or adjust filters.</p>
          ) : rows.length === 0 ? (
            <p className={styles.mutedLabel}>No sources match filters.</p>
          ) : (
            <div className={styles.sourcesTableWrap}>
              <table className={cn(styles.dataTable, styles.sourcesDataTable)}>
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
                  {rows.map((r) => {
                    const isSelected = selected?.source === r.source;
                    return (
                      <tr
                        key={r.source}
                        className={cn(styles.tableRow, isSelected && styles.selectedRow)}
                        onClick={() => setSelected(r)}
                      >
                        <td>
                          <button
                            type="button"
                            className={styles.sourceLink}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(r);
                            }}
                          >
                            {r.source}
                          </button>
                        </td>
                        <td className={styles.cellMono}>{r.job_id}</td>
                        <td className={styles.cellPath}>{r.input_path}</td>
                        <td>
                          <span className={styles.chip}>{r.status}</span>
                        </td>
                        <td className={styles.cellHighlight}>{r.records_valid}</td>
                        <td>{r.records_invalid}</td>
                        <td className={styles.cellMono}>{r.finished_at ?? "—"}</td>
                      </tr>
                    );
                  })}
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
                Validation status:{" "}
                <strong className="text-slate-200">{selected.validation_status ?? "n/a"}</strong>
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => {
                    void navigator.clipboard.writeText(selected.source);
                    pushToast("Source token copied");
                  }}
                >
                  <Copy className="h-3.5 w-3.5" aria-hidden />
                  Copy source token
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => {
                    void navigator.clipboard.writeText(selected.input_path);
                    pushToast("Input path copied");
                  }}
                >
                  <Copy className="h-3.5 w-3.5" aria-hidden />
                  Copy input path
                </Button>
              </div>
              <div className={styles.pathPanel}>
                <h4 className={styles.blockTitle}>Input path</h4>
                <p>{selected.input_path}</p>
              </div>
              <div className={styles.detailSections}>
                <div className={styles.detailBlock}>
                  <h4>validation_summary</h4>
                  <JsonTree data={selected.validation_summary ?? {}} />
                </div>
              </div>
            </>
          )}
        </section>
      </section>
    </main>
  );
}
