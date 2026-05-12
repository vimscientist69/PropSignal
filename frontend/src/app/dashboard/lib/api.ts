import type { ErrorResponse, ListingDetail } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Human-readable message for thrown fetch failures (network, DNS, CORS, etc.). */
export function formatFetchFailure(reason: unknown): string {
  if (reason instanceof Error && reason.message.trim()) {
    return reason.message.trim();
  }
  if (typeof reason === "string" && reason.trim()) {
    return reason.trim();
  }
  return "Network request failed.";
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (reason) {
    const detail = formatFetchFailure(reason);
    throw new Error(
      `Cannot reach API at ${API_BASE} (${detail}). Is the backend running and CORS allowing this origin?`,
    );
  }
  if (!response.ok) {
    let payload: ErrorResponse | null = null;
    try {
      payload = (await response.json()) as ErrorResponse;
    } catch {
      payload = null;
    }
    const message = payload?.message ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export async function fetchListingDetailsForRun(
  runId: string,
  listingIds: number[],
): Promise<Map<number, ListingDetail>> {
  const map = new Map<number, ListingDetail>();
  await Promise.all(
    listingIds.map(async (id) => {
      const d = await fetchJson<ListingDetail>(`/api/v1/rankings/${runId}/listings/${id}`);
      map.set(id, d);
    }),
  );
  return map;
}

export function sourcesQuery(status?: string, q?: string): string {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (q) {
    params.set("q", q);
  }
  const qs = params.toString();
  return qs ? `/api/v1/datasets/sources?${qs}` : "/api/v1/datasets/sources";
}
