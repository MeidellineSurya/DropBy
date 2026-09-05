"""Discovery module — the Detect/Reveal/Discover stage engine.

Flow (triggered by POST /drops/location/ping):
  1. ST_DWithin/ST_Distance query against active Drops for the requesting user's lat/lng.
  2. Map distance -> stage using each Drop's own radius thresholds (falls back to
     settings.default_*_radius_m), OR force "discover" if a discover_unlocked
     cache hit exists for (user_id, drop_id) — see note below.
  3. Compare to the last-known cached stage; on change, insert a DropViewEvent
     row and publish ws:user:{user_id} -> DropStageUpdate.
  4. Return the full current snapshot synchronously in the REST response too,
     so the client stays correct even if a WS push is missed mid-background-update.

Persistence rule: once a user reaches "discover" for a Drop, cache
`discover_unlocked:{user_id}:{drop_id}` in Redis (TTL = Drop's remaining
lifetime) so stepping away to gather a squad doesn't re-hide the offer.
"""


def compute_stage_for_ping(user_id: str, lat: float, lng: float) -> list[dict]:
    raise NotImplementedError
