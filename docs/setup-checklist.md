# Setup Checklist

Use this checklist to verify the project is ready for development after a fresh clone.

## Environment

- [ ] Install Node.js 20.x and npm 10+
- [ ] Install Python 3.11+ (3.11 recommended)
- [ ] Copy env templates:
  - [ ] `cp .env.example .env`
  - [ ] `cp backend/.env.example backend/.env`
  - [ ] `cp frontend/.env.local.example frontend/.env.local`

## Bootstrap

- [ ] Run `./scripts/setup.sh`
- [ ] Confirm `.venv` exists and backend/frontend dependencies are installed

## Local Quality Gates

- [ ] Run `./scripts/lint.sh`
- [ ] Run `./scripts/test.sh`
- [ ] Run `npm --prefix frontend run build`

## Local Runtime Smoke Test

- [ ] Run backend: `./scripts/run-backend.sh`
- [ ] Run frontend: `./scripts/run-frontend.sh`
- [ ] Open `http://localhost:3000` and confirm backend status card appears
