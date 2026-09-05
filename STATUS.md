# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-06 (merged the business/supply-side workstream with the
independently-built redemption/gamification/notifications workstream)_

## Status

All three original workstreams are now implemented on the shared FastAPI
scaffold: the real-time discovery engine, the business/supply-side platform,
and redemption + gamification + notifications. The last two were built in
parallel, unaware of each other, and converged on a near-identical
`redemptions` table and QR design — see "Merging two independent redemption
implementations" below for how that got reconciled. Mobile/dashboard product
polish (wiring the newer gamification endpoints into the UI) is what's left.

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
| Drop requires an approved (`active`) business before it can be published | Done |
| Computed (not business-declared) rarity from discount depth + venue capacity/min group size scarcity signals | Done |
| Computed XP reward derived from that same computed rarity | Done |
| `venue_capacity` captured once at business registration; hard ceiling on a Drop's `max_capacity_participants` | Done |
| Business Drop performance and account overview analytics | Done |
| CORS so the dashboard can call the API cross-origin | Done |
| Automatic Drop expiry / scheduled-activation worker (Celery beat) | Done |
| Venue QR sign/verify (HMAC, per-Drop, venue-facing), fetchable via `GET /redemptions/drops/{id}/qr` | Done |
| Check-in requires both the QR and a geofence check against the scanning member's last known location | Done |
| Redemption queue, confirm, and reject, with capacity correctly reconciled either way | Done |
| XP ledger (`UserXpTransaction`), badges, leveling, streaks | Done |
| Powerups, level-milestone perks, weekly challenges, territory-exploration bonus | Done |
| Push notifications (FCM) with graceful skip when unconfigured; notification log | Done |
| Business dashboard: login/register, Overview, Drops, Create Drop, Analytics, Live Queue | Done |
| Dashboard session-expiry handling (401 → clear token → redirect to login) | Done |
| Business moderation endpoints (approve/reject registrations) | Not built — only direct DB/seed access sets `Business.status = active` |
| Dashboard UI to display/print a Drop's venue QR | Not built (backend endpoint exists, nothing renders it) |
| Mobile app redemption/QR-scan screen | Not built |
| Redemption `pending`/`expired` statuses, automatic redemption-expiry sweep | Not built (enum values reserved, unused) |
| Mobile UI for a cancelled/expired/completed squad | Not built — `SquadScreen` always renders the assembling/ready layout regardless of status, and the mobile `GroupSnapshot` type is missing `cancelled_reason` (the backend has carried it since the capacity-race fix; `packages/shared-types` already models it as `reason`) |
| `packages/shared-types` codegen from `ws-contracts` | Not built — the package is a hand-mirrored placeholder (says so in its own file); neither mobile nor the dashboard actually imports from it, both keep separate hand-written types |

**Verified (2026-09-06):** 177/177 backend tests pass (`pytest -q`) after the
merge; a single linear Alembic head (`0011_business_venue_capacity`).
Live-verified separately before merging: the business platform's full loop
(registration → Drop creation with computed rarity/XP → a squad reaching the
Drop → venue-QR check-in → confirm with an actual XP mutation → reject with
capacity released) against the Docker stack, and the gamification
workstream's mechanics against a live Postgres/Redis/Celery stack (per its
own verification notes, this caught a real `UserStats` initialization crash
and a duplicate `CREATE TYPE` migration bug that unit tests didn't surface).

## Merging two independent redemption implementations

A teammate built the full redemption/gamification/notifications workstream on
`main` at the same time this branch built redemption/gamification for the
business platform — neither aware of the other. Both converged on
essentially the same `redemptions` table (same columns, the same
`uq_redemption_group` unique constraint name) and the same venue-QR design,
which made reconciling them far more tractable than it could have been.
`main`'s version was the deeper implementation (geofenced check-in, a full XP
ledger instead of a flat total, badges, powerups, streaks, weekly challenges,
notifications, and a dashboard-ready `GET /redemptions/drops/{id}/qr`
endpoint this branch hadn't built yet), so it was kept as the base. What this
branch had that `main` didn't:

- a **reject** endpoint (`POST /redemptions/{id}/reject`) — `main`'s version
  had no way to decline a mistaken or fraudulent check-in; a rejected squad
  would have stayed stuck as `checked_in` forever with its capacity never
  released. Ported over onto `main`'s service, alongside the confirm path.
- `get_current_business` on a **separate JWT audience** from consumer auth —
  `main`'s version was still the original skeleton's stub, authenticating a
  business token exactly like a user token. Kept this branch's version;
  nothing on `main`'s side depended on the stub behavior (its tests call the
  service functions directly, not through real minted tokens).
- `drop_title`, `member_count`, and `xp_reward_base` on `RedemptionResponse`,
  for the dashboard's queue cards — added to `main`'s schema and assembled in
  a new `services/redemption.build_response()` helper, since none of those
  are columns on `Redemption` itself.

A live end-to-end check of the merged flow (business login → create/publish a
Drop → check in → confirm) caught a genuine bug the two implementations'
convergence produced: `main`'s `award_xp_for_redemption` computed
`xp_for_rarity(drop.xp_reward_base, drop.rarity)` — correct under `main`'s own
assumption that `xp_reward_base` is a flat, business-set number multiplied by
a rarity factor at redemption time. But on this branch `xp_reward_base` is
*already* the final rarity-scaled value, computed once at Drop creation
(`drop_lifecycle.compute_xp_reward`) specifically so a business can't declare
it directly. Merging both unchanged silently double-counted XP by the rarity
multiplier a second time (confirmed live: a Drop with `xp_reward_base=20`
awarded +30 XP instead of +20). Fixed by removing `xp_for_rarity`/
`RARITY_XP_MULTIPLIER` and using `drop.xp_reward_base` as-is; re-verified live
that a solo squad on that same Drop now awards exactly +20.

Both branches also independently created migrations `0003` through `0006` off
the same parent (`0002_detect_interest_tag`). `main`'s redemption/
gamification chain (`0003_redemption_gamification` through
`0008_progression_extras`) was kept as-is; this branch's three migrations
(business indexes, `discount_percent`, `venue_capacity`) were rebased to
follow it and renumbered `0009`–`0011`. This branch's own `0006_redemptions`
migration was dropped entirely — `main`'s `0003_redemption_gamification`
already creates that exact table.

The dashboard's Live Queue page was repointed from this branch's old
`/business/redemptions` routes to `main`'s `/redemptions/*` routes
accordingly.

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
  from `discount_percent` with a scarcity bump from `venue_capacity` or
  `min_group_size`; XP is a fixed table keyed off that same computed rarity.
- `venue_capacity` is captured once at business registration, not left as a
  freely-editable per-Drop field — otherwise a business could inflate rarity
  by declaring a tiny capacity on every Drop.
- The venue QR is per-Drop and venue-facing (printed/displayed once by the
  business, self-verifying so re-fetching it never invalidates an
  already-printed copy), not per-customer or per-squad.
- Check-in requires both the QR (proves the venue) and a geofence check
  against the scanning member's last location (proves the person), reusing
  the discovery engine's `ST_DWithin` pattern with a 15-minute freshness
  window — longer than the 5-minute assemble window, since walking to the
  venue after assembling legitimately takes longer.
- One Redemption row per Group (`uq_redemption_group`), created lazily on
  first check-in rather than eagerly when the squad becomes ready.
- A Drop cannot go live until its business is `active` — an unverified
  business can create and preview Drops in draft, but publish is gated.
- No refresh-token flow yet; a business simply logs in again once its JWT
  expires. The dashboard acts on that (redirect to login on a 401 from an
  attached token) rather than leaving a dead-end error on screen.
- XP is a full ledger (`UserXpTransaction`) plus a flat squad-completion
  bonus, badges, powerups, level-milestone perks, streaks, and a weekly
  challenge — all additive, deliberately never punishing absence or a "wrong"
  choice (an XP-decay-for-inactivity design was considered and rejected as a
  loss-aversion mechanic).
- There's no city/region model yet, so exploration progress is tracked as
  coarse lat/lng grid cells per user rather than named cities.

## Next steps

1. Build a dashboard view to display/print a Drop's venue QR (backend
   endpoint exists: `GET /redemptions/drops/{id}/qr`).
2. Business moderation UI/endpoints for approving a pending registration —
   right now only direct DB/seed access sets `Business.status = active`.
3. Mobile: wire the check-in/confirm loop, `GET /gamification/me/stats` and
   `/me/history` for a Collection/Profile screen, and the powerup/perk/weekly
   -challenge endpoints — the mobile app currently only exercises discovery.
4. Mobile: register a real FCM token via `POST /devices` and subscribe to the
   `territory.bonus_awarded` WS event, so push notifications and territory
   popups actually reach the phone.
5. Mobile: add `cancelled_reason` to `GroupSnapshot` and give `SquadScreen` an
   actual cancelled/expired/completed layout — right now a squad that loses a
   capacity race just looks stuck in the assembling/ready view with no
   explanation, even though the backend has carried the reason since the
   capacity-race fix.
6. Set up real codegen for `packages/shared-types` from `ws-contracts`, or
   drop the package — right now it's a hand-mirrored placeholder nothing
   actually imports.
7. Run `python -m app.scripts.seed_badges` once against a fresh database so
   badge criteria have real `Badge` rows to unlock against.
8. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
