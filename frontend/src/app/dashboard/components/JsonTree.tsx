"use client";

import { useState } from "react";

import styles from "../dashboard.module.css";

type JsonTreeProps = {
  data: unknown;
  depth?: number;
  path?: string;
};

function JsonArrayTree({ data, depth, path }: { data: unknown[]; depth: number; path: string }) {
  const defaultClosed =
    data.length > 0 && depth >= 1 && (data.length > 6 || path.includes("normalized_payload"));
  const [open, setOpen] = useState(!defaultClosed);
  if (data.length === 0) {
    return <span className={styles.emptyKV}>—</span>;
  }
  return (
    <div className={styles.jsonTree}>
      {depth >= 1 ? (
        <button
          type="button"
          className={styles.jsonToggle}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? "−" : "+"} [{data.length}]
        </button>
      ) : null}
      {(depth < 1 || open) && (
        <div className={depth >= 1 ? styles.jsonRow : undefined}>
          {data.map((item, i) => (
            <div key={i} className={styles.jsonRow}>
              <span className={styles.jsonKey}>[{i}]: </span>
              <JsonTree data={item} depth={depth + 1} path={`${path}[${i}]`} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function JsonObjectTree({
  data,
  depth,
  path,
}: {
  data: Record<string, unknown>;
  depth: number;
  path: string;
}) {
  const keys = Object.keys(data).sort();
  const defaultClosed =
    keys.length > 0 && depth >= 1 && (path.includes("normalized_payload") || keys.length > 14);
  const [open, setOpen] = useState(!defaultClosed);
  if (keys.length === 0) {
    return <span className={styles.emptyKV}>—</span>;
  }
  return (
    <div className={styles.jsonTree}>
      {depth >= 1 ? (
        <button
          type="button"
          className={styles.jsonToggle}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? "−" : "+"} {`{${keys.length}}`}
        </button>
      ) : null}
      {(depth < 1 || open) && (
        <div className={depth >= 1 ? styles.jsonRow : undefined}>
          {keys.map((k) => (
            <div key={k} className={styles.jsonRow}>
              <span className={styles.jsonKey}>{k}: </span>
              <JsonTree data={data[k]} depth={depth + 1} path={path ? `${path}.${k}` : k} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function JsonTree({ data, depth = 0, path = "" }: JsonTreeProps) {
  if (data === null || data === undefined) {
    return <span className={styles.emptyKV}>—</span>;
  }
  if (typeof data !== "object") {
    if (typeof data === "string" && data.length === 0) {
      return <span className={styles.emptyKV}>—</span>;
    }
    return <span>{String(data)}</span>;
  }
  if (Array.isArray(data)) {
    return <JsonArrayTree data={data} depth={depth} path={path} />;
  }
  return <JsonObjectTree data={data as Record<string, unknown>} depth={depth} path={path} />;
}
