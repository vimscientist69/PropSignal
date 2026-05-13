import type { ListingDetail, RankingResponse, RankingResult } from "./types";

export type ExportMetadata = {
  run_id: string;
  generated_at: string;
  strategy_preset: string | undefined;
  profile_id: string | undefined;
  profile_version: string | undefined;
  source_set: string[];
  applied_filters: Record<string, unknown>;
  listing_detail_included?: boolean;
};

export function buildExportMetadata(
  ranking: RankingResponse,
  extras?: { strategy_preset?: string; filters?: Record<string, unknown>; listing_detail_included?: boolean },
): ExportMetadata {
  return {
    run_id: ranking.run_id,
    generated_at: new Date().toISOString(),
    strategy_preset: extras?.strategy_preset,
    profile_id: ranking.resolved_profile.profile_id,
    profile_version: ranking.resolved_profile.profile_version,
    source_set: ranking.dataset_context.selected_sources,
    applied_filters: extras?.filters ?? {},
    listing_detail_included: extras?.listing_detail_included,
  };
}

export function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.click();
  URL.revokeObjectURL(url);
}

function mergeRowsWithDetail(
  rows: RankingResult[],
  detailsByListingId: Map<number, ListingDetail> | undefined,
): Record<string, unknown>[] {
  return rows.map((r) => {
    const base: Record<string, unknown> = { ...r };
    const detail = detailsByListingId?.get(r.listing_id);
    if (detail) {
      base.listing_detail = detail;
    }
    return base;
  });
}

export function exportRankingJson(
  ranking: RankingResponse,
  rows: RankingResult[],
  meta: ExportMetadata,
  options?: { detailsByListingId?: Map<number, ListingDetail> },
) {
  const hasDetail = Boolean(options?.detailsByListingId && options.detailsByListingId.size > 0);
  const metaOut: ExportMetadata = { ...meta, listing_detail_included: hasDetail || meta.listing_detail_included };
  const results = mergeRowsWithDetail(rows, options?.detailsByListingId);
  const payload = { export_metadata: metaOut, results };
  const slug = hasDetail ? "-full-detail" : "";
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  downloadBlob(`${ranking.run_id}-export${slug}.json`, blob);
}

export function exportRankingCsv(
  ranking: RankingResponse,
  rows: RankingResult[],
  meta: ExportMetadata,
  options?: { detailsByListingId?: Map<number, ListingDetail> },
) {
  const hasDetail = Boolean(options?.detailsByListingId && options.detailsByListingId.size > 0);
  const metaOut: ExportMetadata = { ...meta, listing_detail_included: hasDetail || meta.listing_detail_included };
  const lines: string[] = [];
  lines.push(`# export_metadata: ${JSON.stringify(metaOut)}`);
  if (rows.length === 0) {
    lines.push("listing_id,score,confidence,deal_reason");
    const slug = hasDetail ? "-full-detail" : "";
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    downloadBlob(`${ranking.run_id}-export${slug}.csv`, blob);
    return;
  }
  const flat: Record<string, string | number>[] = rows.map((r) => {
    const row: Record<string, string | number> = {
      listing_id: r.listing_id,
      score: r.score,
      confidence: r.confidence,
      deal_reason: r.deal_reason,
      listing_url: r.listing_url ?? "",
      bedrooms: r.bedrooms ?? "",
      bathrooms: r.bathrooms ?? "",
      province: r.province ?? "",
      source_site: r.source_site ?? "",
      summary_json: JSON.stringify(r.summary),
    };
    const d = options?.detailsByListingId?.get(r.listing_id);
    if (d) {
      row.listing_detail_json = JSON.stringify(d);
    }
    return row;
  });
  const headers = Object.keys(flat[0]);
  lines.push(headers.join(","));
  for (const row of flat) {
    lines.push(
      headers
        .map((h) => {
          const v = row[h];
          const s = String(v ?? "");
          if (s.includes(",") || s.includes('"') || s.includes("\n")) {
            return `"${s.replace(/"/g, '""')}"`;
          }
          return s;
        })
        .join(","),
    );
  }
  const slug = hasDetail ? "-full-detail" : "";
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  downloadBlob(`${ranking.run_id}-export${slug}.csv`, blob);
}
