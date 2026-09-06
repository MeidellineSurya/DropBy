# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-06 (tightened the check-in radius, persisted
Group.cancelled_reason so it survives more than one response, and gave the
mobile app cancelled/expired squad screens — after removing the business
confirm/reject approval step in favor of auto-confirm plus a dispute window,
reworking check-in from a QR scan to a location claim before that, and
merging the business/supply-side workstream with the independently-built
redemption/gamification/notifications workstream)_

## Status

All three original workstreams are now implemented on the shared FastAPI
scaffold: the real-time discovery engine, the business/supply-side platform,
and redemption + gamification + notifications. The last two were built in
parallel, unaware of each other, and converged on a near-identical
`redemptions` table and check-in design — see "Merging two independent
redemption implementations" below for how that got reconciled. Check-in
itself was later reworked from a QR scan to a location claim — see "Dropping
the venue QR for a location claim" below. Mobile/dashboard product polish
(wiring the newer gamification endpoints into the UI) is what's left.

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
| Check-in as a location claim — no QR at all, just a tight-radius (`check_in_radius_m`, default 10 m) geofence check against the scanning member's last known location | Done |
| Mobile "Check in now" claim button on `SquadScreen`, wired to the check-in endpoint | Done |
| Check-in auto-confirms on the spot (no business approval step); business can dispute a confirmed redemption within a 24h window, releasing capacity but not clawing back XP | Done |
| `Group.cancelled_reason` persisted on the model, set on every path a squad ends without completing (capacity-race loss, a Drop being cancelled, a Drop expiring while forming/ready) | Done |
| Mobile cancelled/expired squad screen showing the persisted reason, with distinct copy for "never found enough people" vs. "was ready but ran out of time" | Done |
| XP ledger (`UserXpTransaction`), badges, leveling, streaks | Done |
| Powerups, level-milestone perks, weekly challenges, territory-exploration bonus | Done |
| Push notifications (FCM) with graceful skip when unconfigured; notification log | Done |
| Business dashboard: login/register, Overview, Drops, Create Drop, Analytics, Live Queue | Done |
| Dashboard session-expiry handling (401 → clear token → redirect to login) | Done |
| Business moderation endpoints (approve/reject registrations) | Not built — only direct DB/seed access sets `Business.status = active` |
| Redemption `pending`/`expired` statuses, automatic redemption-expiry sweep | Not built (enum values reserved, unused) |
| XP clawback on dispute | Not built — disputing a redemption is records-only (releases capacity, flags the record); already-awarded XP, badges, and streak progress are untouched, deliberately, since unwinding those correctly is real added scope |
| Analytics funnel's "Checked in" vs "Completed" distinction | Now redundant for new data — auto-confirm means every redemption hits both at the same instant, so the two stay equal going forward. Left as-is (still meaningful for historical pre-auto-confirm data); not restructured |
| Business dashboard funnel showing cancelled/expired squads | Not built — `business_analytics.py`'s funnel only ever tracked forming/ready/checked_in/completed; a squad that never made it isn't visible there at all, only findable by absence |
| `packages/shared-types` codegen from `ws-contracts` | Not built — the package is a hand-mirrored placeholder (says so in its own file); neither mobile nor the dashboard actually imports from it, both keep separate hand-written types |

**Verified (2026-09-06):** 190/190 backend tests pass (`pytest -q`); a single
linear Alembic head (`0014_group_cancelled_reason`). Live-verified: the
business platform's full loop (registration → Drop creation with computed
rarity/XP → a squad reaching the Drop → check-in that auto-confirms and
awards real XP in the same flow → dispute that releases capacity without
clawing back XP) against the Docker stack, including a claim from ~15m away
correctly rejected by the tightened 10m check-in radius (and one from the
venue still succeeding); a real capacity-race loss whose `cancelled_reason`
was confirmed to survive a later, separate `GET` (not just the one response
that caused it); and the Celery expiry sweep correctly distinguishing a
still-forming squad's reason from a ready-but-too-late squad's, both
persisted the same way. Also verified: the gamification workstream's
mechanics against a live Postgres/Redis/Celery stack (per its own
verification notes, this
caught a real `UserStats` initialization crash and a duplicate `CREATE TYPE`
migration bug that unit
tests didn't surface).

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

## Dropping the venue QR for a location claim

The QR-based check-in above worked, but before building the mobile in-app
scanner for it, we reconsidered whether a QR was needed at all. Check-in is
now a **location claim**: any squad member taps "Check in now" in the app,
the server verifies their last known location is within a tight radius of
the venue (`settings.check_in_radius_m`, default 20 m — separate from and
much tighter than the 100 m Reveal radius used to form the squad in the
first place), and the squad checks in. No per-Drop artifact for the business
to generate, print, or display, and no camera/scanner screen to build.

This is a deliberate tradeoff, not a pure simplification:

- **Lost**: a printed QR additionally proves someone is at the venue's
  specific counter, not just generally nearby, and it resists GPS spoofing
  in a way a location claim alone does not (a location-mocking app can fake
  "I'm near this venue" far more easily than it can fake having scanned a
  code physically printed at a specific business).
- **Kept** (at the time): the actual fraud backstop was never the QR — it
  was the business's Confirm/Reject step on the Live Queue, where staff
  looked at who's actually there. That step was itself removed shortly
  after, in favor of auto-confirm plus a dispute window — see "Auto-confirm
  plus a dispute window" below.
- **Gained**: no printing/signage setup step for a business going live, and
  no mobile camera-scanner UI to build, test, or maintain — a meaningfully
  smaller surface for an early pilot with a handful of hand-onboarded
  venues.

`sign_venue_qr`/`verify_venue_qr`/`get_venue_qr` and the
`GET /redemptions/drops/{id}/qr` endpoint were removed entirely, along with
`QR_SIGNING_SECRET` (one fewer production secret to provision and rotate).
`check_in_group` no longer takes any request body — proximity is the only
check. Revisit if spoofed claims turn out to be a real problem beyond pilot
scale; the geofence radius is a single settings value
(`CHECK_IN_RADIUS_M`) to tighten further if so.

Live-verified: a claim from ~350 m away is rejected
(`403 Move closer to the venue to check in`); a claim from at the venue
succeeds and reaches the business's Live Queue with no QR involved at any
point.

## Auto-confirm plus a dispute window

The Confirm/Reject step above didn't last long either. Capacity is already
first-come-first-served — a squad reserves its spot the moment it becomes
`ready`, before check-in even happens — so a human gate at check-in time
wasn't actually deciding anything about capacity, only whether to trust the
claim. Check-in now **auto-confirms**: the same call that verifies proximity
also marks the Redemption `confirmed` and the Group `completed`, and
enqueues XP in one step. There is no more "awaiting confirm" resting state,
no headcount-correction step, and no Confirm button on the dashboard.

**Correction to the record**: an earlier version of this document (and
something said directly to the user) claimed confirming a redemption didn't
publish any live update, so the app only learned the outcome via manual
refresh. That was wrong — `award_xp_for_redemption_task` (the Celery task
enqueued on confirm) always published `redemption.confirmed` over
`ws:group:{id}`/`ws:user:{id}` and sent a push notification. The real bug
was narrower: the mobile `SquadScreen`'s WS listener only reacted to
`group.*`-prefixed events and silently dropped `redemption.*` ones, so the
push was arriving and being ignored. Fixed alongside this change by widening
that listener's filter (see `apps/mobile/src/types.ts`'s new
`RedemptionEvent` type).

What replaces the human check: a business can **dispute** a confirmed
redemption within `DISPUTE_WINDOW` (24 hours) of confirmation —
`POST /redemptions/{id}/dispute` — flagging it as fraudulent or mistaken.
This is deliberately **records-only**:

- Releases the squad's reserved capacity back to the Drop, so a disputed
  slot doesn't stay wasted.
- Does **not** claw back XP, badges, or streak progress already awarded. A
  correct clawback would need to unwind everything that redemption
  contributed to (badge unlocks, streak state, weekly-challenge progress),
  which isn't built. A disputed redemption is a permanent audit flag on the
  record, not an undo button.

This trades away real-time human verification entirely — check-in was
already the sole verification point once the QR was dropped, and now
there's no verification at check-in time at all, only after-the-fact
recourse. Accepted for the same reason as the QR removal: instant reward
matters more than friction at this stage, and the fraud surface this opens
(a spoofed or bad-faith claim earning real XP with no human ever looking at
it before the reward lands) is a real cost worth watching, not a solved
problem. If abuse becomes real, the lever to pull is either a shorter dispute
window, tightening `check_in_radius_m` further, or reintroducing a pre-award
human gate — not necessarily a full QR reversal.

Live-verified: check-in returns `status: "confirmed"` directly (no separate
confirm call), the Group is `completed` immediately, XP lands via the async
task shortly after, the redemption appears on `/redemptions/queue`, disputing
it releases capacity while leaving the already-awarded XP untouched, and
disputing twice is a no-op.

## Tighter check-in radius, and a real cancelled/expired experience

Two follow-ups, done together because the second depends on a fix the first
prompted a closer look at.

**`check_in_radius_m` dropped from 20 m to 10 m** — a real tightening, not
just a number change: 10 m sits close to the accuracy floor of consumer GPS
in open sky (~3-5 m), so this is close to as tight as it can go before
ordinary GPS drift near buildings starts rejecting genuine claims rather
than catching abuse. Live-verified: a claim from ~15 m away (inside the old
radius, outside the new one) is now correctly rejected; one from the venue
still succeeds.

**`Group.cancelled_reason` was never actually persisted.** Before this, it
only existed as a one-time field on the exact response that caused a
cancellation — `create_group`/`join_group` would compute it and hand it back
to the caller, but never write it to the row. Anyone who found out about the
cancellation any other way (a WS-triggered refresh, checking back later, a
different squad member) got `null`, regardless of what actually happened.
This was already a real gap before mobile had any UI for it — building that
UI is what surfaced it. Fixed by adding the column and setting it at every
place a squad ends without completing:

- A capacity-race loss in `create_group`/`join_group` (already computed a
  reason via `describe_capacity_failure`; now it's assigned to the model
  before commit instead of only threaded through the return value).
- A business cancelling their Drop (`cancel_drop`'s bulk update) — "The
  business cancelled this Drop."
- The Celery expiry sweep (`expire_due`) — split into two update statements
  instead of one so a squad that was still `forming` gets "This Drop ended
  before your squad found enough people" while one that was `ready` gets
  "This Drop ended before your squad could check in." These are genuinely
  different situations (never found people vs. found people but ran out of
  time) and deserve different copy, not one generic "expired."
- Someone leaving a squad that had no one else left in it — "Everyone left
  the squad."

`group_snapshot()` now reads the persisted column directly instead of
accepting an override parameter, so every code path that builds a
`GroupResponse` — the two mutation endpoints, a plain `GET`, and the Celery
sweep's WS broadcast — reports the same, correct reason.

Live-verified: a genuine capacity-race loss (two squads competing for the
last slots on a Drop, reproduced deterministically via sequential requests —
`join_group`'s capacity check runs regardless of the Drop's own status,
unlike `create_group`'s upfront gate, so this doesn't need real concurrency
to trigger) shows its reason on the immediate response *and* on a completely
separate, later `GET`. The expiry sweep was backdated a Drop's `ends_at` and
run directly, confirming a still-forming squad and a ready squad each got
their own distinct, persisted reason.

**Mobile**: `SquadScreen` now has a dedicated cancelled/expired screen —
distinct eyebrow ("SQUAD CANCELLED" / "DROP EXPIRED"), the persisted reason
(with a generic fallback if one somehow isn't set), and a "Back to Discover"
button. Previously there was no such screen at all; a cancelled or expired
squad just kept rendering the assembling/ready layout with no explanation.

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
- `Group.cancelled_reason` is a persisted column, not a one-response-only
  value — every path that ends a squad without completing (capacity race,
  Drop cancelled, Drop expired) sets it on the model before commit, so it
  survives a later, separate read the same way for everyone, not just
  whoever triggered it.
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
- Check-in is a location claim, not a QR scan — a tight-radius geofence
  check against the scanning member's last location, reusing the discovery
  engine's `ST_DWithin` pattern with a 15-minute freshness window — longer
  than the 5-minute assemble window, since walking to the venue after
  assembling legitimately takes longer. See "Dropping the venue QR for a
  location claim" above for the tradeoff this makes.
- One Redemption row per Group (`uq_redemption_group`), created lazily on
  first check-in rather than eagerly when the squad becomes ready.
- Check-in auto-confirms — no business approval gate, no headcount
  correction — with a 24h dispute window as the only recourse, and disputing
  never claws back XP already awarded. See "Auto-confirm plus a dispute
  window" above for the full reasoning and the fraud-surface tradeoff it
  accepts.
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

1. Decide whether the auto-confirm fraud surface (see "Auto-confirm plus a
   dispute window" above) is acceptable past pilot scale, or whether it
   needs a shorter dispute window or a pre-award human gate reintroduced.
   `check_in_radius_m` has already been tightened once (20m → 10m); it's
   close to the GPS accuracy floor, so it's not much more lever left to
   pull on that specific knob.
2. Business moderation UI/endpoints for approving a pending registration —
   right now only direct DB/seed access sets `Business.status = active`.
3. Mobile: wire `GET /gamification/me/stats` and `/me/history` for a
   Collection/Profile screen, and the powerup/perk/weekly-challenge
   endpoints — check-in is now wired; gamification display isn't.
4. Mobile: register a real FCM token via `POST /devices` and subscribe to the
   `territory.bonus_awarded` WS event, so push notifications and territory
   popups actually reach the phone.
5. Mobile: add `cancelled_reason` to `GroupSnapshot` and give `SquadScreen` an
   actual cancelled/expired layout — right now a squad that loses a capacity
   race just looks stuck in the assembling/ready view with no explanation,
   even though the backend has carried the reason since the capacity-race
   fix. (`checked_in`/`completed` now have their own layout, added alongside
   the claim button.)
6. Set up real codegen for `packages/shared-types` from `ws-contracts`, or
   drop the package — right now it's a hand-mirrored placeholder nothing
   actually imports.
7. Run `python -m app.scripts.seed_badges` once against a fresh database so
   badge criteria have real `Badge` rows to unlock against.
8. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
