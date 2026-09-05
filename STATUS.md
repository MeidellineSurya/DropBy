# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-06 (redemption/gamification/notifications workstream implemented, extended with a full progression system: powerups, level-milestone perks, badge/streak/time-of-day XP bonuses, rarity-set badges, weekly rotating challenges, and territory exploration)_

## Status

The real-time discovery engine (workstream 1) and the redemption,
gamification, and notifications workstream (workstream 3) are both
implemented on the shared FastAPI scaffold. The business/supply, mobile, and
dashboard workstreams remain separate and retain their existing placeholders.

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
| Venue QR sign/verify, geofenced check-in, business confirm, capacity reconciliation | Done |
| XP engine, badge criteria evaluation, streaks, user stats API | Done |
| Drop history API (`GET /gamification/me/history`) and demo Profile screen | Done |
| Push notifications (FCM) with graceful skip when unconfigured; notification log | Done |
| Device registration (`POST /devices`) so a real phone's FCM token reaches `user_devices` | Done |
| Powerup system: 6 types, probabilistic earning, redeem endpoint, inventory cap | Done |
| Level-milestone perk system (every 5 levels): radius/slot-cap/specialization choices | Done |
| Passive XP bonuses: per-badge, per-category/time-specialization-perk, and streak (all additive, none punish absence) | Done |
| Rarity-set-per-category badges ("catch every rarity in one category") | Done |
| Weekly rotating category challenge (pull progress, explicit claim) | Done |
| New-territory flat-XP bonus for a never-before-pinged grid cell | Done |
| Redemption/gamification migrations (`0003`–`0008`) | Done |
| Browser-only demo (`demo.cmd`) mirrors the full progression system: check-in/confirm/XP/badges, powerups, level-milestone perks (incl. category/time-of-day picker), streak bonus/grace/shield, weekly challenge, territory bonus | Done |
| Mobile and dashboard product UI | Teammate-owned scaffold |

**Verified:** all 97 automated tests pass (18 discovery + 79 new redemption/
gamification tests); ruff lint is clean; every Alembic migration through
`0008_progression_extras` renders valid PostgreSQL/PostGIS SQL. Beyond unit
tests, every mechanic below was additionally exercised live against a running
Docker stack (real Postgres/Redis/Celery, not mocks) with assertions on the
actual
database state — this caught one real bug (a `UserStats` initialization crash)
and one real migration bug (a duplicate `CREATE TYPE`) that unit tests alone
did not surface.

**Re-verified locally after pull (2026-09-05):** fresh venv, `pip install -r
requirements-dev.txt`, `pytest -q` — all 18 tests pass (prior to the
redemption/gamification/notifications workstream landing).

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
- The venue QR is self-verifying (HMAC over drop_id/business_id/iat/nonce), so
  re-fetching it any number of times never invalidates an already-printed
  copy — no separate QR-issuance table or activation-time hook needed.
- Check-in requires both the QR (proves the venue) and a geofence check
  against the scanning member's last location (proves the person), reusing
  the same `ST_DWithin` pattern as the assemble-a-squad check but with a
  15-minute freshness window instead of 5, since walking to the venue after
  assembling legitimately takes longer than assembling itself.
- One Redemption row per Group (`uq_redemption_group`), created lazily on
  first check-in rather than eagerly when the squad becomes ready — simpler,
  and avoids the discovery module's squad_state.py needing to import into
  the redemption module.
- XP = `xp_reward_base * rarity_multiplier`, plus a flat 30% squad bonus when
  the Drop was completed as a group of 2+ — mirrors the brief's own
  +250/+80 XP example. Leveling is a flat 500 XP/level.
- There's no city/region model yet, so "exploration progress" is tracked as
  distinct coarse lat/lng grid cells per user rather than named cities —
  swap for real geo-boundaries if/when that data exists.
- `get_current_business` (core/deps.py) decodes the same generic JWT scheme
  as `get_current_user`, just looked up against `businesses` instead of
  `users` — it works the moment the business/supply module mints a token via
  the existing `create_access_token(str(business.id))`, with no changes
  needed on this side.
- Push notifications degrade to a logged-but-skipped `NotificationLog` row
  when Firebase isn't configured (dev/test), so missing FCM credentials never
  fail a check-in, confirm, or XP-award flow.
- award_xp_for_redemption is idempotent per redemption_id (guards on an
  existing `UserXpTransaction`), safe for Celery to retry.
- Powerups (`extra_time`, `xp_boost`, `bigger_reveal`, `double_or_nothing`,
  `extra_slot`, `streak_shield`) are earned probabilistically from Rare+
  Drops (50%/75%/100% by rarity, legendary has a further chance of a 2nd) —
  unlike badges/XP, a Rare completion does not guarantee one. Held-powerup
  inventory is capped (base 3, +1 per `extra_powerup_slot` perk); a roll that
  would exceed the cap is simply not granted rather than queued or wasted
  some other way.
- Every level-based or perk-based bonus in this system is purely additive:
  nothing a user already has is ever reduced for being away, leveling
  slowly, or making a "wrong" choice. This was a deliberate call after
  rejecting an XP-decay-for-inactivity design as functionally a loss-aversion
  mechanic — the brief explicitly asks to avoid manipulative retention
  mechanics, and taking away earned progress for absence is that pattern
  even when it's framed as "your level protects you."
- Two features that sounded simple turned out to need real architecture
  investigation before implementing, both documented in code comments where
  they land: (1) Detect has no distance cutoff at all in this codebase (STATUS
  above), so a "bigger Detect radius" perk would be a no-op — the actual lever
  is Reveal's 100 m radius (`bigger_radius` perk/`bigger_reveal` powerup) and,
  separately, the "Rare+ Drop nearby" push alert's own radius
  (`services/notifications.py::NOTIFICATION_RADIUS_BONUS_PER_LEVEL_M`,
  automatic per level, no perk needed). (2) The expiry sweep
  (`drop_lifecycle.expire_due`) expires a `forming`/`ready` Group purely off
  its Drop's `ends_at`, never consulting the Group's own `expires_at` — so a
  squad-scoped "protect my squad from the Drop's timer" powerup is not
  achievable without either touching that sweep (breaks the
  additive-only-to-other-modules rule) or extending the Drop for everyone
  (a business-facing decision, not a per-user one). The powerup that shipped
  (`extra_time`) instead does the thing that field actually controls: extends
  how long a still-forming squad can keep recruiting.
- Reveal-radius bonuses compose additively as *extra* fraction over 1.0, not
  multiplicatively: permanent `bigger_radius` perks (+15%/pick) and the
  temporary `bigger_reveal` powerup (+50% while active) add their bonus
  fractions together, so having both at once is stronger than either alone
  rather than one overriding the other.
- Badge/specialization/streak XP bonuses are deliberately modest (1-2% per
  badge, 5% per specialization perk pick, capped at +10% for streaks) to
  match today's milestone-style badges — a much harder future badge (e.g. a
  full-area completionist) is where a bigger number would belong, not a
  reason to inflate these. The rarity-set-per-category badges ("catch a
  Common through Legendary in one category") are that harder badge, and
  correspondingly earn 8%.
- The "new territory" bonus is keyed off the user's own ping location
  (`UserExploredCell`, a new grid-cell table), not off which Drops get
  detected — Detect has no distance limit (see above), so a Drop can be
  "detected" from anywhere the instant it activates; only a ping's actual
  coordinates say anything about where the user has physically been.
- Weekly challenge progress is computed by reading `drop_view_events` at
  request time (pull), not pushed automatically the moment a qualifying
  Reveal happens — this needed zero changes to the discovery engine's ping
  hot path. Completing it requires an explicit `POST
  .../challenges/weekly/claim`, same pattern as `redeem_powerup`/
  `choose_perk`: the system tells you what's available, you decide when to
  act on it.
- Time-of-day specialization buckets ("night"/"morning",
  `NIGHT_WINDOW_LOCAL_HOURS`/`MORNING_WINDOW_LOCAL_HOURS`) use the redeeming
  user's *local* hour, not UTC — there is still no timezone field anywhere in
  the schema, so local hour is approximated from the checked-in-at venue's
  longitude (`approximate_utc_offset_hours`: 15 degrees per hour of solar
  time, no DST/political-border awareness) rather than needing one. This
  reuses data the check-in geofence already requires (the scanning member has
  to be physically at the venue), so it needed no new field, dependency, or
  changes to another module's onboarding flow.
- `compute_stage_for_ping`'s return type and the `LocationPingResponse`
  schema were deliberately left untouched for the territory bonus — it's
  announced over the same WS channel that stage-change events already use
  (`ws:user:{id}`, a new `territory.bonus_awarded` event), not returned
  inline, so this needed no changes to drops.py or its response schema.

- Drop history (`GET /gamification/me/history`) reads existing
  `UserXpTransaction` rows tagged `drop_completed` joined out to their
  `Redemption`/`Drop`/`Business` — no new table. Badge/streak/specialization
  bonuses are already folded into that transaction's `amount` (see the XP
  award decision above), so each row is exactly one completed Drop with its
  final awarded XP, not a raw ledger line that would need re-deriving bonuses
  after the fact.

## Next steps

1. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
2. Business/supply workstream: implement Drop creation/listing/cancel and
   business login (`create_access_token(str(business.id))` will then work
   automatically with this workstream's `get_current_business`-gated
   endpoints — `/redemptions/queue`, `/redemptions/drops/{id}/qr`, and
   `/redemptions/{id}/confirm`).
3. Run `python -m app.scripts.seed_badges` once a database exists so badge
   criteria have real Badge rows to unlock against.
4. Mobile/dashboard: wire the Explore→Assemble→Check-in→Confirm loop to
   `POST /groups/{id}/checkin`, the business queue/QR/confirm endpoints,
   `GET /gamification/me/stats` for the Collection/Profile screens (now also
   carrying `powerups`, `powerup_cap`, `pending_perk_choices`, `perks`,
   `category_rarity_sets`, and `territory_cells_explored`), `POST
   /gamification/powerups/{id}/redeem`, `POST /gamification/perks/choose`,
   and `GET`/`POST /gamification/challenges/weekly` (+`/claim`) for the
   weekly-challenge card.
5. Mobile: once it has a real FCM token, call `POST /devices` with it so push
   notifications actually reach the phone — right now `user_devices` has no
   way to get populated except this endpoint.
6. Mobile: subscribe to the `territory.bonus_awarded` WS event on
   `ws:user:{id}` to show a "New area discovered! +10 XP" popup the moment it
   fires — it's a push-style event, not part of any REST response body.
