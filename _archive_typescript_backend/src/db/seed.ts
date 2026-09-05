import { loadConfig } from "../config.js";
import { createPool } from "./pool.js";

const drops = [
  {
    id: "10000000-0000-4000-8000-000000000001",
    venue: "Seoul Table",
    offer: "40% off Korean BBQ",
    description: "40% off the group dining menu.",
    category: "Korean food",
    broad: "Food",
    rarity: "rare",
    address: "200 Little Bourke Street, Melbourne VIC",
    latitude: -37.8119,
    longitude: 144.9674,
    minimum: 4,
    maximum: 6,
  },
  {
    id: "10000000-0000-4000-8000-000000000002",
    venue: "Laneway Coffee",
    offer: "Free coffee upgrade",
    description: "Upgrade any regular coffee to a large at no charge.",
    category: "Cafe",
    broad: "Food",
    rarity: "common",
    address: "Centre Place, Melbourne VIC",
    latitude: -37.8167,
    longitude: 144.9653,
    minimum: 1,
    maximum: 1,
  },
  {
    id: "10000000-0000-4000-8000-000000000003",
    venue: "Vault Escape",
    offer: "Half-price escape room",
    description: "A private one-hour room for your squad.",
    category: "Escape room",
    broad: "Activities",
    rarity: "epic",
    address: "Queen Street, Melbourne VIC",
    latitude: -37.8136,
    longitude: 144.9599,
    minimum: 5,
    maximum: 7,
  },
] as const;

async function seed(): Promise<void> {
  const pool = createPool(loadConfig().DATABASE_URL);
  try {
    for (const drop of drops) {
      await pool.query(
        `INSERT INTO drops (
           id, venue_name, offer_title, offer_description, category, broad_category, rarity,
           status, location, address, minimum_group_size, maximum_group_size,
           available_groups, starts_at, expires_at
         ) VALUES (
           $1, $2, $3, $4, $5, $6, $7, 'active',
           ST_SetSRID(ST_MakePoint($9, $8), 4326)::geography,
           $10, $11, $12, 5, now() - interval '5 minutes', now() + interval '6 hours'
         )
         ON CONFLICT (id) DO UPDATE SET
           status = 'active', starts_at = now() - interval '5 minutes',
           expires_at = now() + interval '6 hours', available_groups = 5,
           updated_at = now()`,
        [
          drop.id, drop.venue, drop.offer, drop.description, drop.category, drop.broad,
          drop.rarity, drop.latitude, drop.longitude, drop.address, drop.minimum, drop.maximum,
        ],
      );
    }
    process.stdout.write(`Seeded ${drops.length} Melbourne Drops\n`);
  } finally {
    await pool.end();
  }
}

seed().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
