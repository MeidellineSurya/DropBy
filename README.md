# DropBy

DropBy is a location-based deal discovery app. Businesses publish timed **Drops**; people can see their rarity from afar, reveal the offer when they get close, form a squad, and redeem it together.

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
