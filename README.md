# DropBy

DropBy is a location-based deal discovery app. Businesses publish timed **Drops**; people can see their rarity from afar, reveal the offer when they get close, form a squad, and redeem it together.

## What it does

DropBy turns local deals into a social, location-based experience. Users explore a live map, see a Drop's rarity from a distance, discover more detail as they move closer, then team up to claim the offer.

### Key features

- Location-aware Detect → Reveal discovery, using PostGIS distance queries
- Time-limited Drops with computed rarity and XP rewards
- Live map pins, progressive deal detail, countdowns, and a move-closer demo mode
- Squad creation, joining, chat, QR check-in, redemption, XP, badges, streaks, perks, and account buffs
- A business dashboard for registration, venue settings, Drop creation, lifecycle management, analytics, redemption scanning, and live updates
- Expo Go support on iPhone, using a Cloudflare tunnel to reach the local API

This repository contains one product with three parts:

| Path | Purpose |
| --- | --- |
| `apps/api` | FastAPI API, Postgres/PostGIS models, Redis and Celery workers |
| `apps/dashboard` | React business dashboard for creating and managing Drops |
| `apps/mobile` | Expo Go shell for the shared mobile experience in `apps/api/demo/mobile.html` |
| `infra` | Local Docker Compose stack |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- Node.js 20 or later
- Expo Go on an iPhone (only required for the mobile app)

The API runs locally in Docker. An iPhone cannot reach `localhost` on your Mac, so Expo Go uses a temporary Cloudflare tunnel.

## Start the full app

From the repository root, create the API environment file once:

```bash
cp apps/api/.env.example apps/api/.env
```

Start the API, database, workers and dashboard:

```bash
cd infra
docker compose up -d --build
docker compose exec api python -m app.scripts.seed_discovery
```

Open the business dashboard at [http://localhost:5173](http://localhost:5173). The API health check is at [http://localhost:8000/health](http://localhost:8000/health) and API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

Seeded dashboard login:

- Email: `venue@dropbyapp.com`
- Password: `dropby12345`

Seeded consumer login:

- Email: `explorer@dropbyapp.com`
- Password: `dropby12345`

## Run on Expo Go (iPhone)

Keep the Docker stack running. In a second terminal at the repository root, start a tunnel to the API:

```bash
npx wrangler tunnel quick-start http://localhost:8000
```

Copy the `https://...trycloudflare.com` URL it prints, keep that terminal open, and put it in `apps/mobile/.env`:

```env
EXPO_PUBLIC_API_URL=https://your-current-tunnel.trycloudflare.com
```

If the file does not exist yet:

```bash
cp apps/mobile/.env.example apps/mobile/.env
```

Then start Expo:

```bash
cd apps/mobile
npm install
npm start -- --lan --clear
```

Scan the QR code using Expo Go. Approve location access when asked. The mobile app is the same frontend as the browser demo, but it injects your iPhone's live location and connects to the API configured above.

Every quick Cloudflare tunnel has a new URL. When you restart the tunnel, update `apps/mobile/.env`, stop Expo with `Ctrl+C`, and start Expo again with the command above.

## Browser demo

The standalone frontend has an offline fallback and is useful for quick UI demos:

```bash
open apps/api/demo/mobile.html
```

On Windows, double-click `demo.cmd`. `mobile.cmd` is retained as the same convenience launcher.

## Common commands

```bash
# View local containers
cd infra
docker compose ps

# Follow API logs
docker compose logs -f api

# Stop local services (keeps database data)
docker compose down

# Rebuild after API changes
docker compose up -d --build api

# Check the Expo project
cd ../apps/mobile
npm run typecheck
```

## Notes

- Drops added in the dashboard are returned to the mobile app while they are active and within their scheduled time window.
- The dashboard is intended for local development at `localhost:5173`; Expo Go connects to the API through the Cloudflare URL in `apps/mobile/.env`.
- The API environment file is deliberately ignored by Git. Do not commit tunnel URLs, production credentials, or secrets.

## Tech stack

| Area | Technology |
| --- | --- |
| API | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic |
| Data and jobs | PostgreSQL with PostGIS, Redis, Celery, GeoAlchemy2, Psycopg |
| Authentication | python-jose, Passlib/bcrypt, email-validator |
| Real-time and notifications | WebSockets, Firebase Admin SDK (FCM integration), Redis fan-out |
| Business dashboard | React, TypeScript, Vite, React Router, html5-qrcode |
| Mobile | Expo, React Native, Expo Location, React Native WebView, React Native Safe Area Context |
| Maps and UI | Leaflet, OpenStreetMap tiles, Phosphor Icons, Google Fonts Candal, BBH Bartle font |
| Local development | Docker Compose, PostGIS Docker image, Redis Docker image, Cloudflare Quick Tunnels, Expo Go |

## Credits and third-party services

### Libraries

- API: FastAPI, Uvicorn, SQLAlchemy, Alembic, Psycopg, GeoAlchemy2, Pydantic, Pydantic Settings, Redis, Celery, Firebase Admin, WebSockets, python-jose, Passlib, bcrypt, email-validator, and python-multipart.
- Dashboard: React, React DOM, React Router, Vite, TypeScript, html5-qrcode, Oxlint, and the Vite React plugin.
- Mobile: Expo, React, React Native, Expo Location, React Native WebView, React Native Safe Area Context, TypeScript, and the React type definitions.
- Shared contracts: Pydantic-based WebSocket contracts in `packages/ws-contracts`.

### APIs, assets, templates, and data

- [OpenStreetMap](https://www.openstreetmap.org/) map tiles and attribution, displayed with [Leaflet](https://leafletjs.com/).
- [Phosphor Icons](https://phosphoricons.com/) for interface icons.
- [Google Fonts](https://fonts.google.com/) for Candal and the embedded BBH Bartle typeface, distributed under the SIL Open Font License.
- [QR Server](https://goqr.me/api/) generates the personal user QR image used in the demo.
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) expose the local API to Expo Go during development.
- The map Pins, business details, offers, and user data used for the demo are fictional seeded data created for DropBy. No external dataset or UI template was used.

## AI usage

[OpenAI Codex](https://openai.com/codex/) was used as a development assistant for implementation, debugging, refactoring, documentation, and testing guidance. Product decisions, validation on devices, final integration, and review were completed by the project team.
