# DropBy

Location-based social deal discovery — "Pokémon GO, but you catch experiences." See
`Charlie - DropBy (1).txt` for the full product brief and
`.claude` plan history for the architecture rationale.

## Structure

- `apps/api` — FastAPI backend (modular monolith: discovery/real-time, business/supply, redemption+gamification+notifications modules), PostgreSQL+PostGIS, Redis, Celery.
- `apps/mobile` — working Expo/React Native demo client for the discovery backend.
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
formation, Drop lifecycle controls, capacity enforcement, onboarding, and the
real-time event stream. Press **Run full demo** for an automatic walkthrough of
the complete flow. An internet connection is only needed to load the map
library and street tiles. It is a product demonstration, not an integration
test of the server.

Try the complete flow:

1. Enter the demo account, choose interests, allow location access, and press
   **Sign in & complete setup**.
2. Pan/zoom and click the map to move, or press **Detect · 500 m**.
   Click any Drop marker to inspect what is currently revealed.
3. Press **Reveal · 150 m** to expose the category and rarity.
4. Press **Discover · 50 m** to expose the venue and full offer.
5. Create a squad and add members to move through 2/4, 3/4, and 4/4.
6. Use the lifecycle controls to create, schedule, activate, fill, and expire a
   Drop while watching the event stream.

On Windows, install and open Docker Desktop, then run one command from the
repository root when you want to test the real backend:

```bat
dev.cmd
```

The launcher creates `.env` when needed, builds the discovery backend, runs the
database migration, loads repeatable demo data, and opens Swagger at
<http://localhost:8000/docs>.

```bat
dev.cmd verify
dev.cmd logs
dev.cmd status
dev.cmd stop
```

`dev.cmd verify` runs an isolated integration check against the live services:
PostGIS availability and proximity, two simultaneous squad joins competing for
the same capacity, Redis publish/subscribe, and authenticated WebSocket
delivery. Its temporary records are removed after the check.

Python dependencies are already defined in `apps/api/requirements.txt` and
development dependencies in `apps/api/requirements-dev.txt`; Docker installs
them during the first build. Manual and non-Docker setup is documented in
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md).

To run the real client on a phone, start the backend in one Command Prompt and
Expo in another:

```bat
dev.cmd
mobile.cmd
```

Install Expo Go on the phone, keep it on the same Wi-Fi network, then scan the
QR code shown by `mobile.cmd`. The launcher detects this computer's LAN address
and creates the mobile `.env` automatically. See
[`apps/mobile/README.md`](apps/mobile/README.md) for troubleshooting and the
two-phone live squad walkthrough.

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
- validated Drop creation with draft/scheduled/active lifecycle staging
- live squad creation/join/leave and 2/4 → 3/4 → 4/4 broadcasts
- Drops, Groups, GroupMembers, users/onboarding, and Alembic migration
- JWT registration/login and protected discovery/group endpoints
- Docker startup/migration wiring and repeatable demo seed
- production Compose configuration, non-root containers, health check, and
  production secret validation

The workstream implementation and local integration sign-off are complete.
The live Docker verification passes against PostgreSQL/PostGIS and Redis,
including a real simultaneous-join capacity race and WebSocket delivery.

## Production deployment

The repository includes `infra/docker-compose.production.yml` for an external
PostgreSQL database with PostGIS enabled and an external Redis service. On the
deployment host, create the untracked environment file and replace every
placeholder with the provider's values:

```bat
copy infra\.env.production.example infra\.env.production
docker compose --env-file infra\.env.production -f infra\docker-compose.production.yml up --build -d
```

The migration runs before the API, worker, and scheduler. The API container has
a health check at `/health`, runs as a non-root user, and refuses weak/default
production signing secrets. TLS, domain attachment, and the final environment
values are configured in the selected hosting provider.

External release step still required:

- choose a deployment provider, configure production secrets/domain, and run
  the supplied production stack in that account

Cross-team integration still required, but not owned by this workstream:

- connect the teammate-owned business Drop-creation route to the lifecycle
  method
- the included Expo client now exercises the REST and authenticated WebSocket
  contracts; teammate-owned production mobile polish and redemption remain
  separate workstreams
