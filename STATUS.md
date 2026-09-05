# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-05_

## Status

**Skeleton complete, not yet functional.** Repository structure, database schema,
API/WebSocket route surface, and Celery task signatures exist for all three
workstreams. Business logic is stubbed with `NotImplementedError` — nothing
end-to-end works yet (no auth, no Drop creation, no proximity detection, no
redemption flow). Nothing has been committed to git.

## Progress

| Area | State |
|---|---|
| Repo structure (monorepo: `apps/api`, `apps/mobile`, `apps/dashboard`, `packages/ws-contracts`, `packages/shared-types`) | Done |
| Database models (users, businesses, drops, groups, redemptions, gamification, notifications) | Done — schema defined, no migrations generated yet |
| REST route stubs (auth, drops, groups, business drops/analytics, redemptions, gamification) | Done — routes exist, all raise `NotImplementedError` |
| WebSocket transport (`ConnectionManager` + Redis pub/sub bridge) | Done — connects/dispatches; topic subscription on connect is still a `TODO` (hardcoded placeholder user) |
| WS event contract (`packages/ws-contracts` + `packages/shared-types`) | Done |
| QR sign/verify (`services/redemption.py`) | Done — the only fully implemented business logic so far |
| Proximity engine, Drop/Group state machines, XP/gamification engine, notification dispatch | Not started — stubs only |
| Alembic migrations | Scaffolded, no migrations generated (`versions/` empty) |
| Dashboard (React+Vite) | Scaffolded, `npm install`ed, routes wired (Login/Create Drop/Live Queue/Analytics), pages are placeholders |
| Mobile (React Native) | JS-layer skeleton only — native `ios`/`android` projects not generated |
| Docker Compose (postgres+postgis, redis, api, worker, beat, dashboard) | Written, not yet run end-to-end |
| Tests | One passing smoke test (`GET /health`) |

**Verified working:** API dependencies install cleanly; `app.main:app` imports
with 20 routes registered; `pytest` passes; dashboard `tsc -b` type-checks clean.

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Mobile platform | React Native | Needs real background GPS + push notifications for the core detect/reveal/discover loop — a PWA's location/push support is too weak for this. |
| Backend architecture | **Modular monolith** (one FastAPI service, three internal modules), not 3 microservices | Drop → Group → Redemption → XP is one tightly-coupled state machine (capacity checks, redemption confirms, XP awards need to be atomic). Splitting into real services would force distributed-transaction handling (sagas, outbox tables) for no benefit at this scale, while still letting 3 people work in parallel on separate files/routers. |
| Backend framework | FastAPI | Native async + WebSocket support + Pydantic validation; pairs naturally with Celery/Redis. |
| Real-time transport | Raw WebSockets + Redis pub/sub (not Socket.IO, not a managed service like Ably/Pusher) | Redis is already in the stack for Celery; full control over reveal-stage/squad broadcast logic without a vendor dependency for the app's core mechanic. |
| Database | PostgreSQL + PostGIS | Needed for accurate geospatial proximity queries (`ST_DWithin`/`ST_Distance`) driving the Detect/Reveal/Discover stages. |
| Background jobs | Celery + Redis | Notification dispatch, Drop expiry sweeps, XP calculation, scheduled countdown warnings. |
| Business dashboard framework | React + Vite (not Next.js) | Authenticated internal tool with no SEO/SSR requirement; shares React knowledge with the mobile app. |
| Check-in/redemption method | QR code (venue-facing, per-Drop, not per-user) scanned in-app | Rejected GPS geofencing (indoor/accuracy issues) and staff-entered codes (friction, error-prone); a single venue QR + one business "Confirm" tap balances low friction with fraud resistance. |
| MVP scope | Full three-workstream build (discovery engine, business/supply, redemption+gamification+notifications), not a trimmed "core loop only" MVP | Explicit user direction — brief itself frames the three areas as parallel-buildable workstreams. |
| Deferred features | Combo Drops, City Events, persistent Social Squads, full Open Squads | Noted in the brief as "longer-term features"; out of scope for this build. |
| Discover-stage distance threshold | 60m default | The brief specifies Detect (~700m) and Reveal (~180m) but not a number for "close range" Discover — 60m is a placeholder default, tunable later. |
| Discover persistence rule | Once a user reaches Discover for a Drop, it stays unlocked for that Drop's remaining lifetime (Redis-cached) | Without this, stepping away to gather a squad would re-hide the offer — directly punishing the core "assemble a squad" behavior the product exists to encourage. |

Full architecture detail (schemas, WS event catalog, state machines, build
phasing) lives in the implementation plan:
`~/.claude/plans/using-this-brief-draft-plan-eventual-tarjan.md`.

## Next Steps

1. Generate the first Alembic migration from the models in `apps/api/app/models/`.
2. Implement `services/proximity.py` (stage engine) and `services/drop_lifecycle.py` (capacity reservation) — these unblock the discovery module end-to-end.
3. Wire real JWT validation into the `/ws/live` endpoint (currently a hardcoded placeholder user).
4. Stand up `docker compose -f infra/docker-compose.yml up --build` and confirm all services start together.
5. Generate native `ios`/`android` projects for `apps/mobile` when ready to run on device/simulator.
