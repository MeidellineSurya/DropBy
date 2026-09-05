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
It uses an interactive Melbourne street map with real metre-scaled proximity
rings and five fictional Drops across food, entertainment, nightlife, and
wellness. Each marker independently changes from hidden → detected → revealed
→ discovered, and the page simulates protected response fields, squad
formation, and the real-time event stream. An internet connection is only
needed to load the map library and street tiles. It is a product demonstration,
not an integration test of the server.

Try the complete flow:

1. Pan/zoom and click the map to move, or press **Detect · 500 m**.
   Click any Drop marker to inspect what is currently revealed.
2. Press **Reveal · 150 m** to expose the category and rarity.
3. Press **Discover · 50 m** to expose the venue and full offer.
4. Create a squad and add members to move through 2/4, 3/4, and 4/4.
5. Compare the API response and real-time event stream after each action.

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

## Workstream 1 sign-off

Implemented for the real-time discovery owner:

- authenticated WebSockets and Redis fan-out
- PostGIS proximity and Detect → Reveal → Discover field gating
- Drop activation, atomic capacity enforcement, countdowns, and expiry
- live squad creation/join/leave and 2/4 → 3/4 → 4/4 broadcasts
- Drops, Groups, GroupMembers, users/onboarding, and Alembic migration
- JWT registration/login and protected discovery/group endpoints
- Docker startup/migration wiring and repeatable demo seed

Still required in this workstream before production sign-off:

- add the Drop-creation lifecycle method that the business API can call
- run the Docker stack end-to-end and test simultaneous squad joins against a
  real PostgreSQL/Redis instance
- choose a deployment provider, configure production secrets/domain, and run
  the migration in that environment

Cross-team integration still required, but not owned by this workstream:

- connect the teammate-owned business Drop-creation route to the lifecycle
  method
- connect a mobile client to the REST/WebSocket contracts; the browser sandbox
  intentionally uses simulated state
