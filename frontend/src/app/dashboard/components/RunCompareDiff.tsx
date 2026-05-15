"use client";

import { cn } from "@/lib/utils";

import { styles } from "../dashboardPageStyles";
import { formatDelta, type RunCompareResult } from "../lib/compareRuns";

function DiffTable({ rows, emptyLabel }: { rows: RunCompareResult["metadata_diffs"]; emptyLabel: string }) {
  if (rows.length === 0) {
    return <p className={styles.mutedLabel}>{emptyLabel}</p>;
  }
  return (
    <div className={styles.runsTableWrap}>
      <table className={cn(styles.dataTable, styles.runsDataTable)}>
        <thead>
          <tr>
            <th>Field</th>
            <th>Baseline</th>
            <th>Candidate</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field}>
              <td>
                <code className={styles.runIdCell}>{row.field}</code>
              </td>
              <td className={styles.diffRemoved}>{row.baseline}</td>
              <td className={styles.diffAdded}>{row.candidate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RunCompareDiff({ result }: { result: RunCompareResult }) {
  if (result.same_run) {
    return (
      <p className={styles.mutedLabel}>
        Baseline and candidate are the same run — choose two different runs to compare.
      </p>
    );
  }

  const noChanges =
    result.metadata_diffs.length === 0 &&
    result.request_diffs.length === 0 &&
    result.result_window_diffs.length === 0 &&
    result.listing_diffs.length === 0;

  return (
    <div className={styles.compareDiff}>
      <div className={styles.compareSummary}>
        <div className={styles.statTile}>
          <span>Shared listings</span>
          <strong>{result.shared_count}</strong>
        </div>
        <div className={styles.statTile}>
          <span>Changed rows</span>
          <strong>{result.changed_listing_count}</strong>
        </div>
        <div className={styles.statTile}>
          <span>Baseline only</span>
          <strong>{result.only_baseline.length}</strong>
        </div>
        <div className={styles.statTile}>
          <span>Candidate only</span>
          <strong>{result.only_candidate.length}</strong>
        </div>
      </div>

      {noChanges ? (
        <p className={styles.mutedLabel}>No differences found between these runs.</p>
      ) : (
        <>
          <section className={styles.compareSection}>
            <h3 className={styles.blockTitle}>Run metadata</h3>
            <DiffTable rows={result.metadata_diffs} emptyLabel="Run metadata matches." />
          </section>

          <section className={styles.compareSection}>
            <h3 className={styles.blockTitle}>Request snapshot</h3>
            <DiffTable rows={result.request_diffs} emptyLabel="Request snapshots match." />
          </section>

          <section className={styles.compareSection}>
            <h3 className={styles.blockTitle}>Result window</h3>
            <DiffTable rows={result.result_window_diffs} emptyLabel="Result windows match." />
          </section>

          <section className={styles.compareSection}>
            <h3 className={styles.blockTitle}>Listing score / rank changes</h3>
            {result.listing_diffs.length === 0 ? (
              <p className={styles.mutedLabel}>No listing-level differences in persisted results.</p>
            ) : (
              <div className={styles.runsTableWrap}>
                <table className={cn(styles.dataTable, styles.runsDataTable)}>
                  <thead>
                    <tr>
                      <th>Listing</th>
                      <th>Status</th>
                      <th>Baseline score</th>
                      <th>Candidate score</th>
                      <th>Δ score</th>
                      <th>Baseline rank</th>
                      <th>Candidate rank</th>
                      <th>Δ rank</th>
                      <th>Deal reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.listing_diffs.map((row) => (
                      <tr key={row.listing_id}>
                        <td className={styles.cellMono}>{row.listing_id}</td>
                        <td>
                          <span className={styles.chip}>
                            {row.status === "baseline_only"
                              ? "Baseline only"
                              : row.status === "candidate_only"
                                ? "Candidate only"
                                : "Changed"}
                          </span>
                        </td>
                        <td>{row.baseline_score?.toFixed(4) ?? "—"}</td>
                        <td>{row.candidate_score?.toFixed(4) ?? "—"}</td>
                        <td className={deltaClass(row.score_delta)}>{formatDelta(row.score_delta)}</td>
                        <td>{row.baseline_rank ?? "—"}</td>
                        <td>{row.candidate_rank ?? "—"}</td>
                        <td className={deltaClass(row.rank_delta, true)}>{formatDelta(row.rank_delta, 0)}</td>
                        <td>{row.deal_reason_changed ? "Changed" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function deltaClass(value: number | null, invert = false): string | undefined {
  if (value === null || value === 0) {
    return undefined;
  }
  const positive = invert ? value < 0 : value > 0;
  return positive ? styles.diffAdded : styles.diffRemoved;
}
