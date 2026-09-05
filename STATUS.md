# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-05_

## Status

The real-time discovery engine (workstream 1) is implemented on the shared
FastAPI scaffold. The business/supply, redemption, gamification,
notifications, mobile, and dashboard workstreams remain separate and retain
their existing placeholders.

## Progress

| Area | State |
|---|---|
| Monorepo and shared WebSocket contracts | Done |
| JWT registration/login and protected endpoints | Done |
| User onboarding preferences and location permission state | Done |
| PostGIS Detect → Reveal → Discover engine | Done |
| Persistent per-user Discover unlock | Done |
| Authenticated WebSocket transport with Redis fan-out/reconnect | Done |
| Squad create/read/join/leave and 2/4 → 3/4 → 4/4 broadcasts | Done |
| Atomic Drop participant-capacity enforcement | Done |
| Scheduled activation, countdown, and expiry tasks | Done |
| Discovery schema and initial Alembic migration | Done |
| Docker migration/API/worker/beat startup ordering | Done; full Docker smoke test still needed |
| Business Drop management and analytics | Teammate-owned scaffold |
| Redemption, gamification, and notifications | Teammate-owned scaffold |
| Mobile and dashboard product UI | Teammate-owned scaffold |

**Verified:** the FastAPI app imports with 17 documented REST paths, the
Alembic upgrade renders valid PostgreSQL/PostGIS SQL, auth hashing works, lint
passes on discovery-owned files, and all 7 tests pass. Docker is not installed
on the current machine, so the full container stack has not been executed here.

## Key decisions

- Keep a modular FastAPI monolith so Drop → Group → Redemption → XP can remain
  transactional while each teammate owns separate modules.
- Use PostgreSQL + PostGIS for `ST_DWithin`/`ST_Distance` proximity queries.
- Use Redis pub/sub for cross-process WebSocket fan-out and Celery as the job
  runner; REST discovery continues from PostgreSQL during a Redis outage.
- Keep all state mutations in protected REST endpoints. WebSockets are a
  read-only notification channel and clients re-fetch snapshots after reconnect.
- Detect defaults to 700 m, Reveal to 180 m, and Discover to 60 m.
- Once discovered, a Drop stays unlocked for that user for the Drop lifetime.
- Reserve participant capacity atomically when a squad becomes ready, then one
  place at a time as it fills to its maximum.
- QR check-in, redemption confirmation, XP, and notifications remain outside
  this workstream.

## Next steps

1. Install Docker Desktop and run the full-stack smoke test documented in
   `apps/api/DISCOVERY_ENGINE.md`.
2. Exercise concurrent squad joins against PostgreSQL to verify capacity races
   under real transactions.
3. Let the other workstreams add migrations after `0001_discovery_core` for
   their own tables and implement their existing route/service boundaries.
