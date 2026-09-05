# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-06 (business platform / supply-side workstream, `feature/business-platform`)_

## Status

The real-time discovery engine (workstream 1) and the business/supply-side
platform (workstream 2, this branch) are both implemented against the shared
FastAPI scaffold, including the full loop from Drop creation through
redemption and XP award. Gamification depth (ledger, badges, leveling),
notifications, and mobile/dashboard product polish remain open.

## Progress

| Area | State |
|---|---|
| Monorepo and shared WebSocket contracts | Done |
| JWT registration/login and protected endpoints (`user`/`business` audiences) | Done |
| User onboarding preferences and location permission state | Done |
| PostGIS Detect → Reveal engine | Done |
| Persistent per-user Reveal unlock | Done |
| Authenticated WebSocket transport with Redis fan-out/reconnect | Done |
| Squad create/read/join/leave and 2/4 → 3/4 → 4/4 broadcasts | Done |
| Atomic Drop participant-capacity enforcement | Done |
| Discovery schema and initial Alembic migration | Done |
| Business registration/login, separate JWT audience from consumer auth | Done |
| Business Drop CRUD (create/list/publish/pause/resume/cancel) | Done |
| Drop requires an approved business before it can be published | Done |
| Computed (not business-declared) rarity from discount depth + venue capacity/min group size scarcity signals | Done |
| Computed XP reward derived from the same computed rarity (no double-scaling at redemption) | Done |
| `venue_capacity` captured once at business registration; hard ceiling on a Drop's `max_capacity_participants` | Done |
| Business Drop performance and account overview analytics | Done |
| CORS so the dashboard can call the API cross-origin | Done |
| Automatic Drop expiry / scheduled-activation worker (Celery beat) | Done |
| Venue QR sign/verify (HMAC, per-Drop, venue-facing) | Done |
| Redemption flow: squad scans venue QR → check-in → business confirms/rejects → XP awarded | Done |
| Business dashboard: login/register, Overview, Drops, Create Drop, Analytics, Live Queue | Done |
| Dashboard session-expiry handling (401 → clear token → redirect to login) | Done |
| Business moderation endpoints (approve/reject registrations) | Teammate/admin-owned, not yet built |
| XP ledger, `UserStats`, badges, leveling | Not built (flat XP total only; tables exist but unmigrated) |
| Notifications (push, countdown warnings, new-Drop alerts) | Not built |
| Dashboard UI to display/print a Drop's venue QR | Not built |
| Redemption `pending`/`expired` statuses, automatic redemption-expiry sweep | Not built (enum values reserved, unused) |
| Mobile app redemption/QR-scan screen | Not built |

**Verified (2026-09-06):** 101/101 backend tests pass (`pytest -q`); a single
linear Alembic head (`0006_redemptions`); full Docker Compose stack
(postgres+postgis, redis, api, worker, beat, dashboard) built and exercised
live — real business registration/login, Drop creation with computed
rarity/XP preview, a real squad reaching a Drop, a real venue-QR check-in,
a real confirm with an actual XP database mutation, and a reject with
capacity correctly released back to the Drop. Dashboard session-expiry
redirect verified with a forced-expired token; a genuine bad-password login
still shows its normal inline error with no redirect loop.

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
  place at a time as it fills to its maximum; a lost race gets an honest
  "someone else took the last spot" reason, not a generic failure.
- Separate JWT audiences (`user` vs `business`) on the same token
  infrastructure, so a business token can never authenticate a consumer route
  or vice versa.
- Rarity and XP are **platform-computed**, not business-declared: a business
  entering its own rarity/XP would be unverifiable and gameable. Rarity comes
  from `discount_percent` (the one number a business can't easily fake without
  it being visible to the customer) with a scarcity bump from `venue_capacity`
  or `min_group_size`; XP is a fixed table keyed off that same computed rarity.
- `venue_capacity` is captured once at business registration, not left as a
  freely-editable per-Drop field — otherwise a business could inflate rarity
  by declaring a tiny capacity on every Drop.
- The venue QR is per-Drop and venue-facing (printed/displayed once by the
  business), not per-customer or per-squad — one artifact to generate,
  display, and reason about, and squad members simply scan it on arrival.
- A Drop cannot go live until its business is approved — an unverified
  business can create and preview Drops in draft, but `publish` is gated.
- No refresh-token flow yet; a business simply logs in again once its JWT
  expires. The dashboard now acts on that (redirect to login on a 401 from an
  attached token) rather than leaving a dead-end error on screen.

## Next steps

1. Build a dashboard view to display/print a Drop's venue QR (currently only
   the backend can sign/verify one).
2. Decide how deep gamification needs to go before launch — at minimum an XP
   transaction ledger if "why did I get X XP" needs to be answerable; badges
   and leveling are further out.
3. Notifications (push, countdown warnings, new-Drop alerts) — currently
   entirely unbuilt across all workstreams.
4. Business moderation UI/endpoints for approving new registrations (right now
   a new business registers as `BusinessStatus.pending` and publishing is
   gated on `status == active`, but nothing transitions a business to
   `active` outside of direct DB/seed access).
5. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
