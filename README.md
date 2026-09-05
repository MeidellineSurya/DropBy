# DropBy

Location-based social deal discovery — "Pokémon GO, but you catch experiences." See
`Charlie - DropBy (1).txt` for the full product brief and
`.claude` plan history for the architecture rationale.

## Structure

- `apps/api` — FastAPI backend (modular monolith: discovery/real-time, business/supply, redemption+gamification+notifications modules), PostgreSQL+PostGIS, Redis, Celery.
- `apps/mobile` — React Native consumer app (JS-layer skeleton; native `ios`/`android` projects not yet generated — see `apps/mobile/README.md`).
- `apps/dashboard` — React + Vite business dashboard.
- `packages/ws-contracts` — frozen Pydantic WebSocket event/DTO contracts, the source of truth for `packages/shared-types`.
- `packages/shared-types` — TypeScript types mirroring `ws-contracts`, for both frontends.
- `infra/docker-compose.yml` — local dev stack (postgres+postgis, redis, api, worker, beat, dashboard).

## Getting started

```bash
# Backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload

# Dashboard
cd apps/dashboard
npm install
npm run dev

# Full stack via Docker
docker compose -f infra/docker-compose.yml up --build
```

Mobile app native scaffolding still needs to be generated — see `apps/mobile/README.md`.

## Status

The real-time discovery workstream is implemented: JWT/onboarding, PostGIS
Detect/Reveal/Discover, authenticated WebSockets, Drop lifecycle jobs, squad
formation, capacity enforcement, migrations, and Docker wiring. See
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md) for setup and a
seeded walkthrough.

The business, redemption, gamification, notifications, mobile, and dashboard
workstreams remain owned separately and still contain scaffold placeholders.
