# Configuration Guide

## Environment Files

- Root `.env` is for shared local script values.
- `backend/.env` is for API service runtime configuration.
- `frontend/.env.local` is for browser-exposed frontend configuration.

Use the provided example files to create local copies:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.local.example`

Do not commit real environment files with secrets.

## Backend Variables

- `APP_NAME` - API title shown in docs.
- `ENVIRONMENT` - runtime environment label.
- `API_PREFIX` - API route prefix.
- `FRONTEND_URL` - allowed CORS origin for local frontend.

## Frontend Variables

- `NEXT_PUBLIC_API_BASE_URL` - base URL for backend API calls from the dashboard.

## Scoring Configuration

The initial scoring profile lives at `config/scoring.yaml`.

- `weights` controls contribution by signal.
- `rules` controls baseline thresholds.
- `flags` enables or disables optional signals.
