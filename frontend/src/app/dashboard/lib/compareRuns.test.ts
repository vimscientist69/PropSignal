import { describe, expect, it } from "vitest";

import { compareRunDetails, formatDelta } from "./compareRuns";
import type { RankingResult, RunDetailResponse } from "./types";

function makeResult(listing_id: number, score: number): RankingResult {
  return {
    listing_id,
    score,
    deal_reason: "test",
    confidence: 0.9,
    summary: {},
    detail_ref: `run:listing-${listing_id}`,
  };
}

function makeRun(run_id: string, results: RankingResult[]): RunDetailResponse {
  return {
    run_id,
    created_at: "2026-01-01T00:00:00Z",
    query_fingerprint: "fp",
    strategy_preset: "rental_income",
    profile_id: "rental_income_default",
    profile_row_id: 1,
    source_count: 1,
    records_considered: results.length,
    result_count: results.length,
    request_snapshot: { strategy: { preset: "rental_income" } },
    result_window: { top_n: results.length },
    results,
    latency_ms: null,
  };
}

describe("compareRunDetails", () => {
  it("detects identical run ids", () => {
    const run = makeRun("run-a", [makeResult(1, 0.5)]);
    const result = compareRunDetails(run, run);
    expect(result.same_run).toBe(true);
    expect(result.listing_diffs).toHaveLength(0);
  });

  it("reports score delta for shared listings", () => {
    const baseline = makeRun("run-a", [makeResult(1, 0.4)]);
    const candidate = makeRun("run-b", [makeResult(1, 0.6)]);
    const result = compareRunDetails(baseline, candidate);
    expect(result.shared_count).toBe(1);
    expect(result.listing_diffs).toHaveLength(1);
    expect(result.listing_diffs[0].score_delta).toBeCloseTo(0.2);
  });

  it("reports baseline-only and candidate-only listings", () => {
    const baseline = makeRun("run-a", [makeResult(1, 0.5)]);
    const candidate = makeRun("run-b", [makeResult(2, 0.5)]);
    const result = compareRunDetails(baseline, candidate);
    expect(result.only_baseline).toEqual([1]);
    expect(result.only_candidate).toEqual([2]);
    expect(result.shared_count).toBe(0);
  });
});

describe("formatDelta", () => {
  it("prefixes positive deltas", () => {
    expect(formatDelta(0.25)).toBe("+0.2500");
  });

  it("returns em dash for null", () => {
    expect(formatDelta(null)).toBe("—");
  });
});
