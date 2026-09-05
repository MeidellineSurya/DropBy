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

To see and interact with the discovery mechanic immediately, double-click
`demo.cmd` or run:

```bat
demo.cmd
```

The browser-only sandbox needs no Docker, database, Python, Node, or install.
It simulates proximity reveals, protected response fields, squad formation, and
the real-time event stream. It is a product demonstration, not an integration
test of the server.

On Windows, install and open Docker Desktop, then run one command from the
repository root when you want to test the real backend:

```bat
dev.cmd
```

The launcher creates `.env` when needed, builds the discovery backend, runs the
database migration, loads repeatable demo data, and opens Swagger at
<http://localhost:8000/docs>.

```bat
dev.cmd logs
dev.cmd status
dev.cmd stop
```

Python dependencies are already defined in `apps/api/requirements.txt` and
development dependencies in `apps/api/requirements-dev.txt`; Docker installs
them during the first build. Manual and non-Docker setup is documented in
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md).

Mobile app native scaffolding still needs to be generated — see `apps/mobile/README.md`.

## Status

The real-time discovery workstream is implemented: JWT/onboarding, PostGIS
Detect/Reveal/Discover, authenticated WebSockets, Drop lifecycle jobs, squad
formation, capacity enforcement, migrations, and Docker wiring. See
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md) for setup and a
seeded walkthrough.

The business, redemption, gamification, notifications, mobile, and dashboard
workstreams remain owned separately and still contain scaffold placeholders.
