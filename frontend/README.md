# PropSignal frontend

Next.js App Router dashboard for the PropSignal operator console.

## Routes

| Path | Tab |
|------|-----|
| `/dashboard/control` | Ranking workbench |
| `/dashboard/sources` | Source Library |
| `/dashboard/runs` | Run history and compare |
| `/dashboard/runs/[runId]` | Run detail |
| `/dashboard/diagnostics` | Health snapshot |

`/ ` redirects to `/dashboard/control`.

## Local development

From repository root:

```bash
cp frontend/.env.local.example frontend/.env.local
./scripts/run-frontend.sh
```

Requires the API at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

## Scripts

```bash
npm run dev        # development server
npm run build      # production build
npm run lint       # ESLint
npm run typecheck  # tsc --noEmit
npm test           # unit tests (vitest)
```

Project-wide setup, demo, and documentation: [`../README.md`](../README.md) and [`../docs/dashboard.md`](../docs/dashboard.md).
