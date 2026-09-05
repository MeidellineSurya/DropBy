import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { loadConfig } from "../config.js";
import { createPool } from "./pool.js";
import { transaction } from "./transaction.js";

function migrationsDirectory(): string {
  return join(process.cwd(), "migrations");
}

export async function migrate(): Promise<void> {
  const config = loadConfig();
  const pool = createPool(config.DATABASE_URL);

  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        filename text PRIMARY KEY,
        applied_at timestamptz NOT NULL DEFAULT now()
      )
    `);

    const files = (await readdir(migrationsDirectory()))
      .filter((file) => file.endsWith(".sql"))
      .sort();

    const applied = await pool.query<{ filename: string }>("SELECT filename FROM schema_migrations");
    const appliedNames = new Set(applied.rows.map((row) => row.filename));

    for (const filename of files) {
      if (appliedNames.has(filename)) continue;
      const sql = await readFile(join(migrationsDirectory(), filename), "utf8");
      await transaction(pool, async (client) => {
        await client.query(sql);
        await client.query("INSERT INTO schema_migrations (filename) VALUES ($1)", [filename]);
      });
      process.stdout.write(`Applied ${filename}\n`);
    }
  } finally {
    await pool.end();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  migrate().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
