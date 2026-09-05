# Discovery engine (workstream 1)

This is the implemented scope for the real-time discovery owner. Other API modules remain owned by their respective teammates.

## Included

- JWT registration/login and protected routes
- onboarding preferences and location permission state
- PostGIS `POST /api/v1/drops/location/ping`
- server-side Detect (700 m), Reveal (180 m), and Discover (60 m) field gating
- Redis-backed persistent Discover unlock until the Drop expires
- authenticated raw WebSocket endpoint at `/ws/live?token=...`
- squad create/read/join/leave with live 2/4 -> 3/4 -> 4/4 count/state events
- atomic Drop capacity reservation when a squad reaches ready and as it fills
- validated Drop creation with draft, scheduled, and active lifecycle staging
- scheduled activation, countdown, expiry, and squad-expiry Celery tasks
- initial Alembic migration for discovery tables and their user/business prerequisites

## Open the zero-install UI demo

From the repository root:

```bat
demo.cmd
```

This opens a self-contained discovery sandbox with a pannable, zoomable
OpenStreetMap view centred on five fictional Melbourne Drops. The distance
control moves the user marker against real 700 m, 180 m, and 60 m map circles,
while every Drop independently applies the reveal rules. Click any marker to
inspect its currently permitted details, or click the map to calculate that
location's distance from the primary Drop. Move
through 850 m → 500 m → 150 m → 50 m to see the exact Detect, Reveal, and
Discover payloads, then create a squad and advance it through 2/4, 3/4, and
4/4. Internet is needed for the map library/tiles. The sandbox uses simulated
local state and does not claim to test the database or WebSocket transport.

## Run the real backend

Install and open Docker Desktop. From the repository root, run:

```bat
dev.cmd
```

That single command creates the environment file, builds the backend services,
runs the migration, seeds a user/business/active Drop, and opens Swagger. Use:

```bat
dev.cmd verify
dev.cmd logs
dev.cmd status
dev.cmd stop
```

`dev.cmd verify` checks the live PostGIS extension, creates two squads whose
simultaneous joins compete for a two-person Drop, asserts that capacity cannot
be oversubscribed, tests Redis pub/sub, and confirms an authenticated WebSocket
receives the event. The verifier always removes its temporary database rows.

Open <http://localhost:8000/docs>.

### Run without Docker

Install PostgreSQL with PostGIS locally first. Redis is optional for this mode:
REST discovery still works without it, but WebSocket fan-out and Celery jobs wait
until Redis is available.

In Windows Command Prompt:

```bat
cd apps\api
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env
```

Change `DATABASE_URL` in `.env` so its host is `localhost`, then run:

```bat
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m app.scripts.seed_discovery
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs>.

Use these login credentials:

```json
{
  "email": "explorer@dropbyapp.com",
  "password": "dropby12345"
}
```

Copy the returned token into Swagger's **Authorize** dialog. Then call the location-ping endpoint with:

```json
{ "latitude": -37.8074, "longitude": 144.9674 }
```

That is roughly 500 m away and returns Detect data only. Repeat with approximately 150 m and 50 m:

```json
{ "latitude": -37.81055, "longitude": 144.9674 }
{ "latitude": -37.81145, "longitude": 144.9674 }
```

Only the final response includes the venue, address, offer, group sizes, countdown, and Assemble flag.

## WebSocket contract

Connect to:

```text
ws://localhost:8000/ws/live?token=YOUR_JWT
```

All mutations remain REST operations. The socket pushes the existing shared contract events:

- `drop.stage_update`
- `drop.capacity_reached`
- `drop.expired`
- `drop.countdown_warning`
- `group.state_update`
- `group.member_joined`
- `group.ready`

Reconnects re-subscribe the user's active squad topics; clients re-fetch REST snapshots rather than replaying missed events. Redis fan-out reconnects automatically, while REST discovery continues from PostgreSQL if Redis is temporarily unavailable.

## Production container deployment

Use `infra/docker-compose.production.yml` with managed PostgreSQL/PostGIS and
Redis services. Copy `infra/.env.production.example` to the ignored
`infra/.env.production`, replace the placeholders, then run from the repository
root:

```bat
docker compose --env-file infra\.env.production -f infra\docker-compose.production.yml up --build -d
```

The migration must succeed before the API, worker, and scheduler start.
Production containers run without auto-reload as a non-root user, the API has a
health check, and startup rejects default or matching JWT/QR signing secrets.
The provider is responsible for TLS termination, the public domain, backups,
and supplying the environment values.
