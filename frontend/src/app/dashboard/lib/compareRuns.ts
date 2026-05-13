import type { RankingResult, RunDetailResponse } from "./types";

export type FieldDiff = {
  field: string;
  baseline: string;
  candidate: string;
};

export type ListingScoreDiff = {
  listing_id: number;
  baseline_score: number | null;
  candidate_score: number | null;
  score_delta: number | null;
  baseline_rank: number | null;
  candidate_rank: number | null;
  rank_delta: number | null;
  baseline_confidence: number | null;
  candidate_confidence: number | null;
  confidence_delta: number | null;
  deal_reason_changed: boolean;
  status: "changed" | "baseline_only" | "candidate_only";
};

export type RunCompareResult = {
  same_run: boolean;
  metadata_diffs: FieldDiff[];
  request_diffs: FieldDiff[];
  result_window_diffs: FieldDiff[];
  listing_diffs: ListingScoreDiff[];
  only_baseline: number[];
  only_candidate: number[];
  shared_count: number;
  changed_listing_count: number;
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function flattenObject(value: unknown, prefix = ""): Record<string, string> {
  if (value === null || value === undefined) {
    return prefix ? { [prefix]: formatValue(value) } : {};
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    return prefix ? { [prefix]: formatValue(value) } : {};
  }
  const out: Record<string, string> = {};
  const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
    a.localeCompare(b),
  );
  for (const [key, child] of entries) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child !== null && typeof child === "object" && !Array.isArray(child)) {
      Object.assign(out, flattenObject(child, path));
    } else {
      out[path] = formatValue(child);
    }
  }
  return out;
}

function diffFlatMaps(baseline: Record<string, string>, candidate: Record<string, string>): FieldDiff[] {
  const keys = new Set([...Object.keys(baseline), ...Object.keys(candidate)]);
  const diffs: FieldDiff[] = [];
  for (const field of [...keys].sort()) {
    const left = baseline[field] ?? "—";
    const right = candidate[field] ?? "—";
    if (left !== right) {
      diffs.push({ field, baseline: left, candidate: right });
    }
  }
  return diffs;
}

function rankByScore(results: RankingResult[]): Map<number, number> {
  const sorted = [...results].sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    return a.listing_id - b.listing_id;
  });
  const ranks = new Map<number, number>();
  sorted.forEach((row, index) => {
    ranks.set(row.listing_id, index + 1);
  });
  return ranks;
}

function metadataDiffs(baseline: RunDetailResponse, candidate: RunDetailResponse): FieldDiff[] {
  const fields: Array<{ key: keyof RunDetailResponse; label: string }> = [
    { key: "strategy_preset", label: "strategy_preset" },
    { key: "profile_id", label: "profile_id" },
    { key: "profile_row_id", label: "profile_row_id" },
    { key: "source_count", label: "source_count" },
    { key: "records_considered", label: "records_considered" },
    { key: "result_count", label: "result_count" },
    { key: "query_fingerprint", label: "query_fingerprint" },
    { key: "latency_ms", label: "latency_ms" },
  ];
  const diffs: FieldDiff[] = [];
  for (const { key, label } of fields) {
    const left = formatValue(baseline[key]);
    const right = formatValue(candidate[key]);
    if (left !== right) {
      diffs.push({ field: label, baseline: left, candidate: right });
    }
  }
  return diffs;
}

function listingDiffs(
  baseline: RunDetailResponse,
  candidate: RunDetailResponse,
): {
  rows: ListingScoreDiff[];
  only_baseline: number[];
  only_candidate: number[];
  shared_count: number;
  changed_listing_count: number;
} {
  const baselineById = new Map(baseline.results.map((row) => [row.listing_id, row]));
  const candidateById = new Map(candidate.results.map((row) => [row.listing_id, row]));
  const baselineRanks = rankByScore(baseline.results);
  const candidateRanks = rankByScore(candidate.results);
  const ids = new Set([...baselineById.keys(), ...candidateById.keys()]);

  const only_baseline: number[] = [];
  const only_candidate: number[] = [];
  const rows: ListingScoreDiff[] = [];
  let changed_listing_count = 0;
  let shared_count = 0;

  for (const listing_id of [...ids].sort((a, b) => a - b)) {
    const baseRow = baselineById.get(listing_id);
    const candRow = candidateById.get(listing_id);
    const baseline_rank = baselineRanks.get(listing_id) ?? null;
    const candidate_rank = candidateRanks.get(listing_id) ?? null;
    const baseline_score = baseRow?.score ?? null;
    const candidate_score = candRow?.score ?? null;
    const baseline_confidence = baseRow?.confidence ?? null;
    const candidate_confidence = candRow?.confidence ?? null;
    const score_delta =
      baseline_score !== null && candidate_score !== null ? candidate_score - baseline_score : null;
    const rank_delta =
      baseline_rank !== null && candidate_rank !== null ? candidate_rank - baseline_rank : null;
    const confidence_delta =
      baseline_confidence !== null && candidate_confidence !== null
        ? candidate_confidence - baseline_confidence
        : null;
    const deal_reason_changed =
      baseRow !== undefined &&
      candRow !== undefined &&
      baseRow.deal_reason !== candRow.deal_reason;

    let status: ListingScoreDiff["status"];
    if (baseRow && !candRow) {
      status = "baseline_only";
      only_baseline.push(listing_id);
    } else if (!baseRow && candRow) {
      status = "candidate_only";
      only_candidate.push(listing_id);
    } else {
      status = "changed";
      shared_count += 1;
    }

    const changed =
      status !== "changed" ||
      score_delta !== 0 ||
      rank_delta !== 0 ||
      confidence_delta !== 0 ||
      deal_reason_changed;

    if (changed) {
      changed_listing_count += 1;
      rows.push({
        listing_id,
        baseline_score,
        candidate_score,
        score_delta,
        baseline_rank,
        candidate_rank,
        rank_delta,
        baseline_confidence,
        candidate_confidence,
        confidence_delta,
        deal_reason_changed,
        status,
      });
    }
  }

  return { rows, only_baseline, only_candidate, shared_count, changed_listing_count };
}

export function compareRunDetails(
  baseline: RunDetailResponse,
  candidate: RunDetailResponse,
): RunCompareResult {
  if (baseline.run_id === candidate.run_id) {
    return {
      same_run: true,
      metadata_diffs: [],
      request_diffs: [],
      result_window_diffs: [],
      listing_diffs: [],
      only_baseline: [],
      only_candidate: [],
      shared_count: baseline.results.length,
      changed_listing_count: 0,
    };
  }

  const listing = listingDiffs(baseline, candidate);
  return {
    same_run: false,
    metadata_diffs: metadataDiffs(baseline, candidate),
    request_diffs: diffFlatMaps(
      flattenObject(baseline.request_snapshot),
      flattenObject(candidate.request_snapshot),
    ),
    result_window_diffs: diffFlatMaps(
      flattenObject(baseline.result_window),
      flattenObject(candidate.result_window),
    ),
    listing_diffs: listing.rows,
    only_baseline: listing.only_baseline,
    only_candidate: listing.only_candidate,
    shared_count: listing.shared_count,
    changed_listing_count: listing.changed_listing_count,
  };
}

export function formatDelta(value: number | null, digits = 4): string {
  if (value === null) {
    return "—";
  }
  if (value === 0) {
    return "0";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}
