"use client";

import { useEffect, useState } from "react";

import { JsonTree } from "../../components/JsonTree";
import styles from "../../dashboard.module.css";
import { fetchJson } from "../../lib/api";
import type { ListingDetail } from "../../lib/types";

export function RunListingDetail({ runId, listingId }: { runId: string; listingId: number }) {
  const [detail, setDetail] = useState<ListingDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const d = await fetchJson<ListingDetail>(`/api/v1/rankings/${runId}/listings/${listingId}`);
        if (!cancelled) {
          setDetail(d);
          setDetailError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setDetailError((e as Error).message);
          setDetail(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId, listingId]);

  if (loading) {
    return <div className={styles.skeleton} style={{ width: "100%" }} aria-hidden />;
  }
  if (detailError) {
    return <p className={styles.error}>{detailError}</p>;
  }
  if (!detail) {
    return <p className={styles.mutedLabel}>No detail.</p>;
  }
  return (
    <div className={styles.detailSections}>
      <div className={styles.detailBlock}>
        <h4>listing_core</h4>
        <JsonTree data={detail.listing_core} />
      </div>
      <div className={styles.detailBlock}>
        <h4>score_summary</h4>
        <JsonTree data={detail.score_summary} />
      </div>
      <div className={styles.detailBlock}>
        <h4>diagnostics</h4>
        <JsonTree data={detail.diagnostics} />
      </div>
    </div>
  );
}
