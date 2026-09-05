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
It mirrors the Expo app as separate mobile screens for sign-in, onboarding,
map discovery, Drop details, squad assembly, profile, and an engine lab. The
Melbourne map includes five fictional Drops that independently progress from
Detect → Reveal. Every active Drop is detectable: Detect shows its rarity,
specific type, and people needed. Reveal unlocks the restaurant, full offer,
and exact location at 100 m. The map displays anonymous signal points and a
100 m Reveal zone around each Drop. The separate engine-lab screen
preserves protected-response, lifecycle, capacity, and real-time event tools
without crowding the product screens. An internet connection is only needed
for the map library and street tiles. It is a product demonstration, not an
integration test of the server.

Try the complete flow:

1. Sign in with the filled demo account, or create an account to see onboarding.
2. On **Nearby Drops**, press **Detect** and **Reveal**.
3. Open a signal card to see the progressive Drop-details screen.
4. Create a squad and add members to move through 2/4, 3/4, and 4/4.
5. Open **Profile** from the avatar, then open **Discovery engine lab** for the
   lifecycle, capacity, protected payload, and real-time event tools.

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

While the discovery screen is open, the mobile client continuously watches the
device location and refreshes nearby Drops after roughly 10 metres of movement
or every few seconds on supported platforms. Selecting a Melbourne demo
position pauses live GPS until continuous tracking is enabled again.

### Business dashboard

With the Docker stack running (`dev.cmd`, or `docker compose up -d` from
`infra/`), the dashboard is served at <http://localhost:5173>. A seeded demo
business is created by the same seed step as the mobile demo data:

- Email: `venue@dropbyapp.com`
- Password: `dropby12345`

Log in to see the Overview, Drops, Create Drop, Analytics, and Live Queue
pages. Creating a Drop only asks for a discount percentage and group-size
requirements — rarity and the resulting XP reward are computed by the
platform from those inputs plus the business's registered venue capacity, not
entered directly, so they can't be inflated. A squad checks in by scanning the
Drop's venue QR (signed server-side; there's no dashboard UI to render it yet,
see `STATUS.md`), which appears on the **Live Queue** page for the business to
confirm or reject. Sessions last one hour and there's no refresh flow yet — an
expired session bounces back to the login screen automatically.

## Status

The real-time discovery workstream is implemented: JWT/onboarding, PostGIS
Detect/Reveal, authenticated WebSockets, Drop lifecycle jobs, squad
formation, capacity enforcement, migrations, and Docker wiring. See
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md) for setup and a
seeded walkthrough.

The business/supply-side workstream is also implemented end to end: business
auth, Drop creation/management, platform-computed rarity and XP (not
business-declared, to keep both honest), analytics, and a full redemption
flow — a squad scans the venue's QR, the business confirms or rejects it from
a live queue on the dashboard, and XP is awarded. See
[`STATUS.md`](STATUS.md) for the detailed progress table and open gaps.

Gamification depth (XP ledger, badges, leveling), notifications, business
moderation UI, and mobile-side QR scanning remain unbuilt.

## Workstream 1 sign-off

Implemented for the real-time discovery owner:

- authenticated WebSockets and Redis fan-out
- PostGIS proximity and Detect → Reveal field gating
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

## Workstream 2 sign-off

Implemented for the business/supply-side owner:

- business registration/login on a separate JWT audience from consumer auth
- Drop CRUD (create/list/publish/pause/resume/cancel), gated on the owning
  business being active before a Drop can go live
- platform-computed rarity (from discount depth, with a scarcity bump from
  venue capacity or minimum group size) and platform-computed XP reward from
  that same rarity — a business can't declare either directly
- venue capacity captured once at registration as a hard ceiling on a Drop's
  capacity, not left as a freely-editable per-Drop field
- business Drop performance and account overview analytics
- venue QR sign/verify and the full check-in → confirm/reject → XP-award
  redemption flow, with capacity correctly released on a reject
- the business dashboard: login/register, Overview, Drops, Create Drop,
  Analytics, and a live redemption queue, all on the shared WebSocket/Redis
  fan-out from workstream 1
- CORS, a global validation-error handler, and session-expiry handling in the
  dashboard
- 101 backend tests and a single linear Alembic migration head

The workstream implementation and local integration sign-off are complete.
Live Docker verification passed end to end: a real business registering,
creating a Drop with a computed rarity/XP preview, a squad reaching that
Drop, a real venue-QR check-in, a confirm with an actual XP database
mutation, and a reject with capacity released back to the Drop.

Still open, not part of this sign-off: gamification depth beyond a flat XP
total (ledger, badges, leveling), notifications, business moderation
UI/endpoints to approve pending registrations, a dashboard view to display or
print a Drop's venue QR, and the mobile-side QR scan screen. See
[`STATUS.md`](STATUS.md) for the full list.

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

Cross-team integration still required, but not owned by either completed
workstream:

- the included Expo client exercises the REST and authenticated WebSocket
  discovery contracts, but has no redemption/QR-scan screen yet — a squad
  currently checks in via the business's venue QR through the API directly,
  with no mobile UI for a customer to scan it
- notifications (push, countdown warnings, new-Drop alerts) are unbuilt
  across every workstream
- business moderation (approving a pending registration so it can publish
  Drops) has no UI or endpoint yet — only direct DB/seed access sets it
