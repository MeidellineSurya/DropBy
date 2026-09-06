# DropBy — Status, Progress & Decisions

_Last updated: 2026-09-06 (renamed confusing dashboard pages — "Redemptions"
to "Redemption Log", "Drops" to "Manage Drops", and its file from the
stale, actively-misleading `LiveQueuePage.tsx` — see "Renamed dashboard
pages for clarity" below; before that, fixed a real bug the user found by
actually opening the Scan page: the camera preview was never visible,
because the video container was hidden while `html5-qrcode` measured it —
see "The camera preview was never visible" below; before that, restyled the
business dashboard to match the mobile app's real design system —
paper/ink/pink/green palette, Lilita One/Candal fonts, per-tier rarity
colours, an ink Sidebar mirroring the mobile bottom nav — see "Restyling
the dashboard to match the mobile app" below; before that, a cross-cutting
consistency audit after the
squad-QR-scan redesign found and fixed three real gaps it had introduced: a
dashboard analytics stat permanently stuck at zero, duplicate push
notifications on a rescan, and the business dashboard never actually
receiving a scan live over WebSocket — see "Consistency audit after the
squad-QR-scan redesign" below; before that, reworked check-in a third
time: each squad now generates its own signed QR once ready, and the
business scans it — the scan
itself is both the verification and the confirmation, closing the fraud gap
the auto-confirm-by-location-claim design opened; before that, made
discovery notification-driven — every user with a known location is
notified when a Drop activates, not just people already nearby — after
tightening the check-in radius, persisting Group.cancelled_reason so it
survives more than one response, and giving the mobile app cancelled/expired
squad screens; before that, removing the business confirm/reject approval
step in favor of auto-confirm plus a dispute window, reworking check-in from
a QR scan to a location claim, and merging the business/supply-side
workstream with the independently-built redemption/gamification/
notifications workstream)_

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
| Check-in is a squad-generated, signed QR scanned by the business — `GET /groups/{id}/qr` (member-facing) and `POST /redemptions/scan` (business-facing); no GPS/location check at all | Done |
| Mobile `SquadScreen` shows a black-on-white QR once the squad is `ready`, replacing the old "Check in now" claim button | Done |
| The scan itself both verifies (proves physical presence in front of staff) and confirms (awards XP) in one action — no business approval step, no headcount correction; business can still dispute a confirmed redemption within a 24h window, releasing capacity but not clawing back XP | Done |
| Business dashboard camera-based Scan page (`/scan`, `html5-qrcode`) to confirm a squad's code, with secure-context/permission-denied/no-camera detection, a camera picker for devices with more than one, and a manual code-entry fallback | Done — user-reported the camera feed wasn't actually visible; found and fixed a real bug (see "The camera preview was never visible" below) |
| `Group.cancelled_reason` persisted on the model, set on every path a squad ends without completing (capacity-race loss, a Drop being cancelled, a Drop expiring while forming/ready) | Done |
| Mobile cancelled/expired squad screen showing the persisted reason, with distinct copy for "never found enough people" vs. "was ready but ran out of time" | Done |
| XP ledger (`UserXpTransaction`), badges, leveling, streaks | Done |
| Powerups, level-milestone perks, weekly challenges, territory-exploration bonus | Done |
| Push notifications (FCM) with graceful skip when unconfigured; notification log | Done |
| Notification-driven discovery: every user with a known location is notified when any Drop activates (not just Rare+, not gated by proximity/freshness); notification shows category + distance only | Done |
| Immediate-publish Drops (`create_drop(publish=True)` / `publish_drop`) trigger the new-Drop notification directly, not just the scheduled→active sweep | Done |
| Business dashboard: login/register, Overview, Manage Drops, Create Drop, Scan to confirm, Redemption Log, Analytics | Done |
| Create Drop's min/max squad size are range sliders (2–10) instead of unbounded number inputs — the backend schema still allows up to 100 (unchanged), the slider just keeps the common case fast to set and out of unrealistic territory | Done |
| Dashboard session-expiry handling (401 → clear token → redirect to login) | Done |
| Dashboard restyled to match the mobile app's actual design system — paper/ink/pink/green palette, Lilita One/Candal fonts, per-tier rarity colours, an ink-panelled Sidebar mirroring the mobile bottom nav — replacing a placeholder dark theme that predated the mobile redesign | Done |
| Business moderation endpoints (approve/reject registrations) | Not built — only direct DB/seed access sets `Business.status = active` |
| Redemption `pending`/`expired` statuses, automatic redemption-expiry sweep | Not built (enum values reserved, unused) |
| XP clawback on dispute | Not built — disputing a redemption is records-only (releases capacity, flags the record); already-awarded XP, badges, and streak progress are untouched, deliberately, since unwinding those correctly is real added scope |
| Analytics funnel's "Checked in" bucket | Removed — see "Consistency audit after the squad-QR-scan redesign" below. It's not a stale distinction anymore, it was reporting a permanent, misleading zero |
| Business dashboard funnel showing cancelled/expired squads | Not built — `business_analytics.py`'s funnel only ever tracked forming/ready/checked_in/completed; a squad that never made it isn't visible there at all, only findable by absence |
| `packages/shared-types` codegen from `ws-contracts` | Not built — the package is a hand-mirrored placeholder (says so in its own file); neither mobile nor the dashboard actually imports from it, both keep separate hand-written types |

**Verified (2026-09-06):** 198/198 backend tests pass (`pytest -q`); a single
linear Alembic head (`0014_group_cancelled_reason` — the squad-QR-scan
redesign below needed no schema change, only a reused `confirmed_by` column
and a reintroduced config secret). Live-verified: the
business platform's full loop (registration → Drop creation with computed
rarity/XP → a squad reaching the Drop → check-in that auto-confirms and
awards real XP in the same flow → dispute that releases capacity without
clawing back XP) against the Docker stack, including a claim from ~15m away
correctly rejected by the tightened 10m check-in radius (and one from the
venue still succeeding); a real capacity-race loss whose `cancelled_reason`
was confirmed to survive a later, separate `GET` (not just the one response
that caused it); the Celery expiry sweep correctly distinguishing a
still-forming squad's reason from a ready-but-too-late squad's, both
persisted the same way; and notification-driven discovery — a Common-rarity
Drop still notifies (previously silently skipped), a user ~5km away gets
notified with the correct distance (no proximity gate), a user with zero
location history is correctly excluded, and an immediately-published Drop
fires the notification without needing the scheduled sweep. Also verified:
the gamification workstream's mechanics against a live Postgres/Redis/Celery
stack (per its own verification notes, this caught a real `UserStats`
initialization crash and a duplicate `CREATE TYPE` migration bug that unit
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

## Notification-driven discovery

Discovery used to be purely proximity-triggered: the only way to ever hear
about a Drop was to already be within its Detect radius (700 m + a
level-scaled bonus) with a location ping in the last 30 minutes, at the
exact moment a ping happened to land. That's now a secondary path. Every
user with a known location gets a push notification the instant a Drop goes
active, regardless of distance or how stale their last ping is — the
notification IS the primary discovery mechanism now, not a Rare+-only bonus
on top of proximity.

What changed:

- `find_nearby_users_for_drop` (radius + 30-minute freshness gate,
  Rare+-only) replaced with `find_users_to_notify_for_drop` — every user
  with *any* known location, no radius or freshness filter, paired with
  their distance to the Drop. The only reason to exclude someone at all is
  that a distance can't be shown for a user who has never pinged once.
- `notify_users_of_new_drop` fires for **every** Drop now, not just Rare or
  better — under the old model, Common/Uncommon staying silent was a
  deliberate choice ("exploration, not notification spam, drives
  discovery" — see the git history on this function). That reasoning
  doesn't hold once notification is the only way most people ever find out
  a Drop exists at all.
- The notification body is deliberately thin: category and distance,
  rounded to the nearest 50 m below 1 km — matching the same anti-
  triangulation rounding Detect already uses in-app
  (`proximity.snapshot_for`) — then whole-km above that. Never the title,
  offer, or business name; those still require actually reaching Reveal
  range (100 m).
- **Fixed a real gap this surfaced**: neither `create_drop` (with
  `publish=True` and a `starts_at` already in the past) nor the manual
  `publish_drop` endpoint ever enqueued this notification — only the
  periodic `scheduled → active` sweep did. That was a minor miss under the
  old proximity-first model; under this one it meant the single most common
  real case — a business publishing a Drop that's immediately live —
  notified nobody at all. Both routes now enqueue
  `notify_users_of_new_drop` directly when the Drop comes back `active`.

Not changed: the in-app Detect/Reveal ping mechanic itself
(`services/proximity.py`) is untouched — a user who's already walking
around still detects/reveals Drops exactly as before. The notification is
an additional channel that gets people who *aren't* already nearby to find
out a Drop exists at all, not a replacement for the walk-closer-to-reveal
loop once they act on it.

Live-verified: a Common-rarity Drop (previously silently skipped) triggers
notifications; a user ~5 km away gets notified with the correct distance
(no proximity gate); a user with zero location history is correctly
excluded (no distance to show); and a Drop created directly into `active`
status (immediate publish, not via the scheduled sweep) fires the
notification too.

## Business scans a squad-generated QR

Auto-confirm-by-location-claim (above) had a real hole: nothing about it
actually proved a *staff member* saw the squad. A location claim only proves
a phone's GPS says it's near the venue — spoofable, and even genuine, it
never puts a human in the loop at all. Check-in is now: each squad, once
`ready`, generates its own signed QR (`GET /groups/{id}/qr`, HMAC-signed
`{group_id, drop_id, business_id, iat, nonce}` — same signing pattern the
original venue QR used, but per-squad instead of per-Drop and scanned in the
opposite direction); a staff member scans it on the dashboard
(`POST /redemptions/scan`). The scan is the **entire** verification and
confirmation step — no location check, no separate approval tap, no
headcount correction. A staff member physically scanning a code shown on a
customer's phone is a stronger presence signal than either the old venue QR
(proves someone's phone has the code, not which phone) or the GPS claim
(proves phone location, not a human witness), while still costing the
business only one tap.

- `qr_signing_secret` is back as a Settings field, reintroduced after being
  removed when the venue QR was dropped — separate from `jwt_secret` so a
  leak of one token domain doesn't implicate the other; the production
  validator now rejects the two secrets being equal, in addition to each
  being individually strong.
- The squad QR carries `business_id`, and `scan_squad_qr` checks it against
  the scanning business's own id before anything else — a business can only
  ever confirm its own Drops' squads. Live-verified: a second, unrelated
  business scanning the first business's squad code gets a hard
  `403 {"detail": "This code belongs to a different business"}`.
- Re-fetching the QR (e.g. reopening the squad screen) issues a fresh token
  each time (new nonce/timestamp) rather than caching one; both the old and
  new tokens stay valid until the squad completes, since nothing expires
  them explicitly. Scanning is idempotent — rescanning an already-confirmed
  squad's code (staff double-tap, or scanning a stale token from before a
  refresh) returns the same Redemption rather than erroring.
- The `DISPUTE_WINDOW`/`dispute_redemption` mechanism from "Auto-confirm plus
  a dispute window" above is unchanged — a scan-confirmed redemption can
  still be disputed within 24h, records-only, no XP clawback.
- **Lost** (again): no location signal is checked at all now — a squad
  physically nowhere near the venue can still be confirmed if a staff member
  scans their code, so this pushes the trust boundary entirely onto staff
  behavior rather than any automated check. Accepted because the same was
  already true of the *original* venue QR design (the very first one in this
  document's history), and staff-in-the-loop was the actual fraud backstop
  the whole time — the auto-confirm-by-GPS design was the one outlier that
  removed it, and it's the one now being corrected.
- **Kept/gained**: no printing/signage step for the business (the squad
  generates its own code, not the venue), no camera/scanner UI on the
  *mobile* side (only the dashboard needs to scan — the phone just displays
  a QR, same complexity as the location-claim button it replaces), and the
  fraud property the user specifically asked for: a business can't fabricate
  a confirmation for a squad that never showed the code to its own staff.

Removed: `check_in_group`, `_within_check_in_range`,
`CHECK_IN_LOCATION_FRESHNESS`, `POST /groups/{id}/checkin`. Removed
`CHECK_IN_RADIUS_M` from the env examples (no longer read by anything).

Live-verified against the running stack: a squad member fetches a valid QR
once `ready`; a different business attempting to scan it is rejected with
the 403 above; the owning business scanning it confirms instantly
(`status: "confirmed"` in the same response, Group `completed` in the same
call, no separate approval step); XP lands via the existing async task
shortly after; rescanning the same squad's code (including a second,
independently-fetched token) is idempotent and returns the original
Redemption; and disputing the confirmed redemption afterward still releases
capacity without touching the awarded XP, exactly as before. The dashboard's
`ScanPage` (camera capture via `html5-qrcode`) and the mobile `SquadScreen`
QR display both type-check cleanly and were exercised at the code-path
level; the actual camera-to-decode-to-API round trip was not physically
verified, since this environment has no camera hardware to test against.

## Consistency audit after the squad-QR-scan redesign

Asked to check the recent redesigns for cross-cutting consistency (mobile
↔ backend, dashboard ↔ backend), not just re-verify each change in
isolation the way it was checked when it shipped. Walked every backend
route against what each frontend actually calls, every WS event the
backend publishes against what each frontend actually listens for, and the
shared response schemas field-by-field. Most of it held up (`GroupResponse`
↔ mobile's `GroupSnapshot`, `RedemptionResponse` ↔ the dashboard's
`Redemption` type, the WS event catalog vs. what's actually published are
all in sync). Two real, live-verified gaps turned up, both introduced by
"Business scans a squad-generated QR" above without being caught at the
time — that change touched `services/redemption.py` and its own unit
tests, not the analytics/notification code paths it silently broke:

- **The Analytics page's "Checked in" stat was structurally guaranteed to
  read 0 forever.** `business_analytics.drop_funnel()` counted
  `GroupStatus.checked_in`, a status that existed as a real intermediate
  step under the old check-in designs but that `scan_squad_qr` never
  sets — a squad now goes straight from `ready` to `completed` in one
  transition. Live-verified before fixing: ran a full create → assemble →
  scan flow to actual completion and confirmed the funnel returned
  `squads_checked_in: 0` sitting right next to `squads_completed: 1` — a
  business reading their own dashboard would see a completed redemption
  reported as 0% checked-in, which reads as broken instrumentation, not as
  a design choice. Fixed by removing the field entirely (schema, service,
  the dashboard's stat card, both test suites) rather than trying to
  redefine what it means — there's no intermediate state left for it to
  count. `GroupStatus.checked_in` and `RedemptionStatus.checked_in`
  themselves are left as unused-but-harmless enum values (same treatment as
  the already-documented unused `Redemption.pending`/`expired`), since
  dropping a value from a Postgres native enum type needs its own
  migration and isn't worth it for a value nothing selects into anymore.
- **Rescanning an already-confirmed squad's code re-sent a duplicate "you
  earned N XP" push and a duplicate `redemption.confirmed` broadcast to
  every member, even though it never re-awarded XP.** `scan_squad_qr` was
  already correctly idempotent about the *data* (returns the existing
  confirmed Redemption on a rescan, no second DB write), and
  `award_xp_for_redemption` was already correctly idempotent about *XP*
  (checks for an existing `UserXpTransaction` before granting more) — but
  the route called `award_xp_for_redemption_task.delay(...)` and published
  the WS event unconditionally on every successful scan, fresh or not, and
  the Celery task sends its push/WS confirm from whatever `xp_awarded`
  comes back, replay or not. A staff double-tap, a scanner misfire, or
  scanning an older still-valid token after the app silently refreshed it
  would each spam the squad's phones again for a scan that changed
  nothing. Fixed by having `scan_squad_qr` return `(redemption, is_fresh)`
  instead of just `redemption`, and having the route skip the WS publish
  and the Celery enqueue entirely when `is_fresh` is `False`. Live-verified:
  scanned the same squad's code twice, checked `notification_log` directly
  — exactly one `redemption_confirmed` row, not two.
- **The business dashboard's live Redemptions queue never actually received
  a scan live — a genuine regression, not a pre-existing gap.** The old
  `POST /groups/{id}/checkin` route (removed by this redesign) published
  its check-in event to `ws:business:{business_id}` in addition to the
  squad's own topics; the new `POST /redemptions/scan` route carried over
  the squad-facing publish targets but dropped that one. The dashboard's
  WS connection authenticates as the business and only ever subscribes to
  `ws:business:{id}` + `ws:drop:{id}` per live Drop (`main.py`'s
  `_business_topics`) — never `ws:group:{id}` — so `RedemptionQueuePage`'s
  reload-on-`redemption.*` listener was dead code with nothing to ever
  trigger it. A business with the Redemptions page open while staff
  scanned a code elsewhere would only see it after a manual refresh. Fixed
  by adding `ws:business:{business.id}` back to the scan route's publish
  set (still gated by `is_fresh`, so a rescan doesn't double-fire this
  either). Live-verified with a real WebSocket client authenticated as the
  business, connected to `/ws/live` exactly like the dashboard does:
  scanning a squad's code delivered a `redemption.checked_in` event on that
  connection within the same second, and a subsequent rescan delivered
  nothing (confirmed via a 2-second wait-and-timeout, not just "didn't
  crash").

Live-verified end to end after all three fixes: `pytest -q` still 198/198;
`GET /business/analytics/drops/{id}` no longer returns `squads_checked_in`
at all (dashboard and backend types both updated, `tsc --noEmit` and
`vite build` clean); a real create → assemble → scan run shows
`squads_completed: 1` with no dead field alongside it; and a deliberate
second scan of the same still-valid token produces exactly one
`redemption_confirmed` notification-log row, confirmed via direct SQL, not
two; and a business's own WebSocket connection now receives the
`redemption.checked_in` event the moment staff scan a code, with a rescan
correctly producing no second one.

Also noted, not fixed (lower severity, pre-existing, unrelated to this
redesign): `connection.request_received`/`connection.request_accepted` are
published over WS but no mobile screen subscribes to them — `Connections`
only loads its lists on mount/tab-switch, so an incoming friend request
only appears after a manual refresh or re-navigation, never live. This
predates the squad-QR-scan work and is a gap in the separate friends/
messaging workstream, not something this audit's fixes touch.

## Restyling the dashboard to match the mobile app

A teammate rebuilt the mobile app's visual design from scratch off a Figma
file — a light "paper" theme (cream background, pink/green brand colours,
dark "ink" accent surfaces for the Drop screen and bottom nav) with two
custom display/body typefaces, replacing what had been a generic dark
theme. They also built `apps/dashboard/src/theme.css` as a direct mirror of
`apps/mobile/src/theme.ts` (same token names, same values) and left a
"Deprecated — removed per page as each is migrated" alias block
(`--color-lime`/`--color-cyan`/`--color-violet`/`--color-surface-raised`
pointing at the new palette) so existing dashboard pages kept rendering
without a big-bang rewrite. Every dashboard page was still built against
the old dark-theme token names underneath that alias layer, and nothing
in the dashboard applied the new fonts at all — this is the migration that
finishes that job.

What changed, across every dashboard page and component:

- **Colour**: every reference to the deprecated aliases replaced with the
  real semantic tokens they were standing in for — `--color-lime` split
  into `--color-primary` (pink, actual CTAs/brand actions) or
  `--color-secondary` (green, "live"/positive/success status) depending on
  which the old lime was actually doing at each call site;
  `--color-violet`/`--color-cyan` mapped to `--color-info`/`--color-secondary`
  the same way; hardcoded dark-theme `rgba(...)` tint colours (status
  pills, danger buttons) replaced with the proper `--color-*-tint` +
  `--color-*` pairs the token system already defines for exactly this. The
  deprecated alias block itself is now deleted from `theme.css` — nothing
  references it anymore.
- **A genuine bug this surfaced**: the login page's active-tab pill used
  `--color-surface-raised` for its background, which the alias mapping had
  quietly made identical to `--color-bg` — the *track* it sits on. The
  active tab was rendering, just invisibly, indistinguishable from the
  inactive track around it. Fixed by giving it the card's own white
  instead, which is genuinely a different shade from the track.
- **Typography**: `apps/mobile/src/theme.ts` documents both custom
  typefaces as single-weight — "emphasis comes from the typeface, not the
  weight" — and the mobile app's own navigator config confirms this by
  pinning every font-weight slot (regular/medium/bold/heavy) to `400`
  regardless of what's requested. The dashboard had never applied either
  font at all (plain system UI font throughout) and had ~20 `font-weight:
  700-900` declarations doing the emphasis work instead. Set `--font-body`
  (Candal) as the base font, `--font-display` (Lilita One) on every
  heading, button, pill, and label — matching which of the two the actual
  mobile screens use for each — and removed every `font-weight` override
  in the dashboard's CSS to match the single-weight design; a boosted
  weight on a single-weight web font either does nothing or triggers a
  synthetic-bold render, neither of which is what the design intends.
- **Rarity colour**: DropCard and the Create Drop rarity preview both
  showed rarity as a single flat colour. The real mobile app doesn't have
  a rarity colour system shipped yet, but the design reference at
  `apps/api/demo/mobile.html` (a Figma-accurate HTML prototype a teammate
  built and just fixed a broken rarity-colour bug in) does: common=green,
  uncommon=teal, rare=gold, epic=pink, legendary=purple. Added `.rarity-*`
  utility classes using that mapping (plus a new `--color-teal` token,
  since teal doesn't otherwise exist in the token set) so a Drop's
  computed rarity reads the same way here as it will once the mobile app's
  own rarity display ships. Flagged as provisional in code comments since
  it's sourced from a prototype, not the shipped app, in case the real
  implementation lands with different colours.
- **Sidebar restyled as a dark "ink" panel**, the same surface
  `BottomTabBar.tsx` reserves for the mobile app's persistent bottom nav —
  reasoned as the dashboard's equivalent persistent navigation, not just a
  colour swap. Nav items are pill-shaped, the active item is a solid pink
  pill with cream text, exactly mirroring the bottom tab bar's
  `pillActive` treatment. The brand mark (a plain "D" square on both the
  Sidebar and the login page) was replaced with the same "DROP" + pin +
  "BY" wordmark HomeScreen.tsx uses for the mobile app's own header.

Not done: no visual/screenshot verification — this sandboxed environment
has no browser or headless-rendering tool available, so every change here
was verified by (1) cross-checking every `var(--...)` reference used
anywhere in the dashboard's CSS against what's actually defined in
`theme.css` (a scripted diff — zero mismatches after fixing one, a
`--radius-xxl` typo that should have been `--radius-2xl` and would have
silently rendered as a square corner), (2) `tsc --noEmit` and `vite build`
both clean, and (3) reasoning each colour/contrast pairing directly off a
real, already-shipped precedent in the mobile app's own screens (e.g. every
primary button pairs `colors.primary` background with `colors.onPrimary`
text in both places) rather than picking colours freehand. None of this is
a substitute for actually looking at the rendered page.

## The camera preview was never visible

The user actually opened the Scan page and confirmed what the last several
entries in this document have been flagging as unverified: the camera
feed never showed up on screen. This was a real, findable bug, not
something that needed a physical device to catch in hindsight.

The reader element (`<div id="dropby-qr-reader">`, the container
`html5-qrcode` attaches its `<video>` into) was rendered with
`hidden={status !== "ready"}` — hidden for the entire "requesting camera
access" phase, only unhidden once `Html5Qrcode.start()` had *already*
resolved. But `start()` measures the container's width the moment it's
called, to size the video feed: `element.clientWidth ? element.clientWidth
: Constants.DEFAULT_WIDTH` (checked directly in the installed
`html5-qrcode` package, `DEFAULT_WIDTH = 300`). A `display:none` element's
`clientWidth` is always `0`, so every single call was falling through to
that hardcoded 300px default instead of actually sizing to the real
container — and it was doing that while the whole element was invisible
regardless, since `hidden` doesn't get removed until after this
measurement already happened.

Fixed by only hiding the reader element for the states where a camera
will genuinely never attach (insecure origin, unsupported browser, no
camera, permission denied, a hard error) — during "requesting" and
"ready" it now stays in the DOM and visible from the very first render, so
by the time `start()` actually measures it, it has real dimensions to
measure. Also gave it a `min-height: 280px` in CSS so it reserves visible
space immediately rather than collapsing to nothing before any video
attaches.

This is exactly the class of bug the "no camera hardware in this
environment" caveat in every prior entry couldn't have caught — verifying
the API round-trip and the code paths in isolation doesn't catch a library
internal like this measuring the wrong thing at the wrong time. Live user
verification is what found it.

## Renamed dashboard pages for clarity

The user asked what the Redemptions page was for — a sign the name itself
wasn't doing its job, since the actual answer ("a history of already-
confirmed redemptions you can flag after the fact, not a queue of things
waiting on you") is not what "Redemptions" on its own suggests. Renamed to
**Redemption Log**, both the sidebar link and the page's own heading.

Looking at it surfaced a second, worse instance of the same problem: the
"Drops" page (list/publish/pause/resume/cancel your Drops) was implemented
in a file still called `LiveQueuePage.tsx`, left over from before
redemption confirmation existed as its own page — its own top comment
still said "once that [redemption] workstream lands, a confirm action...
belongs here," which had already happened, elsewhere, and was just never
updated. Renamed the sidebar link to **Manage Drops** (also distinguishes
it more clearly from the separate "Create Drop" page) and renamed the file
itself to `ManageDropsPage.tsx`/`.css`, since the stale name was actively
misleading to read, not just an internal detail.

Left unchanged: Overview, Create Drop, Scan to confirm, and Analytics —
none of these were confusing on their own terms.

Verified: `tsc --noEmit` and `vite build` both clean; grepped for every
remaining reference to `LiveQueuePage` across the dashboard source (one
left, the historical note in `ManageDropsPage.tsx`'s own comment
explaining the rename).

## Key decisions

- Keep a modular FastAPI monolith so Drop → Group → Redemption → XP can remain
  transactional while each teammate owns separate modules.
- Use PostgreSQL + PostGIS for `ST_DWithin`/`ST_Distance` proximity queries.
- Use Redis pub/sub for cross-process WebSocket fan-out and Celery as the job
  runner; REST discovery continues from PostgreSQL during a Redis outage.
- Keep all state mutations in protected REST endpoints. WebSockets are a
  read-only notification channel and clients re-fetch snapshots after reconnect.
- Every active Drop is detectable regardless of distance (in-app, via a
  location ping). Detect exposes its rarity, specific interest type,
  distance, and required group size. Push notifications now *also* alert
  every user with a known location the moment a Drop goes active, so
  discovery doesn't require already being nearby and pinging at the right
  moment — see "Notification-driven discovery" below. The push itself is
  deliberately thinner than the in-app Detect payload: category and rounded
  distance only, no rarity/group-size/title.
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
- Check-in is a squad-generated, business-scanned QR, not a location claim
  and not the original venue QR — each `ready` squad signs its own token
  (`qr_signing_secret`, separate from `jwt_secret`); the business scans it,
  and that scan is the entire verification+confirmation step, no location
  check involved at all. See "Business scans a squad-generated QR" above for
  the full history of how check-in got here and why GPS-only proved
  insufficient.
- One Redemption row per Group (`uq_redemption_group`), created lazily on
  first scan rather than eagerly when the squad becomes ready.
- Check-in (the scan) auto-confirms — no separate approval gate after it, no
  headcount correction — with a 24h dispute window as the only recourse, and
  disputing never claws back XP already awarded. See "Auto-confirm plus a
  dispute window" above for the fraud-surface reasoning that led here, and
  "Business scans a squad-generated QR" for what replaced the location check
  itself.
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
- The dashboard's design tokens (`theme.css`) are a direct mirror of the
  mobile app's (`theme.ts`) — same names, same values, no independent
  dashboard-only palette — so the two keep reading as one product as the
  mobile design evolves. Both fonts (Lilita One display, Candal body) are
  treated as single-weight everywhere, matching the mobile app's own
  navigator config, which pins every font-weight slot to 400 regardless of
  what's requested — no dashboard CSS sets `font-weight`.
- Rarity gets five distinct colours (common through legendary), sourced
  from the Figma-accurate HTML design reference at
  `apps/api/demo/mobile.html` rather than the shipped mobile app, since the
  mobile app doesn't have its own rarity colour system built yet. Treated
  as provisional — revisit if the real implementation lands with different
  colours.

## Next steps

1. Confirm the camera preview fix (see "The camera preview was never
   visible" above) actually shows a live picture now — the specific bug
   found (a hidden container measured as 0-width) is fixed and reasoned
   through against the `html5-qrcode` source directly, but this sandbox
   still has no camera hardware, so the fix itself hasn't been watched
   render. The insecure-origin/unsupported-browser/no-camera/
   permission-denied branching and the manual code-entry fallback are also
   still unexercised against a real getUserMedia prompt.
2. Visually verify the restyled dashboard in a real browser — this
   sandboxed environment has no headless browser or screenshot tool, so
   the restyle was verified by scripted CSS-variable cross-checking,
   `tsc`/`vite build`, and reasoning off the mobile app's own real usage
   patterns, not by looking at the rendered page. Also reconsider the
   rarity colours once the mobile app ships its own rarity display (see
   "Restyling the dashboard to match the mobile app" above) — they're
   currently sourced from a prototype, not the shipped app.
3. Business moderation UI/endpoints for approving a pending registration —
   right now only direct DB/seed access sets `Business.status = active`.
4. Mobile: wire `GET /gamification/me/stats` and `/me/history` for a
   Collection/Profile screen, and the powerup/perk/weekly-challenge
   endpoints — check-in is now wired; gamification display isn't.
5. Mobile: register a real FCM token via `POST /devices` and subscribe to the
   `territory.bonus_awarded` WS event, so push notifications and territory
   popups actually reach the phone.
6. Set up real codegen for `packages/shared-types` from `ws-contracts`, or
   drop the package — right now it's a hand-mirrored placeholder nothing
   actually imports.
7. Run `python -m app.scripts.seed_badges` once against a fresh database so
   badge criteria have real `Badge` rows to unlock against.
8. Select a deployment provider, add its PostgreSQL/PostGIS and Redis URLs,
   secrets, domain, and TLS configuration, then start the supplied production
   Compose stack.
