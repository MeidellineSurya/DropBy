import type { Pool } from "pg";
import type { NearbyDropRow, RevealStage } from "../types/domain.js";

export interface NearbyDrop {
  id: string;
  revealStage: RevealStage;
  distanceMetres: number;
  rarity: NearbyDropRow["rarity"];
  broadCategory: string;
  expiresAt: string;
  groupRequired?: boolean;
  minimumGroupSize?: number;
  maximumGroupSize?: number;
  category?: string;
  venue?: { name: string; address: string; latitude: number; longitude: number };
  offer?: { title: string; description: string | null };
  canCheckIn?: boolean;
}

export function revealStage(row: NearbyDropRow): RevealStage {
  if (row.distance_m <= row.full_reveal_radius_m) return "full";
  if (row.distance_m <= row.partial_reveal_radius_m) return "partial";
  return "detection";
}

export function serializeNearbyDrop(row: NearbyDropRow): NearbyDrop {
  const stage = revealStage(row);
  const base: NearbyDrop = {
    id: row.id,
    revealStage: stage,
    distanceMetres: Math.round(row.distance_m),
    rarity: row.rarity,
    broadCategory: row.broad_category,
    expiresAt: row.expires_at.toISOString(),
  };

  if (stage === "detection") return base;

  base.category = row.category;
  base.groupRequired = row.minimum_group_size > 1;
  base.minimumGroupSize = row.minimum_group_size;
  base.maximumGroupSize = row.maximum_group_size;

  if (stage === "full") {
    base.venue = {
      name: row.venue_name,
      address: row.address,
      latitude: row.latitude,
      longitude: row.longitude,
    };
    base.offer = { title: row.offer_title, description: row.offer_description };
    base.canCheckIn = row.distance_m <= row.check_in_radius_m;
  }

  return base;
}

export async function findNearbyDrops(
  db: Pool,
  userId: string,
  latitude: number,
  longitude: number,
): Promise<NearbyDrop[]> {
  const result = await db.query<NearbyDropRow>(
    `
      WITH position AS (
        SELECT ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography AS point
      ), updated_user AS (
        UPDATE users
        SET last_location = (SELECT point FROM position), last_location_at = now(), updated_at = now()
        WHERE id = $3
      )
      SELECT
        d.id, d.venue_name, d.offer_title, d.offer_description, d.category, d.broad_category,
        d.rarity, d.address, d.minimum_group_size, d.maximum_group_size, d.expires_at,
        d.partial_reveal_radius_m, d.full_reveal_radius_m, d.check_in_radius_m,
        ST_Distance(d.location, position.point) AS distance_m,
        ST_X(d.location::geometry) AS longitude,
        ST_Y(d.location::geometry) AS latitude
      FROM drops d
      CROSS JOIN position
      WHERE d.status = 'active'
        AND d.starts_at <= now()
        AND d.expires_at > now()
        AND d.available_groups > 0
        AND ST_DWithin(d.location, position.point, d.detection_radius_m)
      ORDER BY distance_m ASC, d.expires_at ASC
      LIMIT 100
    `,
    [latitude, longitude, userId],
  );

  return result.rows.map(serializeNearbyDrop);
}
