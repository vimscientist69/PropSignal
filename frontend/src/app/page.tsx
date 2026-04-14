import styles from "./page.module.css";

type HealthResponse = {
  status: string;
};

async function getApiHealth(): Promise<{
  ok: boolean;
  endpoint: string;
  payload: HealthResponse | null;
}> {
  const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/health`;

  try {
    const response = await fetch(endpoint, { cache: "no-store" });
    if (!response.ok) {
      return { ok: false, endpoint, payload: null };
    }

    const payload = (await response.json()) as HealthResponse;
    return { ok: payload.status === "ok", endpoint, payload };
  } catch {
    return { ok: false, endpoint, payload: null };
  }
}

export default async function Home() {
  const health = await getApiHealth();

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1>PropSignal Dashboard</h1>
        <p>
          Base frontend scaffold is ready. This page verifies backend connectivity using the health
          endpoint.
        </p>
        <section className={styles.statusCard}>
          <h2>Backend Health</h2>
          <p>
            Endpoint: <code>{health.endpoint}</code>
          </p>
          <p className={health.ok ? styles.ok : styles.error}>
            Status: {health.ok ? health.payload?.status ?? "ok" : "unreachable"}
          </p>
        </section>
      </main>
    </div>
  );
}
