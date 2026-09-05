# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-05 (verified after pulling the discovery-engine merge)_

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
| PostGIS Detect → Reveal engine | Done |
| Persistent per-user Reveal unlock | Done |
| Authenticated WebSocket transport with Redis fan-out/reconnect | Done |
| Squad create/read/join/leave and 2/4 → 3/4 → 4/4 broadcasts | Done |
| Atomic Drop participant-capacity enforcement | Done |
| Validated Drop creation and lifecycle staging | Done |
| Scheduled activation, countdown, and expiry tasks | Done |
| Discovery schema and initial Alembic migration | Done |
| Docker migration/API/worker/beat startup ordering | Done and live-tested |
| Production Compose, health check, non-root runtime, secret validation | Done; provider release pending |
| Business Drop management and analytics | Teammate-owned scaffold |
| Redemption, gamification, and notifications | Teammate-owned scaffold |
| Mobile and dashboard product UI | Teammate-owned scaffold |

**Verified:** all 18 automated tests pass; lint and Python compilation pass;
the Alembic upgrade renders valid PostgreSQL/PostGIS SQL; and the Docker API,
migration, Celery worker, and scheduler start cleanly. The live integration
verifier confirmed PostGIS 3.4, atomic capacity under simultaneous squad joins,
Redis pub/sub, and authenticated WebSocket delivery through Redis.

**Re-verified locally after pull (2026-09-05):** fresh venv, `pip install -r
requirements-dev.txt`, `pytest -q` — all 18 tests pass.

## Key decisions

- Keep a modular FastAPI monolith so Drop → Group → Redemption → XP can remain
  transactional while each teammate owns separate modules.
- Use PostgreSQL + PostGIS for `ST_DWithin`/`ST_Distance` proximity queries.
- Use Redis pub/sub for cross-process WebSocket fan-out and Celery as the job
  runner; REST discovery continues from PostgreSQL during a Redis outage.
- Keep all state mutations in protected REST endpoints. WebSockets are a
  read-only notification channel and clients re-fetch snapshots after reconnect.
- Every active Drop is detectable regardless of distance. Detect exposes its
  rarity, specific interest type, distance, and required group size.
- The full Reveal unlocks at 100 m. The legacy radius database fields are
  retained for migration compatibility.
- Once revealed, a Drop stays unlocked for that user for the Drop lifetime.
- Reserve participant capacity atomically when a squad becomes ready, then one
  place at a time as it fills to its maximum.
- QR check-in, redemption confirmation, XP, and notifications remain outside
  this workstream.

## Next steps

1. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
2. Let the other workstreams add migrations after `0001_discovery_core` for
   their own tables and implement their existing route/service boundaries.
