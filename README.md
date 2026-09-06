# DropBy

🎯 Pokémon GO, but you catch real-world deals — businesses drop time-limited
offers that only reveal themselves as you physically walk toward them, and
the best ones require a squad to unlock 🗺️

## What this is

A business posts a **Drop** — a discount, tied to a location and a time
window. Nearby users see a generic signal from a distance (**Detect**); it
only fully reveals — offer, address, countdown — once they're within about
100 meters (**Reveal**). Some Drops need a minimum group size, so unlocking
one means gathering friends and going somewhere in real life. Once a squad
is ready, they scan the venue's QR code to check in; the business confirms
on a live dashboard queue, and everyone in the squad earns XP.

Rarity and XP are never set by the business — the platform computes both
from the offer's actual terms (discount depth, venue capacity, group-size
requirement), so a business can't just label a 5%-off coffee "Legendary."

This repo is a working full-stack implementation of that loop: FastAPI
backend, a React Native consumer app, and a React business dashboard.

## Quick start

The fastest way to see it work needs **no install at all**:

```bat
demo.cmd
```

A self-contained browser demo of the full consumer experience — sign in,
onboarding, map discovery, squad assembly, gamification — against five
fictional Melbourne Drops. No Docker, database, Python, or Node required.

To run the real backend (Windows, with Docker Desktop installed and open):

```bat
dev.cmd
```

This creates `.env`, builds the backend, runs migrations, seeds demo data,
and opens Swagger at <http://localhost:8000/docs>.

```bat
dev.cmd verify   # live integration check: PostGIS, capacity races, WebSockets
dev.cmd logs
dev.cmd status
dev.cmd stop
```

Manual, non-Docker setup is documented in
[`apps/api/DISCOVERY_ENGINE.md`](apps/api/DISCOVERY_ENGINE.md).

## Repository structure

| Path | What it is |
|---|---|
| `apps/api` | FastAPI backend — a modular monolith (discovery/real-time, business/supply, redemption+gamification+notifications), PostgreSQL+PostGIS, Redis, Celery |
| `apps/mobile` | Expo/React Native consumer app |
| `apps/dashboard` | React + Vite business partner dashboard |
| `packages/ws-contracts` | Frozen Pydantic WebSocket event/DTO contracts |
| `packages/shared-types` | TypeScript types mirroring `ws-contracts` |
| `infra/` | Docker Compose stacks (dev and production) |

## Try the consumer frontend

Run `demo.cmd` (or `mobile.cmd`) to open the standalone browser frontend.
It uses local fictional Melbourne Drop data, so it needs no backend, Docker,
Expo Go, account, or API configuration.

1. Sign in with the filled demo account, or create one to see onboarding.
2. On **Nearby Drops**, press **Detect** and **Reveal**.
3. Open a signal card for the progressive Drop-details screen.
4. Create a squad and add members to move through 2/4 → 3/4 → 4/4.
5. Open **Profile → Discovery engine lab** for lifecycle, capacity, and
   real-time event tools.

The Expo/React Native client is an Expo Go wrapper around that same browser
demo, so its interface and interactions match `demo.cmd`. It needs internet
access to load the demo, but no Docker, tunnel, or API account. To run it:

```bash
cd apps/mobile
npm install
npm start -- --lan --clear
```

Install Expo Go, then scan the QR code Expo prints.

## Business dashboard

With the stack running, the dashboard is served at
<http://localhost:5173>. Log in with the seeded demo business:

- Email: `venue@dropbyapp.com`
- Password: `dropby12345`

From there: **Overview**, **Drops**, **Create Drop** (with a live computed
rarity/XP preview), **Analytics**, and **Live Queue** — where checked-in
squads show up in real time for a business to confirm or reject.

Sessions last one hour with no refresh flow yet; an expired session
redirects to login automatically instead of leaving a dead-end error.

## Production deployment

`infra/docker-compose.production.yml` targets an external PostgreSQL
(PostGIS-enabled) and Redis:

```bat
copy infra\.env.production.example infra\.env.production
docker compose --env-file infra\.env.production -f infra\docker-compose.production.yml up --build -d
```

Migrations run before the API, worker, and scheduler start. The API has a
`/health` check, runs as a non-root user, and refuses weak/default
production secrets. Still needed: a hosting provider, real secrets/domain,
and TLS.

## Status & decisions

Discovery, the business platform, and the redemption/gamification/
notifications loop are all implemented and merged. See
[`STATUS.md`](STATUS.md) for the full progress table, key architectural
decisions, and everything that's explicitly *not* built yet (mobile QR
scanning, business moderation UI, notification delivery in the mobile app,
and more).
